"""
crawl/ocr/autocorrect.py
Correct OCR errors in Indonesian text using pyspellchecker.
Preserves proper nouns and formatting where possible.
"""
import re

try:
    from spellchecker import SpellChecker
    PYSPELLCHECKER_AVAILABLE = True
except ImportError:
    PYSPELLCHECKER_AVAILABLE = False


class IndonesianAutocorrect:
    def __init__(self) -> None:
        self.spell = None
        if PYSPELLCHECKER_AVAILABLE:
            # We use the built-in Indonesian dictionary if available,
            # otherwise fallback to English (which is obviously suboptimal for ID, 
            # but this handles the missing dependency gracefully).
            try:
                self.spell = SpellChecker(language="id")
            except ValueError:
                # If 'id' dict isn't installed in this pyspellchecker version
                self.spell = SpellChecker(language="en")

    def correct_text(self, text: str) -> str:
        """Correct misspelled words while preserving punctuation and casing."""
        if not self.spell or not text.strip():
            return text

        # Split by non-word characters but keep the delimiters so we can reconstruct
        tokens = re.split(r'(\W+)', text)
        corrected_tokens = []

        for token in tokens:
            if not token.strip() or not token.isalpha():
                corrected_tokens.append(token)
                continue

            # Heuristic to preserve Proper Nouns: 
            # If the word starts with a capital letter but the rest is lowercase,
            # or if it's ALL CAPS, we assume it's an acronym/name and skip correction.
            # (A perfect system would check if it's the start of a sentence).
            if token.isupper() or (len(token) > 1 and token[0].isupper() and token[1:].islower()):
                corrected_tokens.append(token)
                continue

            # It's a normal lowercase/mixed word. Check spelling.
            # pyspellchecker expects lower case for lookup
            lower_token = token.lower()
            
            if lower_token in self.spell:
                # Known word
                corrected_tokens.append(token)
            else:
                # Unknown word, try to correct
                candidate = self.spell.correction(lower_token)
                if candidate:
                    # Match original casing
                    if token.istitle():
                        candidate = candidate.title()
                    elif token.isupper():
                        candidate = candidate.upper()
                    corrected_tokens.append(candidate)
                else:
                    corrected_tokens.append(token)

        return "".join(corrected_tokens)


_corrector_instance = None


def correct_indonesian_text(text: str) -> str:
    """Convenience function to access the singleton corrector."""
    global _corrector_instance
    if _corrector_instance is None:
        _corrector_instance = IndonesianAutocorrect()
    return _corrector_instance.correct_text(text)
