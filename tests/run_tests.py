import json
import os
import argparse
import random
from datetime import datetime
from difflib import SequenceMatcher

from src.core.auditor import StyleAuditor
from dotenv import load_dotenv

load_dotenv()

TEST_FILE = "tests/generated_tests_complex.json"
RESULTS_DIR = "tests/results_history"
MODEL = os.getenv("MODEL", "unknown-model")

def normalize_text(text):
    """Normalize text for comparison (lower case, strip punctuation/whitespace)."""
    if not text: return ""
    return "".join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()

def is_text_match(expected, actual, threshold=0.8):
    """Check if two text spans are roughly the same."""
    norm_expected = normalize_text(expected)
    norm_actual = normalize_text(actual)
    
    if not norm_expected or not norm_actual:
        return False
        
    # Check for substring inclusion (common if LLM returns partial/full sentence)
    if norm_expected in norm_actual or norm_actual in norm_expected:
        return True
        
    # Fuzzy match
    ratio = SequenceMatcher(None, norm_expected, norm_actual).ratio()
    return ratio >= threshold

def evaluate_test_case(test_case, auditor):
    text = test_case.get('text')
    expected_violations = test_case.get('expected_violations', [])
    
    # Run Audit
    detected_violations = auditor.check_text(text)
    
    # Matching Logic
    matched_expected = set()
    matched_detected = set()
    
    matches = []
    
    # 1. Try to match every expected violation to a detected one
    for i, expected in enumerate(expected_violations):
        exp_text = expected.get('text', '')
        exp_rule = expected.get('rule', '')
        
        best_match_idx = -1
        best_match_score = 0
        
        for j, detected in enumerate(detected_violations):
            if j in matched_detected:
                continue
                
            det_text = detected.get('text', '')
            
            # Score based on text similarity
            if is_text_match(exp_text, det_text):
                # We found a text match!
                best_match_idx = j
                break # Take the first good text match
        
        if best_match_idx != -1:
            matched_expected.add(i)
            matched_detected.add(best_match_idx)
            matches.append({
                "expected": expected,
                "detected": detected_violations[best_match_idx],
                "status": "TP" # True Positive
            })
        else:
            matches.append({
                "expected": expected,
                "detected": None,
                "status": "FN" # False Negative
            })
            
    # 2. Collect any remaining detected violations as False Positives
    for j, detected in enumerate(detected_violations):
        if j not in matched_detected:
            matches.append({
                "expected": None,
                "detected": detected,
                "status": "FP" # False Positive
            })
            
    # 3. Handle True Negatives (No violations expected, none found)
    if not expected_violations and not detected_violations:
        return {
            "matches": [],
            "stats": {"TP": 0, "FP": 0, "FN": 0, "TN": 1}
        }

    # Calculate Stats for this case
    tp = sum(1 for m in matches if m['status'] == 'TP')
    fp = sum(1 for m in matches if m['status'] == 'FP')
    fn = sum(1 for m in matches if m['status'] == 'FN')
    
    return {
        "matches": matches,
        "stats": {"TP": tp, "FP": fp, "FN": fn, "TN": 0}
    }

def save_results(stats, detailed_logs, report_text):
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{RESULTS_DIR}/eval_{timestamp}_{MODEL}.json"
    
    json_data = {
        "meta": {
            "model": MODEL,
            "timestamp": timestamp
        },
        "stats": stats,
        "detailed_logs": detailed_logs
    }
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
        
    print(f"\n💾 Results saved to: {json_filename}")

def run_evaluation(test_file=TEST_FILE, limit=None):
    print(f"🚀 Initializing Auditor ({MODEL})...")
    auditor = StyleAuditor()
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return

    with open(test_file, 'r') as f:
        test_cases = json.load(f)
        
    if limit:
        test_cases = test_cases[:limit]
        
    print(f"\n🧪 Running {len(test_cases)} complex test cases...\n")
    
    global_stats = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    detailed_logs = []
    
    for i, test in enumerate(test_cases):
        print(f"Test #{i+1}: {test.get('text')[:60]}...")
        
        result = evaluate_test_case(test, auditor)
        
        # Update Global Stats
        for key in global_stats:
            global_stats[key] += result['stats'][key]
            
        # Log Details
        log_entry = {
            "id": test.get('id', i+1),
            "text": test.get('text'),
            "matches": result['matches'],
            "stats": result['stats']
        }
        detailed_logs.append(log_entry)
        
        # Print Outcome
        stats = result['stats']
        if stats['FN'] > 0:
            print(f"   ❌ Missed {stats['FN']} violation(s)")
        if stats['FP'] > 0:
            print(f"   ⚠️ {stats['FP']} False Positive(s)")
        if stats['TP'] > 0:
            print(f"   ✅ Detected {stats['TP']} violation(s)")
        if stats['TN'] > 0:
            print(f"   ✅ Correctly ignored (Clean Text)")
            
    # --- FINAL METRICS ---
    tp = global_stats['TP']
    fp = global_stats['FP']
    fn = global_stats['FN']
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print("\n" + "="*40)
    print(f"📊 FINAL REPORT ({MODEL})")
    print("="*40)
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"True Positives:   {tp}")
    print(f"False Positives:  {fp}")
    print(f"False Negatives:  {fn}")
    print(f"True Negatives:   {global_stats['TN']}")
    print("-" * 20)
    print(f"Precision: {precision:.2f}")
    print(f"Recall:    {recall:.2f}")
    print(f"F1 Score:  {f1:.2f}")
    print("="*40)
    
    save_results(global_stats, detailed_logs, "Report generated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=TEST_FILE, help="Path to test file")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    args = parser.parse_args()
    
    run_evaluation(test_file=args.file, limit=args.limit)