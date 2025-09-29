import os
import sys
import subprocess
import json
from collections import Counter

EXPERIMENTS = {
    "C1": {
        "desc": "Code + Rule + Call Chain",
        "template": "C1.txt",
        "requires": ["code", "rule", "merged", "call_chain"]
    }
}

RULES_DIR = "llm/rules"
TEMPLATE_DIR = "llm/templates"
SRC_DIR = "target"

def resolve_session_tag(cli_session_tag=None):
    if cli_session_tag:
        return cli_session_tag
    return os.environ.get("SESSION_TAG") or "default"

API_KEY = os.environ.get("OPENAI_API_KEY")

def majority_vote(results):
    count = Counter(results)
    most_common, freq = count.most_common(1)[0]
    return most_common if freq >= 2 else 'UNCERTAIN'

def run_experiment(target_name, experiment_key, session_tag):
    run_results_dir = f"run_results/{session_tag}"
    merged_base = os.path.join(run_results_dir, "outputs")
    llm_output_base = os.path.join(run_results_dir, "outputs_llm")
    skipped_log_path = os.path.join(merged_base, "skipped_targets_llm.txt")

    os.makedirs(merged_base, exist_ok=True)
    os.makedirs(llm_output_base, exist_ok=True)

    config = EXPERIMENTS[experiment_key]
    print(f"\n[→] Running {experiment_key} ({config['desc']}) for {target_name} [Session: {session_tag}]")

    target_file = os.path.join(SRC_DIR, f"{target_name}.py")
    merged_file = os.path.join(merged_base, target_name, "merged_results.json")
    call_chain = os.path.join(merged_base, target_name, "function_call_chains.txt")
    output_dir = os.path.join(llm_output_base, target_name, experiment_key)

    if not os.path.exists(merged_file):
        print(f"[!] Skipping {target_name} (missing merged_results.json)")
        with open(skipped_log_path, "a") as skip_log:
            skip_log.write(f"{target_name}\n")
        return False

    os.makedirs(output_dir, exist_ok=True)
    print(f"[+] Output directory created: {output_dir}")

    cmd = [
        "python3", "llm/llm_detector.py",
        "--target", target_name,
        "--source", target_file,
        "--rules", RULES_DIR,
        "--templates", TEMPLATE_DIR,
        "--output", output_dir,
        "--experiment", experiment_key,
        "--merged", merged_file,
        "--call_chain", call_chain
    ]

    if API_KEY:
        cmd += ["--api-key", API_KEY]

    decision_results = []
    repeat_count = 5  # Number of repetitions

    for i in range(repeat_count):
        print(f"[→] Repetition {i+1}/{repeat_count}")
        print(f"[+] Executing: {' '.join(cmd)}")
        subprocess.run(cmd, text=True)

        base_result = os.path.join(output_dir, "llm_results.json")
        run_result = os.path.join(output_dir, f"llm_results_run{i+1}.json")

        if os.path.exists(base_result):
            os.rename(base_result, run_result)
            with open(run_result, "r") as f:
                data = json.load(f)
                decision = "vuln" if data.get("misuses") else "safe"
                decision_results.append(decision)
        else:
            print(f"[!] No llm_results.json found after run {i+1}")
            if i == 0:
                with open(skipped_log_path, "a") as skip_log:
                    skip_log.write(f"{target_name}\n")
                return False

    if decision_results:
        final_decision = majority_vote(decision_results)
        print(f"[✓] Final Decision: {final_decision}")
        with open(os.path.join(output_dir, "final_decision.txt"), "w") as f:
            f.write("Repetition Results:\n")
            for idx, res in enumerate(decision_results, start=1):
                f.write(f"{idx}: {res}\n")
            f.write(f"\nFinal Decision: {final_decision}\n")
    else:
        print("[!] No valid results collected for majority vote")

    return True

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 run_llm_experiments.py <target_name> <experiment_key> <session_tag>")
        sys.exit(1)

    target_name = sys.argv[1]
    experiment_key = sys.argv[2]
    session_tag = resolve_session_tag(sys.argv[3])

    experiment_key = "C1"
    success = run_experiment(target_name, experiment_key, session_tag)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
