"""
Test case generator for the style checker.
Generates tests from CBC articles or synthetic paragraphs with injected errors.
"""

import random
import asyncio
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.config import settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core import Settings, QueryBundle
from llama_index.core.retrievers import VectorIndexRetriever

# Import reranker
from src.core.reranker import VertexAIRerank


def fetch_cbc_article_text(url: str) -> List[str]:
    """Scrapes paragraph text from a CBC article URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.google.com/',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        paragraphs = []
        
        content_div = (
            soup.find('div', class_='story') or 
            soup.find('article') or 
            soup.find('div', class_='sc-content')
        )
        
        if content_div:
            for p in content_div.find_all('p'):
                text = p.get_text().strip()
                if len(text) > 50: 
                    paragraphs.append(text)
        
        return paragraphs
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article: {e}")
        return []


def generate_synthetic_paragraph(topic: str) -> str:
    """Asks LLM to write a clean paragraph on a topic."""
    llm = GoogleGenAI(
        model=settings.DEFAULT_MODEL,
        vertexai_config={
            "project": settings.PROJECT_ID,
            "location": settings.LLM_REGION
        },
        temperature=0.7
    )
    
    prompt = f"Write a single, neutral news paragraph about {topic}. It should be around 3-4 sentences long. Do not include any obvious style errors yet."
    return llm.complete(prompt).text.strip()


def retrieve_relevant_rules(text: str, retriever: VectorIndexRetriever, reranker=None, top_k: int = 15) -> List[Dict]:
    """Retrieve relevant style guide rules from vector DB."""
    # Simple full-text retrieval matching Auditor's approach
    # Note: Auditor uses async aretrieve, but this runs in a thread pool so sync retrieve is fine.
    
    # 1. Retrieve
    nodes = retriever.retrieve(text)
    
    # 2. Rerank
    if nodes and reranker:
        try:
            query_bundle = QueryBundle(query_str=text)
            nodes = reranker.postprocess_nodes(nodes=nodes, query_bundle=query_bundle)
        except Exception as e:
            print(f"Reranking failed: {e}")
            nodes = nodes[:top_k]
    
    # 3. Filter and Format
    rules = []
    for node in nodes:
        score = getattr(node, 'score', 0)
        if score >= settings.DEFAULT_RERANK_SCORE_THRESHOLD:
            rules.append({
                "term": node.metadata.get('term', 'Unknown Rule'),
                "text": node.metadata.get('display_text', node.get_content()),
                "url": node.metadata.get('url', ''),
                "score": score
            })
            
    # Sort by score descending
    rules.sort(key=lambda x: x['score'], reverse=True)
    
    return rules[:top_k]


def inject_errors(text: str, num_errors: int, retriever: VectorIndexRetriever, reranker) -> Dict[str, Any]:
    """Injects style errors into text and returns test case."""
    llm = GoogleGenAI(
        model=settings.DEFAULT_MODEL,
        vertexai_config={
            "project": settings.PROJECT_ID,
            "location": settings.LLM_REGION
        },
        temperature=0.9
    )
    
    rules = retrieve_relevant_rules(text, retriever, reranker, top_k=20)
    
    if len(rules) < num_errors:
        num_errors = len(rules)
    
    selected_rules = random.sample(rules, num_errors)
    
    rule_descriptions = "\n".join([
        f"- {r['term']} (URL: {r.get('url', 'N/A')}): {r['text']}"
        for r in selected_rules
    ])
    
    prompt = f"""You are a test generator for a CBC style checker. Given the following paragraph and style rules, introduce exactly {num_errors} violations into the text.

Original paragraph:
{text}

Style rules to violate:
{rule_descriptions}

Instructions:
1. Introduce exactly {num_errors} violations, one for each rule listed
2. Make violations subtle but clear
3. Keep the text natural and readable
4. Return ONLY a JSON object with this structure:
{{
  "text": "modified paragraph with violations",
  "expected_violations": [
    {{
      "rule": "rule name",
      "text": "specific text that violates",
      "reason": "why this violates the rule",
      "link": "URL from the rule above"
    }}
  ]
}}"""
    
    response = llm.complete(prompt).text.strip()
    
    # Parse JSON response
    import json
    try:
        if response.startswith("```json"):
            response = response.split("```json")[1].split("```")[0].strip()
        elif response.startswith("```"):
            response = response.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response)
        
        # Ensure all violations have required fields (add link if missing)
        if "expected_violations" in result:
            for i, violation in enumerate(result["expected_violations"]):
                # Match violation to original rule to get correct link
                if "link" not in violation or not violation["link"]:
                    # Try to find matching rule by name
                    rule_name = violation.get("rule", "")
                    matching_rule = next((r for r in selected_rules if r["term"].lower() in rule_name.lower()), None)
                    if matching_rule:
                        violation["link"] = matching_rule.get("url", "")
                    else:
                        # Fallback to first rule's URL if no match
                        violation["link"] = selected_rules[i % len(selected_rules)].get("url", "") if selected_rules else ""
        
        return result
    except json.JSONDecodeError:
        # Return empty test with proper structure
        return {
            "text": text,
            "expected_violations": []
        }


async def generate_test_from_article(url: str, retriever: VectorIndexRetriever, reranker) -> Dict[str, Any]:
    """Generate a test case from a CBC article."""
    # Run blocking operation in thread pool
    paragraphs = await asyncio.to_thread(fetch_cbc_article_text, url)
    
    if not paragraphs:
        raise ValueError("Could not fetch article or no content found")
    
    # Pick a random paragraph
    text = random.choice(paragraphs)
    
    # Inject 2-4 errors
    num_errors = random.randint(2, 4)
    result = await asyncio.to_thread(inject_errors, text, num_errors, retriever, reranker)
    
    return {
        "label": f"Article test - {url.split('/')[-1][:30]}",
        "text": result["text"],
        "expected_violations": result["expected_violations"]
    }


async def generate_synthetic_tests(count: int, retriever: VectorIndexRetriever, reranker) -> List[Dict[str, Any]]:
    """Generate synthetic test cases."""
    topics = [
        "politics and government policy",
        "technology and innovation", 
        "sports and athletics",
        "health and medical research",
        "environment and climate",
        "business and economy",
        "education and schools",
        "crime and justice",
        "arts and entertainment",
        "science and discovery"
    ]
    
    tests = []
    
    for _ in range(count):
        topic = random.choice(topics)
        num_errors = random.randint(1, 4)
        
        # Run blocking LLM call in thread pool
        clean_text = await asyncio.to_thread(generate_synthetic_paragraph, topic)
        
        if num_errors == 0:
            result = {"text": clean_text, "expected_violations": []}
        else:
            # Run blocking error injection in thread pool
            result = await asyncio.to_thread(inject_errors, clean_text, num_errors, retriever, reranker)
        
        tests.append({
            "label": f"Synthetic test - {topic}",
            "text": result["text"],
            "expected_violations": result["expected_violations"]
        })
    
    return tests
