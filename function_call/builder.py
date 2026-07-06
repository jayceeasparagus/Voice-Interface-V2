import json
import sys
import time

try:
    from function_call.commands import ALLOWED_COMMANDS
except ModuleNotFoundError:
    from commands import ALLOWED_COMMANDS


CALL_SCHEMA_VERSION = 1


def _command_from_mapping_item(item):
    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        return item.get("command", "unknown")

    return "unknown"


def _metadata_from_mapping_item(item):
    if isinstance(item, dict):
        return {
            "input": item.get("input"),
            "fixed_input": item.get("fixed_input"),
            "matched_question": item.get("matched_question"),
            "score": item.get("score"),
        }

    return {}


def build_function_call(command, sequence_id=0, metadata=None):
    metadata = metadata or {}

    if command not in ALLOWED_COMMANDS:
        return {
            "type": "go2_function_call",
            "version": CALL_SCHEMA_VERSION,
            "sequence_id": sequence_id,
            "valid": False,
            "command": "unknown",
            "function": None,
            "args": {},
            "reason": "unknown_or_disallowed_command",
            "source": metadata,
            "timestamp": time.time(),
        }

    spec = ALLOWED_COMMANDS[command]

    return {
        "type": "go2_function_call",
        "version": CALL_SCHEMA_VERSION,
        "sequence_id": sequence_id,
        "valid": True,
        "command": command,
        "function": spec["function"],
        "args": {},
        "requires_motion_safety": spec["movement"],
        "source": metadata,
        "timestamp": time.time(),
    }


def build_function_calls(mapping_output):
    if mapping_output is None:
        mapping_output = []

    if isinstance(mapping_output, (str, dict)):
        mapping_output = [mapping_output]

    calls = []

    for index, item in enumerate(mapping_output):
        command = _command_from_mapping_item(item)
        metadata = _metadata_from_mapping_item(item)
        calls.append(build_function_call(command, sequence_id=index, metadata=metadata))

    return calls


def valid_function_calls(mapping_output):
    calls = build_function_calls(mapping_output)
    return [call for call in calls if call["valid"]]


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 -m function_call.builder sit")
        print("  python3 -m function_call.builder '[{\"command\":\"sit\"},{\"command\":\"walk_forward\"}]'")
        return

    raw_input = " ".join(sys.argv[1:])

    try:
        mapping_output = json.loads(raw_input)
    except Exception:
        if len(sys.argv[1:]) > 1:
            mapping_output = sys.argv[1:]
        else:
            mapping_output = raw_input

    calls = build_function_calls(mapping_output)
    print(json.dumps(calls, indent=2))


if __name__ == "__main__":
    main()
