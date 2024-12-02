import unicodedata

# Comprehensive replacement map for Elizabethan to modern character substitutions
replacement_map = {
    "Æ": "Ae", "æ": "ae",
    "ſ": "s",
    "ꝛ": "r",
    "I": "J", "i": "j",
    "V": "U", "v": "u",
    "U": "V", "u": "v",
    "Y": "Th", "y": "th",
    "Þ": "Th", "þ": "th",
    "Ð": "D", "ð": "d",
    "ƿ": "w",
    "Ƿ": "W",
    "ꝣ": "d",
    "Ꝺ": "d",
    "Ȝ": "Y", "ȝ": "y",
    "Ç": "C", "ç": "c",
    "ß": "ss",
    "Œ": "Oe", "œ": "oe",
    "Ꝋ": "o", "ꝋ": "o",
    "Ꝑ": "p", "ꝑ": "p",
    "Ꝙ": "q", "ꝙ": "q",
    "ꝺ": "d",
    "ȣ": "ou",
    "Ā": "A", "ā": "a",
    "Ē": "E", "ē": "e",
    "Ī": "I", "ī": "i",
    "Ō": "O", "ō": "o",
    "Ū": "U", "ū": "u",
    "Ȳ": "Y", "ȳ": "y",
}

def normalize_text(text):
    """
    Normalizes the given text by applying Elizabethan-to-modern character substitutions
    and removing diacritics.
    """
    if text:
        # Normalize Unicode and remove diacritics
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))  # Strip diacritics

        # Apply replacements from the replacement map
        for old, new in replacement_map.items():
            text = text.replace(old, new)

        # Return normalized lowercase text
        return text.lower()
    return text
