ALLOWED_COMMANDS = {
    "sit": {
        "function": "go2.sit",
        "description": "Put the Go2 into sit posture.",
        "movement": False,
    },
    "stand": {
        "function": "go2.stand",
        "description": "Put the Go2 into standing posture.",
        "movement": False,
    },
    "stand_down": {
        "function": "go2.stand_down",
        "description": "Lower the Go2 into stand-down posture.",
        "movement": False,
    },
    "stop": {
        "function": "go2.stop",
        "description": "Stop active movement.",
        "movement": False,
    },
    "recover": {
        "function": "go2.recover",
        "description": "Run recovery stand.",
        "movement": False,
    },
    "walk_forward": {
        "function": "go2.walk_forward",
        "description": "Walk forward using the dog-side safe default distance.",
        "movement": True,
    },
    "walk_backward": {
        "function": "go2.walk_backward",
        "description": "Walk backward using the dog-side safe default distance.",
        "movement": True,
    },
    "walk_left": {
        "function": "go2.walk_left",
        "description": "Step left using the dog-side safe default distance.",
        "movement": True,
    },
    "walk_right": {
        "function": "go2.walk_right",
        "description": "Step right using the dog-side safe default distance.",
        "movement": True,
    },
    "rotate_left": {
        "function": "go2.rotate_left",
        "description": "Rotate left using the dog-side safe default angle.",
        "movement": True,
    },
    "rotate_right": {
        "function": "go2.rotate_right",
        "description": "Rotate right using the dog-side safe default angle.",
        "movement": True,
    },
}
