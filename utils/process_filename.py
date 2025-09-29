import os
import shutil
from pathlib import Path
import sys

def flatten_py_files(source_dir, flat_dir="target"):
    os.makedirs(flat_dir, exist_ok=True)
    seen = set()

    for file in Path(source_dir).rglob("*.py"):
        # Retain a hint of the original path (last 4 components)
        parts = file.parts[-4:]
        flat_name = "_".join(part.replace(".py", "") for part in parts) + ".py"

        # Prevent name collisions
        original = flat_name
        counter = 1
        while flat_name in seen or os.path.exists(Path(flat_dir) / flat_name):
            name, ext = os.path.splitext(original)
            flat_name = f"{name}_{counter}{ext}"
            counter += 1

        seen.add(flat_name)
        shutil.copy(file, Path(flat_dir) / flat_name)
        print(f"[+] Copied: {file} → {flat_dir}/{flat_name}")

if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "target_files"
    flatten_py_files(source)
