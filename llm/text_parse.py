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
    "standdown": "stand_down",
    "go_forward": "walk_forward",
    "move_forward": "walk_forward",
    "walk_straight": "walk_forward",
    "go_straight": "walk_forward",
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
    return """Map user speech to one robot command.

Input speech:
{}

Output must be exactly one of:
unknown
stop
stand
stand_down
walk_forward
walk_backward
walk_left
walk_right
rotate_left
rotate_right
recover
sit

Use unknown if the speech is not clearly a robot command.
Return only the command string.

Output:""".format(text)


def normalize_action(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9_\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" ", "_")
    text = ACTION_NORMALIZATION.get(text, text)

    if text in ALLOWED_ACTIONS:
        return text

    return "unknown"


def get_generated_text(raw_output):
    if "Output:" in raw_output:
        return raw_output.rsplit("Output:", 1)[-1].strip()
    return raw_output.strip()


def extract_action(generated_text):
    if not generated_text:
        return "unknown"

    first_line = ""
    for line in generated_text.splitlines():
        line = line.strip()
        if line:
            first_line = line
            break

    if not first_line:
        return "unknown"

    try:
        value = json.loads(first_line)
        if isinstance(value, str):
            return normalize_action(value)
        if isinstance(value, list) and value:
            return normalize_action(str(value[0]))
    except Exception:
        pass

    quoted = re.findall(r'"([^"]+)"', first_line)
    if quoted:
        return normalize_action(quoted[0])

    return normalize_action(first_line.split()[0])


def call_liquid(text, debug=False):
    prompt = build_prompt(text)
    command = [
        LLAMA_CLI_PATH,
        "-m",
        LIQUID_MODEL_PATH,
        "-p",
        prompt,
        "-n",
        "12",
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
        if debug:
            print("LLM_ERROR:", result.stderr.strip())
        return "unknown"

    generated_text = get_generated_text(result.stdout)
    action = extract_action(generated_text)

    if debug:
        print("TASK:", text)
        print("RAW_LLM_OUTPUT:")
        print(result.stdout.strip())
        print("GENERATED_TEXT:", generated_text)
        print("PARSED_ACTION:", action)

    return action


def parse_text(text, debug=False):
    tasks = split_text(text)
    actions = []

    for task in tasks:
        actions.append(call_liquid(task, debug=debug))

    return actions


def main():
    args = sys.argv[1:]
    debug = False

    if "--debug" in args:
        debug = True
        args.remove("--debug")

    if not args:
        print("Usage: python3 -m llm.text_parse [--debug] \"command text\"")
        return

    text = " ".join(args)
    print(parse_text(text, debug=debug))


if __name__ == "__main__":
    main()
