import re
import os
import json
import glob

def build_common_rules():
    # Define the mapping of categories to file patterns or specific files
    # Based on the user's request and the file list I saw earlier
    category_map = {
        "CAPITALIZATION": ["home_c_capitalization.json", "home_t_titles.json", "home_g_geography_cities.json", "home_c_courts.json", "home_a_academic_terms.json", "home_g_government_terms.json"], # Note: some filenames are guesses, will use glob for broader search if needed
        "PUNCTUATION": ["home_p_punctuation*.json", "home_e_ellipses.json", "home_q_quotation_marks.json", "home_p_possessive_apostrophe.json"],
        "NUMBERS": ["home_n_numbers.json", "home_m_money.json"],
        "SPELLING": ["home_s_spelling.json", "home_s_spelling_*.json"],
        "HYPHENS": ["home_h_hyphens.json", "home_c_compound_words.json"], # Hyphens often in spelling or specific files
        "GRAMMAR": ["home_v_verb_agreement.json", "home_t_that_versus_which.json", "home_w_who_versus_whom.json"],
        "PLACES": ["home_c_cities.json", "home_p_provinces_and_cities.json", "home_u_united_states.json"],
        "MISC": ["home_t_the_versus_the.json", "home_u_united_nations.json", "home_r_royal_titles.json", "home_m_military_ranks.json", "home_p_police_forces.json"]
    }

    # Specific terms to look for if file matching is too broad
    target_terms = [
        "capitalization", "titles", "government", "academic", "business", "geographic", "court",
        "ellipsis", "brackets", "quotation marks", "possessive", "italics",
        "numbers", "money", "currency",
        "toward", "skeptical", "OK", "travelling", "labelling", "acknowledgment", "Zelenskyy", "defence", "ton", "tonne",
        "The vs. the", "cities", "states", "countries", "Canadian spelling", "U.S. spelling",
        "royal titles", "military ranks", "police", "RCMP",
        "dates", "months", "1960s",
        "UN", "commas", "hyphens"
    ]

    data_dir = os.path.join("data")
    all_files = glob.glob(os.path.join(data_dir, "*.json"))
    
    extracted_rules = []

    # Helper to find file by partial name
    def find_files(pattern):
        return [f for f in all_files if pattern in os.path.basename(f)]

    # 1. Capitalization
    cap_files = []
    for pattern in category_map["CAPITALIZATION"]:
        if "*" in pattern:
            cap_files.extend(glob.glob(os.path.join(data_dir, pattern)))
        else:
            # Try exact match first, then partial
            exact = os.path.join(data_dir, pattern)
            if os.path.exists(exact):
                cap_files.append(exact)
            else:
                # Fallback to finding by partial name if exact file not found
                # This handles the "guesses" mentioned in the comment
                partial_name = pattern.replace(".json", "").replace("home_", "")
                cap_files.extend(find_files(partial_name))
    
    extracted_rules.append(extract_from_files("CAPITALIZATION", cap_files, target_terms))

    # 2. Punctuation
    punc_files = []
    for pattern in category_map["PUNCTUATION"]:
        if "*" in pattern:
            punc_files.extend(glob.glob(os.path.join(data_dir, pattern)))
        else:
            exact = os.path.join(data_dir, pattern)
            if os.path.exists(exact):
                punc_files.append(exact)
            else:
                partial_name = pattern.replace(".json", "").replace("home_", "")
                punc_files.extend(find_files(partial_name))

    extracted_rules.append(extract_from_files("PUNCTUATION", punc_files, target_terms))

    # 3. Numbers
    num_files = []
    for pattern in category_map["NUMBERS"]:
        if "*" in pattern:
            num_files.extend(glob.glob(os.path.join(data_dir, pattern)))
        else:
            exact = os.path.join(data_dir, pattern)
            if os.path.exists(exact):
                num_files.append(exact)
            else:
                partial_name = pattern.replace(".json", "").replace("home_", "")
                num_files.extend(find_files(partial_name))

    extracted_rules.append(extract_from_files("NUMBERS", num_files, target_terms))

    # 4. Spelling & Hyphens
    spell_files = []
    for pattern in category_map["SPELLING"] + category_map["HYPHENS"]:
        if "*" in pattern:
            spell_files.extend(glob.glob(os.path.join(data_dir, pattern)))
        else:
            exact = os.path.join(data_dir, pattern)
            if os.path.exists(exact):
                spell_files.append(exact)
            else:
                partial_name = pattern.replace(".json", "").replace("home_", "")
                spell_files.extend(find_files(partial_name))

    extracted_rules.append(extract_from_files("SPELLING & HYPHENS", spell_files, target_terms))

    # 5. Dates & Time (Adding a category for this if not in map, or using MISC)
    # The user didn't explicitly put DATES in the map above, but listed it in target_terms.
    # I'll add a manual lookup for dates/time files similar to before.
    date_files = find_files("dates") + find_files("time") + find_files("months")
    extracted_rules.append(extract_from_files("DATES & TIME", date_files, target_terms))

    # 6. Places & Misc
    place_files = []
    for pattern in category_map["PLACES"] + category_map["MISC"]:
        if "*" in pattern:
            place_files.extend(glob.glob(os.path.join(data_dir, pattern)))
        else:
            exact = os.path.join(data_dir, pattern)
            if os.path.exists(exact):
                place_files.append(exact)
            else:
                partial_name = pattern.replace(".json", "").replace("home_", "")
                place_files.extend(find_files(partial_name))

    extracted_rules.append(extract_from_files("PLACES & MISC", place_files, target_terms))

    # 7. Grammar
    gram_files = []
    for pattern in category_map["GRAMMAR"]:
        if "*" in pattern:
            gram_files.extend(glob.glob(os.path.join(data_dir, pattern)))
        else:
            exact = os.path.join(data_dir, pattern)
            if os.path.exists(exact):
                gram_files.append(exact)
            else:
                partial_name = pattern.replace(".json", "").replace("home_", "")
                gram_files.extend(find_files(partial_name))

    extracted_rules.append(extract_from_files("GRAMMAR", gram_files, target_terms))

    # Combine
    final_text = "COMMON_RULES = \"\"\"\n" + "\n\n".join(extracted_rules) + "\n\"\"\""
    
    with open("src/prompts.py", "w", encoding="utf-8") as f:
        f.write(final_text)
    
    print("Successfully rebuilt src/prompts.py from data files.")

