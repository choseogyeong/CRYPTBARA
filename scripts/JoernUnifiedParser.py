#!/usr/bin/env python3
import re
import json
import os
import sys
from collections import defaultdict
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def is_crypto_import_present(log_path, class_list):
    """Check if cryptographic libraries are imported in the caller/callee log."""
    if not os.path.exists(log_path):
        return False
    with open(log_path, "r") as f:
        content = f.read()
        for cls in class_list:
            if f"import(, {cls})" in content or f"import({cls}" in content:
                return True
    return False

class JoernUnifiedParser:
    def __init__(self):
        self.result = defaultdict(lambda: {
            "function": "",
            "callee_trace": []
        })
    
    def parse_receiver_trace_log(self, text: str):
        """Extract receiver variables per function from receiver_trace_output.txt."""
        current_func = None
        for line in text.splitlines():
            line = line.strip()

            # Extract function context
            match_func = re.match(r'\[\+\] Call: .*?@ line \d+ in (.*)', line)
            if match_func:
                current_func = match_func.group(1).strip()
                if not current_func.startswith(":"):
                    current_func = f":{current_func}"
                self.result[current_func]["function"] = current_func
                if "receivers" not in self.result[current_func]:
                    self.result[current_func]["receivers"] = []
                continue

            # Extract receiver info
            match_recv = re.match(r'→ Receiver: (\w+) \(code: .*?, base: (.*?)\)', line)
            if match_recv and current_func:
                receiver = match_recv.group(1).strip()
                base = match_recv.group(2).strip()
                self.result[current_func]["receivers"].append(f"{receiver} (base: {base})")

    def parse_caller_callee_log(self, text: str):
        """Extract callee and code context from Joern caller/callee trace log."""
        pattern = re.compile(r"CALLER: .*? \| CALLEE: (?P<callee>.*?) \| CODE: (?P<code>.*?) \| LINE: \d+")
        for match in pattern.finditer(text):
            callee = match.group("callee").strip()
            code = match.group("code").strip()
            self.result[callee]["function"] = callee
            self.result[callee]["callee_trace"].append({"code": code})

    def save_to_json(self, path: str):
        """Save the formatted result as JSON."""
        with open(path, "w") as f:
            json.dump(self.result, f, indent=2)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 JoernUnifiedParser.py <target_name>")
        sys.exit(1)

    session_tag = os.environ.get("SESSION_TAG", "default")
    base_dir = f"run_results/{session_tag}/outputs"
    skipped_log_path = os.path.join(base_dir, "skipped_targets_joern.txt")

    # Load filtered cryptographic class names
    filtered_classes_path = os.path.join(SCRIPT_DIR, "..", "utils", "filtered_classes.txt")

    class_list = []
    if os.path.exists(filtered_classes_path):
        with open(filtered_classes_path, 'r') as f:
            class_list = [line.strip() for line in f if line.strip()]

    target_name = sys.argv[1]
    joern_dir = os.path.join(base_dir, target_name, "joern")
    caller_log = os.path.join(joern_dir, "caller_callee_trace_output.txt")
    output_path = os.path.join(joern_dir, "formatted_result.json")

    # Skip if no crypto-related import is found
    if not is_crypto_import_present(caller_log, class_list):
        print(f"[!] Skipping {target_name} (no crypto import found)")
        with open(skipped_log_path, "a") as skip_log:
            skip_log.write(f"{target_name}\n")
        return

    parser = JoernUnifiedParser()

    if os.path.exists(caller_log):
        with open(caller_log) as f:
            parser.parse_caller_callee_log(f.read())

    receiver_log = os.path.join(joern_dir, "receiver_trace_output.txt")
    if os.path.exists(receiver_log):
        with open(receiver_log) as f:
            parser.parse_receiver_trace_log(f.read())

    print(f"[+] Saving formatted result for {target_name}")
    parser.save_to_json(output_path)
    print(f"[✓] Saved at: {output_path}")

if __name__ == "__main__":
    main()
