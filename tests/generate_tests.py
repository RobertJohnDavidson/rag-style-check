import os
import random
import json
import glob
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Configuration
JSON_DATA_DIR = os.getenv("JSON_DATA_DIR")
OUTPUT_FILE = "tests/generated_tests.json"
YOUR_PROJECT_ID = os.getenv("PROJECT")
YOUR_LOCATION = os.getenv("REGION", "us-central1")
MODEL = os.getenv("MODEL")

NUM_RULES_TO_TEST = 20


def get_random_rules(num_rules):
    # Read JSON files instead of TXT
    files = glob.glob(os.path.join(JSON_DATA_DIR, "*.json"))
    if not files:
        raise ValueError(f"No JSON files found in {JSON_DATA_DIR}")
    
    selected_files = random.sample(files, min(num_rules, len(files)))
    rules = []
    
    for file_path in selected_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle list or dict
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                # Only test "Terms" not "Policies" for now (easier to test)
                if entry.get("type") == "term":
                    rules.append(entry)
                    
    # Shuffle and pick N rules from the loaded set
    random.shuffle(rules)
    return rules[:num_rules]

def generate_test_cases(client, rule):
    print(f"Generating tests for rule: {rule.get('term')}...")
    
    # Prompt designed for your specific RAG structure
    prompt = f"""
    You are a QA Engineer generating test cases for a Style Guide Auditor.
    
    RULE TO TEST:
    Term: "{rule.get('term')}"
    Definition: "{rule.get('definition')}"
    Negative Constraints (What to avoid): {rule.get('negative_constraints', [])}
    
    TASK:
    Generate 3 distinct test sentences:
    1. [VIOLATION]: A sentence that explicitly violates the rule (uses a negative constraint).
    2. [COMPLIANCE]: A sentence that uses the term correctly.
    3. [AMBIGUOUS]: A sentence using a similar word or context that should NOT trigger the rule (to test false positives).
    
    OUTPUT JSON FORMAT:
    [
      {{
        "text": "The sentence text",
        "expected_violation": true/false,
        "test_type": "violation" | "compliance" | "ambiguous",
        "expected_correction": "The corrected text (if violation)"
      }},
      ...
    ]
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "max_output_tokens": 8192,
              }
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating: {e}")
        return []

def main():
    client = genai.Client(
        vertexai=True, 
        project=YOUR_PROJECT_ID, 
        location=YOUR_LOCATION
    )
    
    rules = get_random_rules(NUM_RULES_TO_TEST)
    all_tests = []
    
    for rule in rules:
        tests = generate_test_cases(client, rule)
        # Enrich with rule metadata for the evaluator
        for t in tests:
            t["target_rule"] = rule.get("term")
            t["target_url"] = rule.get("url")
        all_tests.extend(tests)

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_tests, f, indent=2)
    
    print(f"Generated {len(all_tests)} test cases.")

if __name__ == "__main__":
    main()