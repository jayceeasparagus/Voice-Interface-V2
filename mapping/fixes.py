import re


# Add common one-word speech mistakes here.
# Example: if Moonshine hears "set" when you said "sit", map it before matching.
MISHEARD_WORDS = {
    "set": "sit",
}


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def apply_text_fixes(text):
    words = normalize_text(text).split()
    fixed_words = [MISHEARD_WORDS.get(word, word) for word in words]
    return " ".join(fixed_words)
