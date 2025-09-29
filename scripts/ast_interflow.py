#!/usr/bin/env python3
import ast
import json
import sys
import os
from collections import defaultdict

class ASTInterproceduralDependencyExtractor(ast.NodeVisitor):
    def __init__(self):
        self.functions = {}  # function_name -> FunctionDef node
        self.call_map = defaultdict(list)  # function_name -> list of called functions
        self.assignments = {}  # variable_name -> function_name (where it was assigned)
        self.return_vars = defaultdict(list)  # function_name -> returned variable names
        self.inter_flow = defaultdict(lambda: {
            "returns": [],
            "used_by": [],
            "hardcoded_constants": []
        })
        self.current_function = None

    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.functions[node.name] = node
        self.generic_visit(node)
        self.current_function = None

    def visit_Return(self, node):
        if isinstance(node.value, ast.Name):
            self.return_vars[self.current_function].append(node.value.id)
            self.inter_flow[self.current_function]["returns"].append(node.value.id)
        elif isinstance(node.value, ast.Tuple):
            for elt in node.value.elts:
                if isinstance(elt, ast.Name):
                    self.return_vars[self.current_function].append(elt.id)
                    self.inter_flow[self.current_function]["returns"].append(elt.id)
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Track function call assignments
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id in self.functions:
                assigned_func = node.value.func.id
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.assignments[target.id] = assigned_func
            elif isinstance(node.value.func, ast.Attribute):
                func_base = node.value.func.value
                if isinstance(func_base, ast.Name):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.assignments[target.id] = f"{func_base.id}.{node.value.func.attr}"

        # Extract hardcoded constants
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if isinstance(node.value, ast.Constant):
                    value = node.value.value
                    try:
                        json.dumps(value)  # Ensure it's serializable
                        self.inter_flow[self.current_function]["hardcoded_constants"].append({
                            "variable": var_name,
                            "value": value,
                            "type": type(value).__name__,
                            "lineno": node.lineno
                        })
                    except TypeError:
                        self.inter_flow[self.current_function]["hardcoded_constants"].append({
                            "variable": var_name,
                            "value": str(value),
                            "type": type(value).__name__,
                            "lineno": node.lineno
                        })
        self.generic_visit(node)

    def visit_Call(self, node):
        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                callee = f"{node.func.value.id}.{node.func.attr}"

        if callee:
            self.call_map[self.current_function].append(callee)
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    arg_name = arg.id
                    if arg_name in self.assignments:
                        origin_func = self.assignments[arg_name]
                        self.inter_flow[origin_func]["used_by"].append({
                            "variable": arg_name,
                            "used_in": f"{callee}({arg_name})",
                            "used_by": self.current_function
                        })
                elif isinstance(arg, ast.Attribute):
                    if isinstance(arg.value, ast.Name):
                        arg_name = arg.value.id
                        if arg_name in self.assignments:
                            origin_func = self.assignments[arg_name]
                            self.inter_flow[origin_func]["used_by"].append({
                                "variable": arg_name,
                                "used_in": f"{callee}({arg.attr})",
                                "used_by": self.current_function
                            })
        self.generic_visit(node)

    def extract(self, source_code):
        tree = ast.parse(source_code)
        self.visit(tree)
        return dict(self.inter_flow)

    def save_to_json(self, data, path: str):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 ast_interflow.py <file_path> <target_name>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    target_name = sys.argv[2]
    
    # Get session tag (from env or default)
    session_tag = os.environ.get("SESSION_TAG", "default")
    output_dir = f"run_results/{session_tag}/outputs/{target_name}/ast"
    output_path = f"{output_dir}/interprocedural_dependencies.json"
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        with open(file_path) as f:
            code = f.read()
    except FileNotFoundError:
        print(f"[!] Error: File not found: {file_path}")
        with open(output_path, "w") as f:
            json.dump({}, f)
        sys.exit(1)

    extractor = ASTInterproceduralDependencyExtractor()
    result = extractor.extract(code)
    extractor.save_to_json(result, output_path)
    print(f"[✓] AST analysis complete. Results saved to: {output_path}")

if __name__ == "__main__":
    main()
