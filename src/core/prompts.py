# --- PROMPT TEMPLATES ---

STYLE_CATEGORIES = (
   "- **Capitalization**: Case rules (titles, government, academic, business terms, etc.).\n"
   "- **Punctuation**: Ellipses, brackets, quotation marks, commas, hyphens.\n"
   "- **Spelling**: Preferred spellings, compound words, Canadian vs U.S. variants.\n"
   "- **Grammar**: Possessives, verb agreement, clause distinction.\n"
   "- **Numbers**: Digits vs text, measurements, currency, percentages.\n"
   "- **Dates & Time**: Months, years, days, time formatting.\n"
   "- **Geography**: Place names, regions, demonyms, abbreviations for locations.\n"
   "- **Titles & Ranks**: Military ranks, royal titles, job titles, honorifics.\n"
   "- **Abbreviations**: Acronyms, initialisms (e.g. UN, U.S.).\n"
   "- **Formatting**: Italics, bolding, lists.\n"
   "- **Usage & Diction**: Word choice distinctions (e.g. \"lay vs lie\"), jargon, redundancy.\n"
   "- **Proper Names**: Specific names of people, organizations, or entities (e.g. \"Zelenskyy\", \"RCMP\").\n"
   "- **Bias & Sensitivity**: Inclusive language, preferred terminology for groups.\n"
)

PROMPT_QUERY_GEN = (
    "You are an expert Copy Editor. Generate {num_queries} specific search queries "
    "to find style rules relevant to the following text. "
    "Your goal is to identify potential violations in these specific categories:\n"
    f"{STYLE_CATEGORIES}"
    "Generate queries focusing on the specific terms, capitalization, spelling, or punctuation issues. "
    "Do NOT include generic phrases like 'style guide' in your queries.\n"
    "Text: {query}"
)

PROMPT_CLASSIFY_TAGS = """
Classify the following text into one or more of these specific style categories: {tags_list_str}.
Return ONLY the category titles (text before any colon) as a comma-separated list. If none apply, return "General".

Text: "{text_snippet}"
"""

PROMPT_AUDIT_SYSTEM = """You are an expert Copy Editor for CBC News with agentic capabilities.
Review the entire paragraph below and flag every rule violation you can find.

CRITICAL INSTRUCTIONS:
1. TEMPORAL GROUNDING: 
   - Accept the paragraph's timeline as factual. 
   - Do NOT flag dates in the future (e.g., Nov 2024) or political appointments (e.g., Mark Carney) as errors unless they violate a STYLE rule (e.g., "Use 'Nov.' instead of 'November'").
   - Your role is STYLE, not FACT-CHECKING.
   
2. Apply rules LITERALLY based on the guideline text, not rule interpretations.
   - Read the full guideline text carefully.
   - Only flag violations that explicitly match the guideline.
   - If the text already matches the guideline requirement, DO NOT flag it.
   
   EXAMPLE: If rule says "Use 'Alberta Government' (capitalized)" and text says "Alberta Government", this is CORRECT - do NOT flag it.
   EXAMPLE: If rule says "Use 'oilsands'" and text says "tarsands", this IS a violation.

3. Do NOT over-generalize or extrapolate.
   - Rules about specific terms apply only to those exact terms.
   - Do NOT invent additional cases.

4. Verify each violation:
   - Is the text in the paragraph exactly what the guideline says to change?
   - Would fixing it actually improve compliance with the rule?
   - If the text is already correct per the guideline, skip it.

5. Avoid reporting duplicates.

6. Confidence:
   - Set "confident": true only if you have reviewed all rules and are certain.
   - Set "confident": false if unsure or rules seem incomplete.

7. Context:
   - If you need more rules, set "needs_more_context": true and provide "additional_queries".
"""

PROMPT_AUDIT_USER_TEMPLATE = """
USER PARAGRAPH:
"{paragraph}"

--- RETRIEVED RULES (reference by rule_id) ---
{context_block}

{reflection_block}
"""

PROMPT_GENERATE_NEWS_TEXT = (
    "Write a single, neutral, high-quality news paragraph about a timely and realistic topic "
    "The paragraph should be approximately 3-5 sentences long and written in a professional journalistic style. It should be in the style of CBC News."
    "Focus on clear, concise, and objective reporting."
)
