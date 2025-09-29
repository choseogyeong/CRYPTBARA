#!/usr/bin/env python3

import os
import csv
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True, help="Session tag (e.g., 20240525_2300)")
    parser.add_argument("--base", default=".", help="Base project directory (default: current directory)")
    args = parser.parse_args()

    session_tag = args.session
    base_dir = args.base  # default = current directory
    llm_base_dir = os.path.join(base_dir, "run_results", session_tag, "outputs_llm")
    out_csv = os.path.join(base_dir, f"results_{session_tag}_llm_summary.csv")

    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["target", "verdict"])

        for target_dir in sorted(os.listdir(llm_base_dir)):
            target_path = os.path.join(llm_base_dir, target_dir)
            c1_path = os.path.join(target_path, "C1")
            final_decision_path = os.path.join(c1_path, "final_decision.txt")

            if not os.path.exists(final_decision_path):
                verdict = "missing"
            else:
                with open(final_decision_path, "r") as dec_file:
                    content = dec_file.read().strip()
                    lines = [line for line in content.splitlines() if "Final Decision" in line]
                    if lines:
                        decision = lines[0].split(":")[-1].strip().lower()
                        verdict = "misuse" if decision == "vuln" else "safe"
                    else:
                        verdict = "invalid"

            writer.writerow([target_dir, verdict])

    print(f"[✓] LLM summary saved to: {out_csv}")

if __name__ == "__main__":
    main()
