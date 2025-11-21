import json
import os
import argparse
import random
from src.audit import StyleAuditor 
from src.agent_audit import AgentStyleAuditor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TEST_FILE = "tests/generated_tests.json"
RESULTS_DIR = "tests/results_history"
MODEL = os.getenv("MODEL")
TOP_K = 3
THRESHOLD = 0.48

def normalize_url(url):
    if not url: return ""
    return url.replace("https://", "").replace("http://", "").replace("www.", "").split("#")[0].strip("/")

def save_results(stats, detailed_logs, report_text):
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{RESULTS_DIR}/eval_{timestamp}_{MODEL}.json"
    json_data = {
        "meta": {
            "model": MODEL,
            "timestamp": timestamp,
            "top_k": TOP_K,
            "threshold": THRESHOLD
        },
        "stats": stats,
        "detailed_logs": detailed_logs
    }
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
        
    txt_filename = f"{RESULTS_DIR}/report_{timestamp}_{MODEL}.txt"
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n💾 Results saved to:\n   - {json_filename}")

def run_evaluation(limit=None, randomize=False, use_agent=False):
    if use_agent:
        print(f"🚀 Initializing Agent Auditor ({MODEL})...")
        auditor = AgentStyleAuditor()
    else:
        print(f"🚀 Initializing RAG Auditor ({MODEL})...")
        auditor = StyleAuditor()
    
    if not os.path.exists(TEST_FILE):
        print(f"❌ Test file not found: {TEST_FILE}")
        return

    with open(TEST_FILE, 'r') as f:
        test_cases = json.load(f)
    
    if randomize:
        print("🎲 Randomizing test selection...")
        random.shuffle(test_cases)
        
    if limit:
        print(f"✂️ Limiting to {limit} tests...")
        test_cases = test_cases[:limit]
    
    stats = {
        "total": 0,
        "correct_violation_detection": 0,
        "correct_rule_citation": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "wrong_rule_cited": 0
    }
    
    detailed_logs = []
    console_output = []

    def log(message):
        print(message)
        console_output.append(message)

    log(f"\n🧪 Running {len(test_cases)} tests...\n")
    
    for i, test in enumerate(test_cases):
        text = test.get('text', test.get('original_text'))
        expected_violation = test.get('expected_violation', True)
        target_url = normalize_url(test.get('target_url', test.get('url', '')))
        target_term = test.get('target_rule', 'Unknown Term') 
        
        # 1. Run Audit
        detections = auditor.check_text(text)
        is_flagged = len(detections) > 0
        stats["total"] += 1

        log_entry = {
            "id": i + 1,
            "text": text,
            "expected_violation": expected_violation,
            "flagged": is_flagged,
            "outcome": "UNKNOWN",
            "details": "",
            "detected_rules": []
        }

        log(f"Test #{i+1}: {text[:60]}...")

        # SCENARIO A: Expected a Violation
        if expected_violation:
            if is_flagged:
                stats["correct_violation_detection"] += 1
                
                cited_correctly = False
                found_info = [] # Store tuples of (url, name)

                for d in detections:
                    citation = normalize_url(d.get('source_url', ''))
                    rule_name = d.get('rule_name', 'Unknown') # <--- NEW: Get Rule Name
                    
                    found_info.append(f"{rule_name} ({citation})")
                    
                    log_entry["detected_rules"].append({
                        "url": citation,
                        "rule_name": rule_name,
                        "violation_text": d.get('violation')
                    })

                    if citation == target_url:
                        cited_correctly = True
                        break 
                
                if cited_correctly:
                    stats["correct_rule_citation"] += 1
                    log(f"   ✅ PASS")
                    # Print the name of the rule we found
                    log(f"      Matched: {rule_name}") 
                    log_entry["outcome"] = "PASS"
                else:
                    stats["wrong_rule_cited"] += 1
                    log(f"   ⚠️ DETECTED BUT WRONG RULE")
                    log(f"      Expected: {target_term}")
                    log(f"      Got: {found_info}")
                    log_entry["outcome"] = "PARTIAL_FAIL"
                    log_entry["details"] = f"Wrong citation. Got {found_info}"
            else:
                stats["false_negatives"] += 1
                log(f"   ❌ FAIL (Missed Violation: {target_term})")
                log_entry["outcome"] = "FAIL"
                log_entry["details"] = "Missed violation"

        # SCENARIO B: Expected Compliance
        else:
            if not is_flagged:
                stats["correct_violation_detection"] += 1
                log("   ✅ PASS (Correctly Ignored)")
                log_entry["outcome"] = "PASS"
            else:
                stats["false_positives"] += 1
                violation_msg = detections[0].get('violation', 'Unknown')
                cited_rule = detections[0].get('rule_name', 'Unknown') # <--- NEW
                
                log(f"   ❌ FAIL (False Positive)")
                log(f"      Flagged as: {cited_rule}")
                log(f"      Reason: {violation_msg}")
                log_entry["outcome"] = "FAIL"
                log_entry["details"] = f"False positive on {cited_rule}"

        detailed_logs.append(log_entry)

    # --- METRICS ---
    total_flags = stats["correct_violation_detection"] + stats["false_positives"]
    precision = stats["correct_violation_detection"] / total_flags if total_flags > 0 else 0

    total_actual_errors = stats["correct_violation_detection"] + stats["false_negatives"] + stats["wrong_rule_cited"]
    recall = stats["correct_violation_detection"] / total_actual_errors if total_actual_errors > 0 else 0

    citation_acc = 0
    if stats["correct_violation_detection"] > 0:
        citation_acc = stats["correct_rule_citation"] / stats["correct_violation_detection"]

    # --- FINAL REPORT ---
    separator = "=" * 40
    final_report = [
        "\n" + separator,
        f"📊 FINAL EVALUATION REPORT ({MODEL})",
        separator,
        f"Total Tests:      {stats['total']}",
        f"Precision:        {precision:.2f} (Trustworthiness)",
        f"Recall:           {recall:.2f} (Safety)",
        f"Citation Acc:     {citation_acc:.2f} (Retrieval Quality)",
        "-" * 20,
        f"✅ Correct Detection: {stats['correct_violation_detection']}",
        f"🎯 Exact Rule Match:  {stats['correct_rule_citation']}",
        f"⚠️ Wrong Rule Cited:  {stats['wrong_rule_cited']}",
        f"❌ False Positives:   {stats['false_positives']}",
        f"❌ Missed Errors:     {stats['false_negatives']}",
        separator
    ]

    full_report_text = "\n".join(console_output + final_report)
    print("\n".join(final_report))
    save_results(stats, detailed_logs, full_report_text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit tests")
    parser.add_argument("--random", action="store_true", help="Randomize")
    parser.add_argument("--agent", action="store_true", help="Use Agent Auditor instead of RAG")
    args = parser.parse_args()
    
    run_evaluation(limit=args.limit, randomize=args.random, use_agent=args.agent)