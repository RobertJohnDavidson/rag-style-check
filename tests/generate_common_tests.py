import re
import json
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
from dotenv import load_dotenv
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core import Settings
from src.prompts import COMMON_RULES

# Load environment variables
load_dotenv()

# Configure LLM
MODEL = os.getenv("MODEL", "models/gemini-1.5-flash")
PROJECT_NAME = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION", "us-central1")

if not PROJECT_NAME:
    # Fallback or error, but let's assume env is set if running in this context
    pass

def configure_llm():
    Settings.llm = GoogleGenAI(
        model=MODEL,
        vertexai_config={
            "project": PROJECT_NAME,
            "location": REGION
        },
        temperature=0.8
    )

def parse_rules(common_rules_text):
    """Parses the COMMON_RULES string into a list of rule dictionaries."""
    rules = []
    lines = common_rules_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith("- **"):
            # Try to match with Source
            match = re.match(r"- \*\*(.*?)\*\*: (.*?) \(Source: (.*?)\)", line)
            if match:
                name = match.group(1)
                desc = match.group(2)
                url = match.group(3)
                rules.append({"name": name, "description": desc, "url": url})
            else:
                # Fallback without Source
                match = re.match(r"- \*\*(.*?)\*\*: (.*)", line)
                if match:
                    name = match.group(1)
                    desc = match.group(2)
                    rules.append({"name": name, "description": desc, "url": None})
    return rules

def generate_test_case(rule):
    """Generates a test case for a single rule using the LLM."""
    prompt = f"""
    You are a QA engineer generating test data for a Style Guide Auditor.
    
    TARGET RULE:
    Name: {rule['name']}
    Description: {rule['description']}
    
    TASK:
    Generate a single test case that specifically violates this rule.
    
    OUTPUT FORMAT (JSON ONLY):
    {{
        "target_rule": "{rule['name']}",
        "text": "A sentence containing the error.",
        "expected_violation": true,
        "target_url": "{rule['url'] if rule['url'] else ''}"
    }}
    
    Do not include markdown formatting like ```json. Just the raw JSON string.
    """
    
    try:
        response = Settings.llm.complete(prompt).text.strip()
        if response.startswith("```json"):
            response = response.replace("```json", "").replace("```", "")
        elif response.startswith("```"):
            response = response.replace("```", "")
            
        return json.loads(response)
    except Exception as e:
        print(f"Error generating test for '{rule['name']}': {e}")
        return None

def generate_common_tests_file(output_path="tests/generated_tests_common.json"):
    configure_llm()
    print("Parsing rules from src/prompts.py...")
    rules = parse_rules(COMMON_RULES)
    print(f"Found {len(rules)} rules.")
    
    generated_tests = []
    
    print("Generating test cases (this may take a moment)...")
    # Limit to first 10 for speed in this demo, or maybe all? 
    # The user didn't specify a limit, but generating for ALL rules might take a long time.
    # I'll generate for all but add a small delay.
    
    for i, rule in enumerate(rules):
        print(f"[{i+1}/{len(rules)}] Generating test for: {rule['name']}")
        test_case = generate_test_case(rule)
        if test_case:
            generated_tests.append(test_case)
        
        time.sleep(0.5)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(generated_tests, f, indent=2)
        
    print(f"\n✅ Successfully generated {len(generated_tests)} test cases.")
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    generate_common_tests_file()
