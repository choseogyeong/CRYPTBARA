#!/usr/bin/env python3

import sys
import os
import subprocess
import tempfile

def fix_joern_script(content):
    """Patch Joern script to fix type-related errors (e.g., resolver type declaration)."""
    return content.replace(
        "implicit val resolver = io.joern.dataflowengineoss.language.toExtendedCfgNode _",
        "implicit val resolver: io.joern.dataflowengineoss.language.ExtendedCfgNode => io.joern.dataflowengineoss.language.ExtendedCfgNode = io.joern.dataflowengineoss.language.toExtendedCfgNode"
    )

def run_joern_script(script_content, target_file, output_file):
    """Run a Joern script with importCode dynamically injected."""
    script_content = fix_joern_script(script_content)

    # Dynamically insert importCode for the target file
    import_statement = f'importCode("{os.path.abspath(target_file)}")\n'
    full_script = import_statement + script_content

    with tempfile.NamedTemporaryFile(suffix=".sc", delete=False) as temp_file:
        temp_file.write(full_script.encode('utf-8'))
        temp_file_path = temp_file.name

    try:
        cmd = f'joern --script {temp_file_path}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        with open(output_file, 'w') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\n--- ERRORS ---\n")
                f.write(result.stderr)

        return True

    except Exception as e:
        print(f"    × Failed to execute Joern script: {str(e)}")
        with open(output_file, 'w') as f:
            f.write(f"ERROR: {str(e)}")
        return False

    finally:
        os.unlink(temp_file_path)

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 run_joern_script.py <file_path> <target_name> [session_tag]")
        sys.exit(1)

    file_path = sys.argv[1]
    target_name = sys.argv[2]
    session_tag = sys.argv[3] if len(sys.argv) > 3 else "default"

    output_dir = f"run_results/{session_tag}/outputs/{target_name}/joern"
    os.makedirs(output_dir, exist_ok=True)

    script_dir = "joern_scripts"
    script_files = ["caller_callee_trace.sc", "receiver_trace.sc", "return.sc"]

    all_success = True
    for script_file in script_files:
        script_path = os.path.join(script_dir, script_file)
        output_file = os.path.join(output_dir, f"{os.path.splitext(script_file)[0]}_output.txt")

        print(f"    → Running {script_file} on {file_path}")

        try:
            with open(script_path, 'r') as f:
                script_content = f.read()

            success = run_joern_script(script_content, file_path, output_file)
            all_success = all_success and success

        except Exception as e:
            print(f"    × Error processing {script_file}: {str(e)}")
            all_success = False

    sys.exit(0 if all_success else 1)

if __name__ == "__main__":
    main()
