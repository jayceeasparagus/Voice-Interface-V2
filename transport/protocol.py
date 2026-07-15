import json

try:
    from transport.commands import is_allowed_command, normalize_command
except ModuleNotFoundError:
    from commands import is_allowed_command, normalize_command


MAX_MESSAGE_BYTES = 65536


def action_from_item(item):
    if isinstance(item, dict):
        return normalize_command(item.get("command"))
    return normalize_command(item)


def command_items_from_mapping(mapping_output):
    if mapping_output is None:
        return []

    if isinstance(mapping_output, (str, dict)):
        mapping_output = [mapping_output]

    items = []
    for item in mapping_output:
        action = action_from_item(item)
        if is_allowed_command(action):
            command_item = {"command": action}
            if isinstance(item, dict) and item.get("params"):
                command_item["params"] = item["params"]
            items.append(command_item)

    return items


def actions_from_mapping(mapping_output):
    return [item["command"] for item in command_items_from_mapping(mapping_output)]


def build_message(mapping_output):
    command_items = command_items_from_mapping(mapping_output)

    if len(command_items) == 1:
        return command_items[0]

    return {"commands": command_items}


def encode_message(message):
    return (json.dumps(message) + "\n").encode("utf-8")


def receive_line(sock):
    data = bytearray()

    while b"\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break

        data.extend(chunk)
        if len(data) > MAX_MESSAGE_BYTES:
            raise ValueError("Command message is too large")

    if not data:
        raise ConnectionError("Connection closed without a message")

    return bytes(data).split(b"\n", 1)[0]


def decode_message(raw_text):
    text = raw_text.strip()
    if not text:
        raise ValueError("Empty command message")

    if not text.startswith("{"):
        action = normalize_command(text)
        if not is_allowed_command(action):
            raise ValueError("Invalid command: {}".format(action))
        return [{"command": action, "params": {}}]

    message = json.loads(text)

    if "command" in message:
        raw_items = [message]
    else:
        raw_items = message.get("commands", [])

    command_items = []
    for item in raw_items:
        if isinstance(item, dict):
            action = normalize_command(item.get("command"))
            params = item.get("params", {})
        else:
            action = normalize_command(item)
            params = {}

        if is_allowed_command(action):
            command_items.append({"command": action, "params": params})

    if not command_items:
        raise ValueError("No valid commands in message")

    return command_items
