import json
import re
import subprocess
import sys

from llm.text_split import split_text


LLAMA_CLI_PATH = "/home/aicps/liquid_test/llama.cpp/build/bin/llama-cli"
LIQUID_MODEL_PATH = "/home/aicps/liquid_test/models/LFM2.5-230M-Q4_K_M.gguf"

ALLOWED_ACTIONS = {
    "sit",
    "stand",
    "stand_down",
    "stop",
    "walk_forward",
    "walk_backward",
    "walk_left",
    "walk_right",
    "rotate_left",
    "rotate_right",
    "recover",
    "unknown",
}

MODEL_ALIASES = {
    "forward": "walk_forward",
    "backward": "walk_backward",
    "left": "walk_left",
    "right": "walk_right",
    "turn_left": "rotate_left",
    "turn_right": "rotate_right",
    "turn left": "rotate_left",
    "turn right": "rotate_right",
}


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s_]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_action(action):
    cleaned = normalize_text(action)
    underscored = cleaned.replace(" ", "_")

    for candidate in (cleaned, underscored):
        candidate = MODEL_ALIASES.get(candidate, candidate)
        if candidate in ALLOWED_ACTIONS:
            return candidate

    return "unknown"


def build_prompt(text):
    return """Return only an array of one string.

Allowed strings:
sit, stand, stand_down, stop, walk_forward, walk_backward, walk_left, walk_right, rotate_left, rotate_right, recover, unknown

The input comes from speech-to-text and may have mistakes.
Correct likely speech mistakes before choosing the action.
Examples of possible mistakes:
set or seat means sit
stock or stopped means stop
standup means stand
standdown means stand_down
walk straight means walk_forward
turn right means rotate_right
turn left means rotate_left

Input: stop moving
Output: ["stop"]

Input: sit down
Output: ["sit"]

Input: can you walk straight
Output: ["walk_forward"]

Input: turn right please
Output: ["rotate_right"]

Input: {}
Output:""".format(text)


def extract_array(output):
    matches = re.findall(r"\[[^\[\]]*\]", output)
    for item in reversed(matches):
        try:
            value = json.loads(item)
        except Exception:
            continue
        if isinstance(value, list) and all(isinstance(entry, str) for entry in value):
            return value
    return []


def run_liquid(text):
    prompt = build_prompt(text)
    command = [
        LLAMA_CLI_PATH,
        "-m",
        LIQUID_MODEL_PATH,
        "-p",
        prompt,
        "-n",
        "40",
        "--temp",
        "0",
        "-no-cnv",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        print("LLM_ERROR:", exc)
        return "unknown"

    output = result.stdout + "\n" + result.stderr
    tokens = extract_array(output)
    if not tokens:
        return "unknown"

    return normalize_action(tokens[0])


def parse_action(text):
    return run_liquid(text)


def parse_text(text):
    tasks = split_text(text)
    actions = []

    for task in tasks:
        actions.append(parse_action(task))

    return actions


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m llm.text_parse \"command text\"")
        return

    text = " ".join(sys.argv[1:])
    print(parse_text(text))


if __name__ == "__main__":
    main()
