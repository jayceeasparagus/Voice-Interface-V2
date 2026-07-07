import json
import time

try:
    from transport.commands import is_allowed_command, normalize_command
except ModuleNotFoundError:
    from commands import is_allowed_command, normalize_command


MESSAGE_TYPE = "go2_command_batch"
MESSAGE_VERSION = 1


def command_from_mapping_item(item):
    if isinstance(item, str):
        return normalize_command(item)

    if isinstance(item, dict):
        return normalize_command(item.get("command"))

    return "unknown"


def source_from_mapping_item(item):
    if isinstance(item, dict):
        return {
            "input": item.get("input"),
            "fixed_input": item.get("fixed_input"),
            "matched_question": item.get("matched_question"),
            "score": item.get("score"),
        }

    return {}


def make_command_items(mapping_output):
    if mapping_output is None:
        mapping_output = []

    if isinstance(mapping_output, (str, dict)):
        mapping_output = [mapping_output]

    items = []

    for index, item in enumerate(mapping_output):
        command = command_from_mapping_item(item)
        allowed = is_allowed_command(command)

        items.append({
            "sequence_id": index,
            "command": command if allowed else "unknown",
            "valid": allowed,
            "source": source_from_mapping_item(item),
        })

    return items


def valid_command_items(command_items):
    return [item for item in command_items if item.get("valid")]


def build_message(mapping_output, source="voice", transcript=None):
    command_items = make_command_items(mapping_output)

    return {
        "type": MESSAGE_TYPE,
        "version": MESSAGE_VERSION,
        "source": source,
        "transcript": transcript,
        "commands": valid_command_items(command_items),
        "rejected": [item for item in command_items if not item.get("valid")],
        "timestamp": time.time(),
    }


def encode_message(message):
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(raw_text):
    text = raw_text.strip()
    if not text:
        raise ValueError("Empty message")

    if not text.startswith("{"):
        command = normalize_command(text)
        if not is_allowed_command(command):
            raise ValueError("Invalid plain command: {}".format(command))
        return build_message([command], source="plain_text", transcript=text)

    message = json.loads(text)

    if message.get("type") != MESSAGE_TYPE:
        raise ValueError("Unsupported message type: {}".format(message.get("type")))

    if int(message.get("version", 0)) != MESSAGE_VERSION:
        raise ValueError("Unsupported message version: {}".format(message.get("version")))

    commands = message.get("commands")
    if not isinstance(commands, list):
        raise ValueError("Message commands must be a list")

    for item in commands:
        command = normalize_command(item.get("command") if isinstance(item, dict) else None)
        if not is_allowed_command(command):
            raise ValueError("Invalid command in message: {}".format(command))
        item["command"] = command
        item["valid"] = True

    return message
