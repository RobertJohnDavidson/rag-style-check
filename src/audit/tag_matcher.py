
import ahocorasick
from typing import List, Tuple, Set

class TagMatcher:
    """
    Efficiently matches multiple string patterns in text using Aho-Corasick algorithm.
    Used for rapid identification of rule triggers (including multi-word terms).
    """

    def __init__(self):
        self.automaton = ahocorasick.Automaton()
        self.is_built = False

    def build(self, triggers: List[Tuple[str, str]]):
        """
        Builds the Aho-Corasick automaton from a list of (rule_id, trigger_text) tuples.
        
        Args:
            triggers: List of tuples where:
                - matching_text (str): The text to match (will be lowercased)
                - rule_id (str): The ID of the rule associated with this trigger
        """
        self.automaton = ahocorasick.Automaton()
        count = 0
        for rule_id, text in triggers:
            if text:
                # Store rule_id as the value associated with the key
                self.automaton.add_word(text.lower(), rule_id)
                count += 1
        
        self.automaton.make_automaton()
        self.is_built = True
        return count

    def find_matches(self, text: str) -> Set[str]:
        """
        Finds all rule IDs present in the text.
        
        Returns:
            Set[str]: A set of unique rule_ids found in the text.
        """
        if not self.is_built:
            return set()
        
        found_rule_ids = set()
        
        # iter() returns tuples of (end_index, value)
        # value is what we stored in add_word (the rule_id)
        for _, rule_id in self.automaton.iter(text.lower()):
            found_rule_ids.add(rule_id)
            
        return found_rule_ids
