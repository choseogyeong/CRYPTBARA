import io.joern.dataflowengineoss.language._
implicit val resolver = toExtendedCfgNode _

// importCode is dynamically injected by run_joern_script.py

// Load list of cryptographic classes from file
val classFilePath = "./utils/filtered_classes.txt"
val targetClasses = scala.io.Source.fromFile(classFilePath)
  .getLines()
  .map(_.trim)
  .filter(_.nonEmpty)
  .toList

println("[+] Cryptographic-related calls and receiver tracing results:")

// Filter API calls that match target classes
val targets = cpg.call.filter { call =>
  targetClasses.exists(cls => call.methodFullName.contains(cls))
}.l

// Iterate over each matching call
targets.foreach { call =>
  val api = call.methodFullName
  val line = call.lineNumber.getOrElse(-1)
  val method = Option(call.method.fullName).getOrElse("unknown")
  val callCode = call.code

  // Check if receiver exists (e.g., x.update)
  val receiverExpr = call.receiver.headOption
  val receiverVarCode = receiverExpr.map(_.code).getOrElse("N/A")

  // Extract base variable name (e.g., x from x.update)
  val receiverVarBase = if (receiverVarCode.contains(".")) {
    receiverVarCode.split("\\.")(0)
  } else {
    receiverVarCode
  }

  println(s"\n[+] Call: $callCode @ line $line in $method")

  if (receiverExpr.nonEmpty) {
    println(s"  → Receiver: ${call.name} (code: $receiverVarCode, base: $receiverVarBase)")

    // 1. Use DDG to trace backward data flow definitions
    val defsFromDDG = cpg.identifier.nameExact(receiverVarBase).ddgIn
      .filterNot(_.code.matches(".*\\.encode\\(\\).*"))
      .filterNot(_.code.matches(".*\\.decode\\(\\).*"))
      .filterNot(_.code.matches("\".*\""))
      .filterNot(_.code.matches(".*[0-9]+.*"))
      .map(_.code)
      .distinct
      .l

    // 2. Check assignment where RHS is a function call (e.g., x = MD5.new())
    val defsFromAssign = cpg.assignment
      .where(_.target.codeExact(receiverVarBase))
      .map(_.source)
      .filter(_.isCall)
      .map(_.code)
      .distinct
      .l

    // 3. Combine definition sources
    val defs = (defsFromDDG ++ defsFromAssign).distinct

    if (defs.nonEmpty) {
      println(s"  Receiver defined by:")
      defs.foreach(d => println(s"     - $d"))
    } else {
      println(s"  [!] No data flow found for $receiverVarBase (possibly inter-procedural or unresolved)")
    }

  } else {
    println(s"  → Direct call, no receiver variable")

    try {
      val src = cpg.call.codeExact(callCode)
      val flows = src.reachableByFlows(src).l
      if (flows.nonEmpty) {
        println("  → Forward flows:")
        flows.foreach { path =>
          path.elements.foreach { e => println(s"     - ${e.code}") }
        }
      } else {
        println(s"  [!] No forward data flow from $callCode")
      }
    } catch {
      case e: Exception =>
        println(s"  [!] Error analyzing data flow: ${e.getMessage}")
    }

    try {
      val parent = call.astParent
      println(s"  ← Parent AST node: ${parent.code}")
    } catch {
      case e: Exception =>
        println("  [!] Error getting parent node")
    }
  }
}
