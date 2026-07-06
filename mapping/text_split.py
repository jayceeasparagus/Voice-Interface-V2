import re
import sys


SPLIT_PATTERNS = [
    r"\band\s+then\b",
    r"\bthen\b",
    r"\bafter\s+that\b",
    r"\balso\b",
]


def clean_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s,+]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_text(text):
    text = clean_text(text)
    if not text:
        return []

    pattern = "|".join(SPLIT_PATTERNS)
    parts = re.split(pattern, text)
    tasks = []

    for part in parts:
        part = part.strip(" ,")
        if part:
            tasks.append(part)

    return tasks


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m mapping.text_split \"command text\"")
        return

    text = " ".join(sys.argv[1:])
    print(split_text(text))


if __name__ == "__main__":
    main()
