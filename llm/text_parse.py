import json
import re
import subprocess
import sys

try:
    from llm.text_split import split_text
except ModuleNotFoundError:
    from text_split import split_text


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

ACTION_NORMALIZATION = {
    "set": "sit",
    "seat": "sit",
    "sid": "sit",
    "sit_down": "sit",
    "set_down": "sit",
    "standup": "stand",
    "stand_up": "stand",
    "get_up": "stand",
    "standdown": "stand_down",
    "stay_down": "stand_down",
    "lay_down": "stand_down",
    "lie_down": "stand_down",
    "stopped": "stop",
    "stock": "stop",
    "freeze": "stop",
    "halt": "stop",
    "go_forward": "walk_forward",
    "move_forward": "walk_forward",
    "walk_straight": "walk_forward",
    "go_straight": "walk_forward",
    "move_straight": "walk_forward",
    "go_backward": "walk_backward",
    "move_backward": "walk_backward",
    "back_up": "walk_backward",
    "move_left": "walk_left",
    "step_left": "walk_left",
    "move_right": "walk_right",
    "step_right": "walk_right",
    "turn_left": "rotate_left",
    "look_left": "rotate_left",
    "turn_right": "rotate_right",
    "look_right": "rotate_right",
}


def build_prompt(text):
    return """Map the input to one action.

Input: {}

Output only one string from this list:
sit
stand
stand_down
stop
walk_forward
walk_backward
walk_left
walk_right
rotate_left
rotate_right
recover
unknown

The input is from speech-to-text and may have mistakes.
Map likely speech mistakes to the closest valid action.
If the input is unclear, output unknown.

Output:""".format(text)


def normalize_token(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9_\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" ", "_")
    text = ACTION_NORMALIZATION.get(text, text)

    if text in ALLOWED_ACTIONS:
        return text

    return "unknown"


def extract_action(raw_output):
    text = raw_output.strip()

    arrays = re.findall(r"\[[^\[\]]*\]", text)
    for array_text in reversed(arrays):
        try:
            value = json.loads(array_text)
        except Exception:
            continue
        if isinstance(value, list) and value:
            return normalize_token(str(value[0]))

    quoted = re.findall(r'"([^"]+)"', text)
    for item in reversed(quoted):
        action = normalize_token(item)
        if action != "unknown":
            return action

    for action in sorted(ALLOWED_ACTIONS, key=len, reverse=True):
        if re.search(r"\b{}\b".format(re.escape(action)), text):
            return action

    return "unknown"


def call_liquid(text):
    prompt = build_prompt(text)
    command = [
        LLAMA_CLI_PATH,
        "-m",
        LIQUID_MODEL_PATH,
        "-p",
        prompt,
        "-n",
        "16",
        "--temp",
        "0",
        "-no-cnv",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        print("LLM_ERROR:", result.stderr.strip())
        return "unknown"

    output = result.stdout
    if "Output:" in output:
        output = output.rsplit("Output:", 1)[-1]

    return extract_action(output)


def parse_text(text):
    tasks = split_text(text)
    actions = []

    for task in tasks:
        actions.append(call_liquid(task))

    return actions


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m llm.text_parse \"command text\"")
        return

    text = " ".join(sys.argv[1:])
    print(parse_text(text))


if __name__ == "__main__":
    main()
