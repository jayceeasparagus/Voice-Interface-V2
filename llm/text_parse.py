import subprocess
import sys

try:
    from llm.text_split import split_text
except ModuleNotFoundError:
    from text_split import split_text


LLAMA_CLI_PATH = "/home/aicps/liquid_test/llama.cpp/build/bin/llama-cli"
LIQUID_MODEL_PATH = "/home/aicps/liquid_test/models/LFM2.5-230M-Q4_K_M.gguf"


def build_prompt(text):
    return """Convert the speech text into one robot command.

Allowed commands:
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

Choose the closest allowed command.
Return only the command. No explanation.

Speech text: {}
Command:""".format(text)


def clean_output(output):
    if "Command:" in output:
        output = output.rsplit("Command:", 1)[-1]

    output = output.strip()
    if not output:
        return "unknown"

    return output.split()[0].strip(" ,.'\"[]")


def map_text_to_command(text):
    result = subprocess.run(
        [
            LLAMA_CLI_PATH,
            "-m",
            LIQUID_MODEL_PATH,
            "-p",
            build_prompt(text),
            "-n",
            "8",
            "--temp",
            "0",
            "-no-cnv",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return "unknown"

    return clean_output(result.stdout)


def parse_text(text):
    commands = []
    for task in split_text(text):
        commands.append(map_text_to_command(task))
    return commands


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m llm.text_parse \"speech text\"")
        return

    text = " ".join(sys.argv[1:])
    print(parse_text(text))


if __name__ == "__main__":
    main()
