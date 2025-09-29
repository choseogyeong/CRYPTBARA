#!/usr/bin/env python3
import json
import os
import sys
import re

def parse_receiver_trace(path):
    """Parse receiver_trace_output.txt and return {function: [receivers]}"""
    receivers = {}
    current_func = None

    if not os.path.exists(path):
        return receivers

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()

            # 함수 위치 추출
            match_func = re.match(r'\[\+\] Call: .*?@ line \d+ in (.*)', line)
            if match_func:
                current_func = match_func.group(1).strip()
                if current_func not in receivers:
                    receivers[current_func] = []
                continue

            # 리시버 정보 추출
            match_recv = re.match(r'→ Receiver: (\w+) \(code: .*?, base: (.*?)\)', line)
            if match_recv and current_func:
                receiver = match_recv.group(1).strip()
                base = match_recv.group(2).strip()
                receivers[current_func].append(f"{receiver} (base: {base})")

    return receivers



def merge_results(target_name):
    SESSION_TAG = os.environ.get("SESSION_TAG", "")
    OUTPUT_BASE = f"run_results/{SESSION_TAG}/outputs" if SESSION_TAG else "outputs"

    formatted_path = f"{OUTPUT_BASE}/{target_name}/joern/formatted_result.json"
    inter_path = f"{OUTPUT_BASE}/{target_name}/ast/interprocedural_dependencies.json"
    output_path = f"{OUTPUT_BASE}/{target_name}/merged_results.json"
    skipped_targets_path = f"{OUTPUT_BASE}/skipped_targets.txt"
    receiver_path = f"{OUTPUT_BASE}/{target_name}/joern/receiver_trace_output.txt"
    receiver_map = parse_receiver_trace(receiver_path)

    formatted = {}
    inter = {}

    # Check if formatted_result.json exists
    if not os.path.exists(formatted_path):
        print(f"[!] Skipping {target_name} (formatted_result.json not found)")
        with open(skipped_targets_path, "a") as skip_log:
            skip_log.write(f"{target_name}\n")
        return

    # Load formatted result
    try:
        with open(formatted_path) as f:
            formatted = json.load(f)
    except json.JSONDecodeError:
        print(f"[!] Failed to parse {formatted_path}")

    # Load interprocedural dependencies
    if os.path.exists(inter_path):
        try:
            with open(inter_path) as f:
                inter = json.load(f)
        except json.JSONDecodeError:
            print(f"[!] Failed to parse {inter_path}")

    # Merge both results
    for func, inter_data in inter.items():
        if func not in formatted:
            formatted[func] = {
                "function": func,
                "ast": [],
                "returns": {
                    "expressions": [],
                    "assigned_vars": [],
                    "usages": []
                },
                "callers": [],
                "callee_trace": []
            }
        if func in receiver_map:
            formatted[func]["receivers"] = receiver_map[func]
        
        formatted[func]["interprocedural"] = {
            "returns": inter_data.get("returns", []),
            "used_by": inter_data.get("used_by", [])
        }
        if "hardcoded_constants" in inter_data:
            formatted[func]["hardcoded_constants"] = inter_data["hardcoded_constants"]

    # Save merged result
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(formatted, f, indent=2)

    # Skip if merged content is still empty
    if not formatted:
        print(f"[!] Skipping {target_name} (merged content is empty)")
        with open(skipped_targets_path, "a") as skip_log:
            skip_log.write(f"{target_name}\n")
        return

    print(f"[✓] Merged result saved at: {output_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 merge.py <target_name>")
        sys.exit(1)

    target_name = sys.argv[1]
    merge_results(target_name)

if __name__ == "__main__":
    main()
