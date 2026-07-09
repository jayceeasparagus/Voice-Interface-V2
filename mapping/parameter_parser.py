import re


DEFAULT_DISTANCE_M = 1.0
MIN_DISTANCE_M = 0.2
MAX_DISTANCE_M = 2.0

DEFAULT_ROTATION_DEG = 45.0
MIN_ROTATION_DEG = 10.0
MAX_ROTATION_DEG = 180.0

NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

DISTANCE_COMMANDS = {
    "walk_forward",
    "walk_backward",
    "walk_left",
    "walk_right",
}

ROTATION_COMMANDS = {
    "rotate_left",
    "rotate_right",
    "turn_around",
}


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def number_from_text(text):
    match = re.search(r"\b\d+(\.\d+)?\b", text)
    if match:
        return float(match.group(0))

    words = text.lower().split()
    for word in words:
        if word in NUMBER_WORDS:
            return float(NUMBER_WORDS[word])

    return None


def parse_distance_m(text):
    number = number_from_text(text)
    if number is None:
        return DEFAULT_DISTANCE_M

    text = text.lower()
    if "inch" in text:
        distance_m = number * 0.0254
    elif "foot" in text or "feet" in text:
        distance_m = number * 0.3048
    else:
        distance_m = number

    return clamp(distance_m, MIN_DISTANCE_M, MAX_DISTANCE_M)


def parse_rotation_deg(text):
    number = number_from_text(text)
    if number is None:
        return DEFAULT_ROTATION_DEG

    return clamp(number, MIN_ROTATION_DEG, MAX_ROTATION_DEG)


def params_for_command(command, text):
    if command in DISTANCE_COMMANDS:
        return {"distance_m": parse_distance_m(text)}

    if command in ROTATION_COMMANDS:
        default_deg = 180.0 if command == "turn_around" else DEFAULT_ROTATION_DEG
        degrees = parse_rotation_deg(text)
        if number_from_text(text) is None:
            degrees = default_deg
        return {"degrees": clamp(degrees, MIN_ROTATION_DEG, MAX_ROTATION_DEG)}

    return {}
