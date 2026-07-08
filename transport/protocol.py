import json

try:
    from transport.commands import is_allowed_command, normalize_command
except ModuleNotFoundError:
    from commands import is_allowed_command, normalize_command


def action_from_item(item):
    if isinstance(item, dict):
        return normalize_command(item.get("command"))
    return normalize_command(item)


def actions_from_mapping(mapping_output):
    if mapping_output is None:
        return []

    if isinstance(mapping_output, (str, dict)):
        mapping_output = [mapping_output]

    actions = []
    for item in mapping_output:
        action = action_from_item(item)
        if is_allowed_command(action):
            actions.append(action)

    return actions


def build_message(mapping_output):
    actions = actions_from_mapping(mapping_output)

    if len(actions) == 1:
        return {"command": actions[0]}

    return {"commands": actions}


def encode_message(message):
    return (json.dumps(message) + "\n").encode("utf-8")


def decode_message(raw_text):
    text = raw_text.strip()
    if not text:
        raise ValueError("Empty command message")

    if not text.startswith("{"):
        action = normalize_command(text)
        if not is_allowed_command(action):
            raise ValueError("Invalid command: {}".format(action))
        return [action]

    message = json.loads(text)

    if "command" in message:
        actions = [normalize_command(message["command"])]
    else:
        actions = [normalize_command(action) for action in message.get("commands", [])]

    actions = [action for action in actions if is_allowed_command(action)]
    if not actions:
        raise ValueError("No valid commands in message")

    return actions
