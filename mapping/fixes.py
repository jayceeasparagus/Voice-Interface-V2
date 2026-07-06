import re


# Add single-word Moonshine mishears here when you notice them.
# Keep this empty by default so mapping is handled by qa_pairs.json.
#
# Format:
# TEXT_FIXES = [
#     ("set", "sit"),
#     ("seat", "sit"),
# ]
TEXT_FIXES = []


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def apply_text_fixes(text):
    text = normalize_text(text)

    for bad_text, fixed_text in TEXT_FIXES:
        bad_text = normalize_text(bad_text)
        fixed_text = normalize_text(fixed_text)

        if " " in bad_text or " " in fixed_text:
            continue

        words = text.split()
        words = [fixed_text if word == bad_text else word for word in words]
        text = " ".join(words)

    return text
