import re


# Add Moonshine mishears or common wording fixes here.
# These run before mapping, so obvious fixes stay fast and predictable.
TEXT_FIXES = [
    ("set", "sit"),
    ("seat", "sit"),
    ("sid", "sit"),
    ("set down", "sit down"),
    ("please walk straight", "walk forward"),
    ("walk straight", "walk forward"),
    ("go straight", "walk forward"),
    ("move straight", "walk forward"),
    ("back it up", "walk backward"),
]


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def apply_text_fixes(text):
    text = normalize_text(text)

    for bad_text, fixed_text in TEXT_FIXES:
        if text == normalize_text(bad_text):
            return normalize_text(fixed_text)

    return text
