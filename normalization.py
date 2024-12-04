import unicodedata

# Updated replacement map that converts Elizabethan to modern English
replacement_map = {
    "Æ": "ae", "æ": "ae",
    "ſ": "s",
    "ꝛ": "r",
    "j": "i",
    "v": "u",
    "th": "y",
    "Þ": "th", "þ": "th",
    "Ð": "d", "ð": "d",
    "ƿ": "w",
    "Ƿ": "w",
    "ꝣ": "d",
    "Ꝺ": "d",
    "Ȝ": "y", "ȝ": "y",
    "ß": "ss",
    "Œ": "oe", "œ": "oe",
    "Ꝋ": "o", "ꝋ": "o",
    "Ꝑ": "p", "ꝑ": "p",
    "Ꝙ": "q", "ꝙ": "q",
    "ꝺ": "d"
}


def normalize_text(text):
    if not text:
        return text

    # Convert to lowercase and remove diacritics
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()

    # Character substitutions
    text = text.replace('j', 'i')
    text = text.replace('v', 'u')
    text = text.replace('ye', 'the')
    text = text.replace('æ', 'ae')

    # Common spelling variations
    text = text.replace('tragedie', 'tragedy')
    text = text.replace('comedie', 'comedy')
    text = text.replace('historie', 'history')
    text = text.replace('ſ', 's')  # long s
    text = text.replace('haviour', 'havior')
    text = text.replace('honour', 'honor')
    text = text.replace('labour', 'labor')
    text = text.replace('griefe', 'grief')
    text = text.replace('loue', 'love')
    text = text.replace('publike', 'public')
    text = text.replace('musicke', 'music')
    text = text.replace('magicke', 'magic')
    text = text.replace('worke', 'work')
    text = text.replace('booke', 'book')

    return text