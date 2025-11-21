import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# --- CONFIGURATION ---
MODEL = os.getenv("MODEL")
PROJECT_NAME = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION", "us-central1")
STYLE_GUIDE_PATH = "full_style_guide.md"

if not PROJECT_NAME:
    raise ValueError("PROJECT_NAME not found in environment variables.")

class AgentStyleAuditor:
    def __init__(self):
        if not os.path.exists(STYLE_GUIDE_PATH):
            raise FileNotFoundError(f"Style guide file not found: {STYLE_GUIDE_PATH}")
        
        with open(STYLE_GUIDE_PATH, "r", encoding="utf-8") as f:
            self.style_guide_content = f.read()
            
        print(f"✅ AgentStyleAuditor initialized with {len(self.style_guide_content)} chars of context.")
        
        self.client = genai.Client(
            vertexai=True, 
            project=PROJECT_NAME, 
            location=REGION
        )

    def check_text(self, text):
        """
        Audits the entire text block at once using the full context window.
        """
        print(f"\n🔍 Auditing text block ({len(text)} chars) (Agent Mode)...")
        
        prompt = f"""
        You are an expert Copy Editor for CBC News.
        You have access to the full CBC News Style Guide below.
        
        Check the User Text against the Style Guide.
        
        STYLE GUIDE:
        {self.style_guide_content}
        
        USER TEXT: 
        "{text}"

        TASK:
        Identify ALL violations in the text.
        Return a JSON list of objects.
        If no violations are found, return an empty list [].

        JSON SCHEMA:
        [
            {{
                "sentence": "The specific sentence or phrase that is wrong",
                "violation_explanation": "Why it is wrong",
                "correction": "Corrected version",
                "cited_rule_name": "The exact name of the rule from the style guide",
                "cited_url": "The URL of the rule if available in the text (or null)"
            }}
        ]
        
        Return ONLY raw JSON. No markdown blocks.
        """

        try:
            response = self.client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                    "labels": {"usage": "style_audit_agent"}
                }
            
            )
            
            results = json.loads(response.text)
            
            # Map to expected output format for compatibility
            mapped_results = []
            for res in results:
                mapped_results.append({
                    "sentence": res.get("sentence"),
                    "violation": res.get("violation_explanation"),
                    "correction": res.get("correction"),
                    "source_url": res.get("cited_url", ""),
                    "rule_name": res.get("cited_rule_name", "Unknown Rule"),
                    "rule_context": res.get("cited_rule_name", "Unknown Rule")
                })
                
            return mapped_results

        except Exception as e:
            print(f"Error calling GenAI: {e}")
            return []
