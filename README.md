# CRYPTBARA

Dependency-Guided Detection of Python Cryptographic API Misuses


## Prerequisites (Environment Setup)

To reproduce CRYPTBARA, ensure the following system environment and dependencies are properly configured.

### System Requirements

* **OS**: Linux or macOS (Tested on macOS 12 / Ubuntu 20.04)
* **Python**: 3.8+
* **Java**: 11+ (required for Joern)
* **Shell**: Bash
* **Internet connection** (required for LLM-based detection)

---

### Python Environment Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

> If `requirements.txt` is missing, install manually:

```bash
pip install pandas tqdm openai
```

---

### Joern Installation (Static Analysis Engine)

Joern is used to extract intra-procedural data flows from Python source code.

```bash
# Download installer (latest version)
curl -L -o joern-install.sh https://github.com/joernio/joern/releases/latest/download/joern-install.sh
chmod +x joern-install.sh

# Run installer interactively
./joern-install.sh --interactive

# Add to PATH (if installed in default location)
echo 'export PATH=$PATH:$HOME/bin/joern' >> ~/.zshrc
source ~/.zshrc
```

---

### OpenAI API Key Setup (Optional for LLM Inference)

```bash
export OPENAI_API_KEY="sk-..."
```

> If the key is not provided, LLM-based detection will be automatically skipped.

---

## 🦫 How to Run CRYPTBARA

###  Option 1: Full Pipeline (Recommended)

This automatically creates a session tag and runs the full process.

```bash
bash run.sh
```

* Performs static analysis (Joern + AST) and LLM detection
* Automatically creates a session ID (e.g., `20250528_123456`)
* All outputs are saved under `run_results/{SESSION_TAG}/`

---

###  Option 2: Use a Specific Session (Reproducibility)

```bash
bash run.sh --session=20250528_211228
```

You can also run components independently:

```bash
# Static analysis only (Joern + AST)
bash shell/run_all.sh --session=20250528_211228

# LLM-based detection only
bash shell/run_llm.sh --session=20250528_211228

# Run LLM inference for a single file (debug/testing)
python3 llm/run_llm_experiments.py <target_name> 20250528_211228
```

---

### Output Directory Structure

```
run_results/
  └── {SESSION_TAG}/
       ├── outputs/           # Static analysis outputs (Joern + AST)
       └── outputs_llm/       # LLM detection results
```

> Logs are stored in the `logs/` directory with timestamps.

