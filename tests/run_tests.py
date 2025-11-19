import json
import time
import os
from src import StyleAuditor
from dotenv import load_dotenv
from datetime import datetime
# Load environment variables
load_dotenv()

TEST_FILE = "tests/generated_tests.json"
RESULTS_DIR = "tests/results_history"
MODEL = os.getenv("MODEL")
TOP_K = 3  # Match the retriever setting in audit.py
THRESHOLD = 0.48  # Match the confidence threshold in audit.py

def normalize_url(url):
    """Strips protocol and www to compare URLs reliably."""
    if not url: return ""
    return url.replace("https://", "").replace("http://", "").replace("www.", "").split("#")[0].strip("/")

def save_results(stats, detailed_logs, report_text):
    """Saves both JSON data and Text report to disk."""
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save JSON (Data for future comparison)
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
        
    # 2. Save Text Report (Readable summary)
    txt_filename = f"{RESULTS_DIR}/report_{timestamp}_{MODEL}.txt"
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n💾 Results saved to:\n   - {json_filename}\n   - {txt_filename}")

def run_evaluation():
    print(f"Initializing Auditor ({MODEL})...")
    auditor = StyleAuditor()
    
    if not os.path.exists(TEST_FILE):
        print(f"❌ Test file not found: {TEST_FILE}")
        return

    with open(TEST_FILE, 'r') as f:
        test_cases = json.load(f)
    
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
        """Helper to print to console and save to text report"""
        print(message)
        console_output.append(message)

    log(f"\n🧪 Running {len(test_cases)} tests...\n")
    
    for i, test in enumerate(test_cases):
        text = test.get('text', test.get('original_text'))
        expected_violation = test.get('expected_violation', True)
        target_url = normalize_url(test.get('target_url', test.get('url', '')))
        
        # 1. Run Audit
        detections = auditor.check_text(text)
        is_flagged = len(detections) > 0
        stats["total"] += 1

        # Log entry structure
        log_entry = {
            "id": i + 1,
            "text": text,
            "expected_violation": expected_violation,
            "flagged": is_flagged,
            "outcome": "UNKNOWN",
            "details": ""
        }

        log(f"Test #{i+1}: {text[:60]}...")

        # SCENARIO A: Expected a Violation
        if expected_violation:
            if is_flagged:
                stats["correct_violation_detection"] += 1
                
                # Check Citation
                cited_correctly = False
                found_urls = []
                for d in detections:
                    citation = normalize_url(d.get('source_url', ''))
                    found_urls.append(citation)
                    if citation == target_url:
                        cited_correctly = True
                        break
                
                if cited_correctly:
                    stats["correct_rule_citation"] += 1
                    log("   ✅ PASS (Detected & Cited Correctly)")
                    log_entry["outcome"] = "PASS"
                else:
                    stats["wrong_rule_cited"] += 1
                    log(f"   ⚠️ DETECTED BUT WRONG RULE")
                    log(f"      Expected: {target_url}")
                    log(f"      Got: {found_urls}")
                    log_entry["outcome"] = "PARTIAL_FAIL"
                    log_entry["details"] = f"Wrong citation. Got {found_urls}"
            else:
                stats["false_negatives"] += 1
                log("   ❌ FAIL (Missed Violation)")
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
                log(f"   ❌ FAIL (False Positive)")
                log(f"      Flagged for: {violation_msg}")
                log_entry["outcome"] = "FAIL"
                log_entry["details"] = f"False positive: {violation_msg}"

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
        f"Timestamp:        {datetime.now().isoformat()}",
        f"Total Tests:      {stats['total']}",
        f"Precision:        {precision:.2f} (Trustworthiness)",
        f"Recall:           {recall:.2f} (Safety)",
        f"Citation Acc:     {citation_acc:.2f} (Retrieval Quality)",
        f"Confidence Thrshld: {THRESHOLD}",
        f"Retriever Top K:    {TOP_K}",
        f"Model used as evaluator: {MODEL}",
        "-" * 20,
        f"✅ Correct Detection: {stats['correct_violation_detection']}",
        f"🎯 Exact Rule Match:  {stats['correct_rule_citation']}",
        f"⚠️ Wrong Rule Cited:  {stats['wrong_rule_cited']}",
        f"❌ False Positives:   {stats['false_positives']}",
        f"❌ Missed Errors:     {stats['false_negatives']}",
        separator
    ]

    full_report_text = "\n".join(console_output + final_report)
    
    # Print the summary to console
    print("\n".join(final_report))

    # Save to disk
    save_results(stats, detailed_logs, full_report_text)

if __name__ == "__main__":
    run_evaluation()