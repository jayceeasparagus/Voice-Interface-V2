import json


MESSAGE_TYPE = "go2_function_call_batch"
MESSAGE_VERSION = 1


def build_message(function_calls, source="voice", transcript=None):
    return {
        "type": MESSAGE_TYPE,
        "version": MESSAGE_VERSION,
        "source": source,
        "transcript": transcript,
        "calls": function_calls,
    }


def encode_message(message):
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(raw_text):
    message = json.loads(raw_text.strip())

    if message.get("type") != MESSAGE_TYPE:
        raise ValueError("Unsupported message type: {}".format(message.get("type")))

    if int(message.get("version", 0)) != MESSAGE_VERSION:
        raise ValueError("Unsupported message version: {}".format(message.get("version")))

    calls = message.get("calls")
    if not isinstance(calls, list):
        raise ValueError("Message calls must be a list")

    return message
