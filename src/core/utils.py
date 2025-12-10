def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    return "".join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()

def find_span_indices(paragraph: str, snippet: str):
    """Find start and end indices of a snippet within a paragraph."""
    if not snippet:
        return None, None

    idx = paragraph.find(snippet)
    if idx == -1:
        lower_idx = paragraph.lower().find(snippet.lower())
        if lower_idx == -1:
            return None, None
        return lower_idx, lower_idx + len(snippet)

    return idx, idx + len(snippet)

def deduplicate_violations(violations: list) -> list:
    """Remove duplicate violations based on text span and location."""
    seen = set()
    deduplicated = []
    
    for v in violations:
        # Pydantic model access vs dict access handling
        # If v is a Pydantic model, use model_dump or attribute access
        # Assuming dicts or objects with get/getattr equivalent is handled by caller or we make this robust.
        # For now, let's assume these are Pydantic models or Dicts passed in final stage.
        
        # Helper to get attr/item
        def get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        text = get(v, 'text', '')
        start = get(v, 'start_index')
        end = get(v, 'end_index')
        para = get(v, 'paragraph', '')

        text_normalized = normalize_text(text)
        key = (text_normalized, start, end, para)
        
        if key not in seen and text_normalized:
            seen.add(key)
            deduplicated.append(v)
    
    return deduplicated
