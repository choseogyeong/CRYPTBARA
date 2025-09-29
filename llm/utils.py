import json
import os

def load_template(template_path):
    """Load prompt template file"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[!] Failed to load template: {str(e)}")
        return ""

def load_rules(rules_path):
    """Load cryptographic usage rules"""
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return json.dumps(json.load(f), indent=2)
    except Exception as e:
        print(f"[!] Failed to load rules: {str(e)}")
        return "[]"

def load_json_file(file_path):
    """Load a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Failed to load JSON ({file_path}): {str(e)}")
        return {}

def save_json_file(data, file_path):
    """Save data to a JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[!] Failed to save JSON ({file_path}): {str(e)}")
        return False
