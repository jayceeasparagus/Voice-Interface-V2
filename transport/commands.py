ALLOWED_COMMANDS = {
    "check",
    "sit",
    "stand",
    "stand_down",
    "stop",
    "recover",
    "walk_forward",
    "walk_backward",
    "walk_left",
    "walk_right",
    "rotate_left",
    "rotate_right",
    "turn_around",
    "release",
}


def normalize_command(command):
    if command is None:
        return "unknown"
    return str(command).strip().lower()


def is_allowed_command(command):
    return normalize_command(command) in ALLOWED_COMMANDS
