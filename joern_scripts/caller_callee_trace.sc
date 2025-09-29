import io.joern.dataflowengineoss.language._
implicit val resolver = toExtendedCfgNode _

// importCode will be injected dynamically from run_joern_script.py

cpg.call.l.foreach { call =>
  val methodOpt = Option(call.method).map(_.name).getOrElse("<module>")
  val callee = call.methodFullName
  val code = call.code
  val line = call.lineNumber.getOrElse(-1)
  println(s"CALLER: $methodOpt | CALLEE: $callee | CODE: $code | LINE: $line")
}
