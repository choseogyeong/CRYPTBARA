#!/usr/bin/env python3

import re
import os
import sys
from collections import defaultdict

def normalize_func_name(name: str) -> str:
    """Remove Joern-specific module prefixes."""
    name = name.strip()
    name = name.replace(":<module>.", "").replace("<module>.", "")
    return name

def is_valid_function(name: str) -> bool:
    """Filter out non-function or irrelevant Joern function names."""
    return (
        not name.startswith("<operator>")
        and not name.startswith("<unknown")
        and not name.startswith("__builtin")
        and "/" not in name
        and not name.endswith(".py")
    )

def parse_joern_log(text: str):
    """Parse Joern caller → callee logs and return an edge dictionary."""
    edges = defaultdict(list)
    pattern = re.compile(r"CALLER: (?P<caller>.*?) \| CALLEE: (?P<callee>.*?) \|")
    for match in pattern.finditer(text):
        caller = normalize_func_name(match.group("caller"))
        callee = normalize_func_name(match.group("callee"))
        if is_valid_function(caller) and is_valid_function(callee):
            edges[caller].append(callee)
    return edges

def build_call_chains(edges, start="main", path=None, visited=None, results=None):
    """Recursively build call chains from caller→callee edges."""
    if path is None:
        path = []
    if visited is None:
        visited = set()
    if results is None:
        results = []

    path.append(start)
    visited.add(start)

    if start not in edges or not edges[start]:
        results.append(" → ".join(path))
    else:
        for callee in edges[start]:
            if callee not in visited:
                build_call_chains(edges, callee, list(path), visited.copy(), results)

    return results

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 generate_call_tree.py <target_name>")
        sys.exit(1)

    target_name = sys.argv[1]

    # Session tag support (optional)
    SESSION_TAG = os.environ.get("SESSION_TAG") or ""
    OUTPUT_BASE = f"run_results/{SESSION_TAG}/outputs" if SESSION_TAG else "outputs"

    log_file = f"{OUTPUT_BASE}/{target_name}/joern/caller_callee_trace_output.txt"
    output_file = f"{OUTPUT_BASE}/{target_name}/function_call_chains.txt"

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if not os.path.exists(log_file):
        print(f"[!] Error: Log file not found at '{log_file}'")
        sys.exit(1)

    with open(log_file, "r") as f:
        log_text = f.read()

    edges = parse_joern_log(log_text)
    results = build_call_chains(edges, start="<module>")

    # Fallback: try roots not called by anyone
    if not results and edges:
        potential_roots = set(edges.keys()) - set(callee for callees in edges.values() for callee in callees)
        if potential_roots:
            all_results = []
            for root in potential_roots:
                all_results.extend(build_call_chains(edges, start=root))
            results = all_results

    with open(output_file, "w") as out:
        if results:
            out.write("\n".join(results))
        else:
            out.write("No valid function call chains found.")

    print(f"[+] Function call chains for '{target_name}' saved to '{output_file}'")
    return 0

if __name__ == "__main__":
    sys.exit(main())