def extract_from_files(category_name, file_paths, keywords):
    content_block = f"### {category_name}\n"
    seen_terms = set()
    
    for fp in file_paths:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict): data = [data]
                
                for item in data:
                    term = item.get("term", "")
                    definition = item.get("definition", "")
                    negatives = item.get("negative_constraints", [])
                    
                    # Simple keyword filter to keep the prompt size manageable
                    # If keywords is empty, take everything (careful!)
                    # For now, we take it if the term matches a keyword OR if it's a high-value file
                    
                    if term in seen_terms: continue

                    # Check if term matches any of the target keywords (case-insensitive)
                    # Or if the term is in the target_terms list directly
                    is_relevant = False
                    term_lower = term.lower()
                    
                    # If no keywords provided, assume all content in this file is relevant (e.g. specific file selected)
                    if not keywords:
                        is_relevant = True
                    else:
                        for k in keywords:
                            # Use regex word boundary check to avoid "un" matching "under"
                            # Escape the keyword to handle special chars like "." in "U.S."
                            pattern = r'\b' + re.escape(k) + r'\b'
                            if re.search(pattern, term, re.IGNORECASE) or re.search(pattern, definition, re.IGNORECASE):
                                is_relevant = True
                                break
                    
                    if not is_relevant:
                        continue
                    clean_def = definition.replace("\n", " ").strip()
                    if len(clean_def) > 300: clean_def = clean_def[:300] + "..."
                    
                    url = item.get("url", "")

                    entry = f"- **{term}**: {clean_def}"
                    if url:
                        entry += f" (Source: {url})"
                    if negatives:
                        entry += f"\n  *Negative Constraints*: {', '.join(negatives)}"
                    
                    content_block += entry + "\n"
                    seen_terms.add(term)
        except Exception as e:
            print(f"Error reading {fp}: {e}")
            
    return content_block

if __name__ == "__main__":
    build_common_rules()
