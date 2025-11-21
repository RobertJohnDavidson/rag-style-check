import os
import random
import json
import glob
from datetime import datetime
from google import genai
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
    files = glob.glob(os.path.join(JSON_DATA_DIR, "*.json"))
    if not files:
        raise ValueError(f"No JSON files found in {JSON_DATA_DIR}")
    
    selected_files = random.sample(files, min(num_rules, len(files)))
    rules = []
    
    for file_path in selected_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if entry.get("type") == "term":
                    rules.append(entry)
                    
    random.shuffle(rules)
    return rules[:num_rules]

def generate_test_cases(client, rule):
    print(f"Generating tests for rule: {rule.get('term')}...")
    
    # --- IMPROVED PROMPT ---
    # We use "Few-Shot" examples to teach the LLM exactly what we want.
    prompt = f"""
    You are a QA Data Generator. Your job is to create TRICKY but FAIR test cases to evaluate a Style Guide Checker.

    ### INPUT DATA
    TERM: "{rule.get('term')}"
    DEFINITION: "{rule.get('definition')}"
    NEGATIVE CONSTRAINTS (The Errors): {rule.get('negative_constraints', [])}
    CONTEXT TAG: "{rule.get('context_tag', 'General')}"

    ### TASK
    Generate exactly 3 test cases in JSON format:

    1. **TYPE: VIOLATION**
       - The sentence MUST contain one of the 'Negative Constraints'.
       - It should look like a natural sentence a journalist might write.
       - expected_violation: true

    2. **TYPE: COMPLIANCE**
       - The sentence MUST use the **TERM** correctly as per the definition.
       - It must NOT contain the negative constraint.
       - expected_violation: false

    3. **TYPE: AMBIGUOUS / IRRELEVANT**
       - The sentence should contain the word, but in a context where the rule DOES NOT apply.
       - OR use a generic word that looks similar but isn't the specific term.
       - Example: If the rule is for "Apple" (the company), an ambiguous sentence is "I ate an apple."
       - expected_violation: false

    ### EXAMPLES (For Reference)
    
    Input Rule: "Livestream" (one word). Negative: "live stream".
    Output:
    [
      {{ "text": "I will watch the live stream tomorrow.", "expected_violation": true, "test_type": "violation", "reason": "Uses two words 'live stream'" }},
      {{ "text": "The livestream was interrupted.", "expected_violation": false, "test_type": "compliance", "reason": "Uses correct one-word spelling" }},
      {{ "text": "Fish swim in the live stream near the woods.", "expected_violation": false, "test_type": "ambiguous", "reason": "Refers to a body of water, not video" }}
    ]

    ### YOUR OUTPUT
    Generate the JSON for the INPUT DATA provided above.
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.6, # Lower temp = less creative, more rule-following
                "max_output_tokens": 2048,
            }
        )
        
        tests = json.loads(response.text)
        
        # --- SANITY CHECK ---
        # Ensure the LLM didn't hallucinate the booleans
        clean_tests = []
        for t in tests:
            if t['test_type'] == 'violation':
                t['expected_violation'] = True
            else:
                t['expected_violation'] = False
            clean_tests.append(t)
            
        return clean_tests

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
        
        for t in tests:
            # Enrich with metadata for the evaluator
            t["target_rule"] = rule.get("term")
            t["target_url"] = rule.get("url")
            t["rule_context"] = rule.get("context_tag")
            
        all_tests.extend(tests)

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_tests, f, indent=2)
    
    print(f"Generated {len(all_tests)} test cases. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()