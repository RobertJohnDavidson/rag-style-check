from typing import List, Dict, Tuple
from src.utils import find_span_indices

def nodes_to_dicts(nodes, source_type="retrieved") -> List[Dict]:
    """Convert LlamaIndex TextNodes to simple dictionaries."""
    out = []
    for node in nodes:
        # Safely access metadata
        meta = node.metadata or {}
        out.append({
            "term": meta.get('term', 'Untitled Rule'),
            "text": meta.get('display_text', node.get_content()),
            "url": meta.get('url', ''),
            "score": node.score or 0.0,
            "source_type": source_type,
            "id": f"RULE_{node.node.node_id[:8]}"
        })
    return out

def format_violations(pydantic_violations, paragraph: str, contexts: List[Dict]) -> List[Dict]:
    """Convert Pydantic violations to Dicts with indices."""
    formatted = []
    context_map = {c['id']: c for c in contexts}
    
    for v in pydantic_violations:
        start, end = find_span_indices(paragraph, v.text)
        
        # Enrich with source info
        rule_info = context_map.get(v.rule_id, {})
        
        formatted.append({
            "text": v.text,
            "violation": v.explanation,
            "correction": v.suggested_fix,
            "rule_id": v.rule_id,
            "rule_name": v.rule_name or rule_info.get('term'),
            "url": v.url or rule_info.get('url'),
            "paragraph": paragraph,
            "start_index": start,
            "end_index": end
        })
    return formatted
