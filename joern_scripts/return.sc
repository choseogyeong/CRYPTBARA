import io.joern.dataflowengineoss.language._
implicit val resolver = toExtendedCfgNode _

// --- Load cryptographic class names from file ---
val classFilePath = "./utils/filtered_classes.txt"
val targetClasses = scala.io.Source.fromFile(classFilePath)
  .getLines()
  .map(_.trim)
  .filter(_.nonEmpty)
  .toList

// --- Identify API calls to target cryptographic functions ---
val calleeFuncs = cpg.call.filter { call =>
  targetClasses.exists(cls => call.methodFullName.contains(cls))
}.method.name.distinct.l.toSet

// --- Begin full inter- and intra-procedural flow analysis ---
calleeFuncs.foreach { calleeFunc =>
  println(s"\n[+] Callee Function: $calleeFunc")

  val callers = cpg.call.nameExact(calleeFunc).method.fullName.distinct.l

  if (callers.nonEmpty) {
    println(s"[i] '$calleeFunc' is invoked by other functions (inter-procedural case)")

    // Analyze each caller of this callee
    cpg.call.nameExact(calleeFunc).foreach { call =>
      val callerMethod = Option(call.method.fullName).getOrElse("unknown")
      val callCode = call.code
      val args = call.argument.l.map(_.code)

      println(s"\n→ Caller Function: $callerMethod")
      println(s"   - Call: $callCode")
      println(s"   - Arguments: ${args.mkString(", ")}")

      // Backward dependency tracing of each argument
      args.foreach { argCode =>
        val defs = cpg.identifier.nameExact(argCode).ddgIn.code.distinct.l
        if (defs.nonEmpty) {
          println(s"     → Definition(s) of argument '$argCode':")
          defs.foreach(d => println(s"       - $d"))
        }
      }
    }
  } else {
    println(s"[✓] '$calleeFunc' is a root-level function (no external callers)")
    println(s"[→] Performing intra-procedural analysis...")

    // Perform simple intra-procedural analysis
    cpg.method.nameExact(calleeFunc).call.foreach { call =>
      val callCode = call.code
      val args = call.argument.code.l
      println(s"   - Call: $callCode")
      println(s"   - Arguments: ${args.mkString(", ")}")
    }
  }

  // --- Return Value Analysis ---
  println(s"\n[↩] Return Value Analysis for: $calleeFunc")
  val returnExprs = cpg.method.nameExact(calleeFunc).ast.isReturn.astChildren.code.l
  if (returnExprs.nonEmpty) {
    println(s"  → Return expression(s):")
    returnExprs.foreach(expr => println(s"     - $expr"))
  } else {
    println(s"  [!] No return expression found in '$calleeFunc'")
  }

  // Check if return values are assigned to variables
  val callExprs = cpg.call.nameExact(calleeFunc)
  val assignedVars = callExprs.inAssignment.target.code.distinct.l

  if (assignedVars.nonEmpty) {
    println(s"  → Return value assigned to variable(s):")
    assignedVars.foreach(v => println(s"     - $v"))

    // Try fallback: track how those variables are later used (assignment-based)
    assignedVars.foreach { varName =>
      val fallbackUsages = cpg.assignment.where(_.source.codeExact(varName)).target.code.distinct.l
      if (fallbackUsages.nonEmpty) {
        println(s"  → Usage(s) of variable '$varName' (via assignment):")
        fallbackUsages.foreach(u => println(s"     - $u"))
      } else {
        println(s"  → Variable '$varName' is not used afterwards")
      }
    }
  } else {
    println(s"  [!] No variable was assigned the return value of '$calleeFunc'")
  }
}
