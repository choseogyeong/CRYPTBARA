#!/usr/bin/env python3

import argparse
import json
import os
import sys
from openai import OpenAI
from utils import load_template, load_rules, load_json_file, save_json_file
from dotenv import load_dotenv
from pathlib import Path


project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    
client = OpenAI()

class LLMCryptoMisuseDetector:
    def __init__(self, target, source_file, merged_file, rules_dir, templates_dir, output_dir, experiment, api_key=None, call_chain=None):
        self.target = target
        self.source_file = source_file
        self.merged_file = merged_file
        self.rules_dir = rules_dir
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.experiment = experiment
        self.results = {
            "target": target,
            "source_file": os.path.basename(source_file),
            "misuses": [],
            "recommendations": [],
            "analysis_summary": ""
        }
        self.call_chain_path = call_chain

        self.load_data()

    def load_data(self):
        try:
            with open(self.source_file, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
        except Exception as e:
            print(f"[!] Failed to load source code: {str(e)}")
            self.source_code = ""

        self.merged_results = load_json_file(self.merged_file)
        self.rules_file = os.path.join(self.rules_dir, "rules.json")
        self.rules = load_rules(self.rules_file)
        self.template_file = os.path.join(self.templates_dir, f"{self.experiment}.txt")
        self.template = load_template(self.template_file)

        call_chain_file = os.path.join(os.path.dirname(self.merged_file), "function_call_chains.txt")
        try:
            with open(call_chain_file, 'r', encoding='utf-8') as f:
                self.call_chain = f.read()
        except:
            self.call_chain = "No call chain available"

    def generate_prompt(self):
        return self.template.format(
            RULE=self.rules,
            CODE=self.source_code,
            MERGED_DEPENDENCY_JSON=json.dumps(self.merged_results, indent=2),
            CALL_CHAIN=self.call_chain,
        )

    def analyze_with_llm(self, prompt):
        if not self.api_key:
            return {"error": "API key is not set."}

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "You are a security expert detecting cryptographic API misuses in code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1500
            )
            result_text = response.choices[0].message.content.strip()
            json_start = result_text.find("{")
            json_end = result_text.rfind("}")
            if json_start >= 0 and json_end >= 0:
                json_str = result_text[json_start:json_end + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return {"error": "Failed to parse LLM response as JSON.", "raw_response": result_text}
            else:
                return {"error": "No JSON found in LLM response.", "raw_response": result_text}
        except Exception as e:
            return {"error": f"Error during LLM analysis: {str(e)}"}

    def run(self):
        # Save the generated prompt for reference
        prompt = self.generate_prompt()
        prompt_path = os.path.join(self.output_dir, "prompt.txt")
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt)

        print(f"  [*] Prompt saved to {prompt_path}")
        print(f"  [*] Running LLM analysis...")
        llm_response = self.analyze_with_llm(prompt)
        raw_response_path = os.path.join(self.output_dir, "raw_response.json")
        save_json_file(llm_response, raw_response_path)

        if "error" in llm_response:
            self.results["error"] = llm_response["error"]
            if "raw_response" in llm_response:
                self.results["raw_response"] = llm_response["raw_response"]
        else:
            self.results.update({
                "misuses": llm_response.get("misuses", []),
                "recommendations": llm_response.get("recommendations", []),
                "analysis_summary": llm_response.get("analysis_summary", "")
            })

        results_path = os.path.join(self.output_dir, "llm_results.json")
        save_json_file(self.results, results_path)
        print(f"  [✓] Results saved to {results_path}")
        return self.results


def main():
    parser = argparse.ArgumentParser(description="LLM-based cryptographic misuse detector")
    parser.add_argument("--target", required=True, help="Target identifier")
    parser.add_argument("--source", required=True, help="Path to source code file")
    parser.add_argument("--merged", required=True, help="Path to merged static analysis results")
    parser.add_argument("--rules", required=True, help="Directory containing misuse rules")
    parser.add_argument("--templates", required=True, help="Directory containing prompt templates")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--api-key", help="OpenAI API key (or use environment variable)")
    parser.add_argument("--experiment", required=True, help="Experiment setting (Z1, F1, C1, C2)")
    parser.add_argument("--call_chain", help="Path to function call chain file")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    detector = LLMCryptoMisuseDetector(
        args.target, args.source, args.merged,
        args.rules, args.templates, args.output,
        args.experiment,
        args.api_key,
        args.call_chain
    )

    results = detector.run()

    if "error" in results:
        try:
            print(f"  [!] Error: {results['error']}")
        except UnicodeEncodeError:
            print("  [!] Error: (contains non-displayable Unicode characters)")
        sys.exit(1)

    try:
        print(f"  [✓] Analysis complete: {len(results['misuses'])} issue(s) found")
        for misuse in results['misuses']:
            misuse_type = misuse.get('type', 'unknown')
            description = misuse.get('description', 'no description')
            location = misuse.get('location', 'unknown location')
            print(f"    - {misuse_type}: {description} ({location})")
    except UnicodeEncodeError:
        print("  [!] Unicode error during result display. Please check the output file.")

if __name__ == "__main__":
    main()