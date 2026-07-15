import argparse
import socket
import sys

try:
    from transport import config
    from transport.commands import ALLOWED_COMMANDS
    from transport.protocol import actions_from_mapping, build_message, encode_message, receive_line
except ModuleNotFoundError:
    import config
    from commands import ALLOWED_COMMANDS
    from protocol import actions_from_mapping, build_message, encode_message, receive_line


def get_dog_host():
    if config.COMMAND_TRANSPORT == "wired":
        return config.WIRED_DOG_HOST
    if config.COMMAND_TRANSPORT == "wireless":
        return config.WIRELESS_DOG_HOST
    raise ValueError("Unknown COMMAND_TRANSPORT: {}".format(config.COMMAND_TRANSPORT))


def send_actions(actions, host=None, port=config.DOG_COMMAND_PORT, timeout=config.DOG_COMMAND_TIMEOUT_S):
    host = host or get_dog_host()
    message = build_message(actions)

    if not actions_from_mapping(actions):
        return "NO_VALID_COMMANDS"

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(encode_message(message))
        response = receive_line(sock)

    return response.decode("utf-8", errors="replace").strip()


def send_commands(mapping_output, host=None, port=config.DOG_COMMAND_PORT, timeout=config.DOG_COMMAND_TIMEOUT_S, **_):
    return send_actions(
        mapping_output,
        host=host,
        port=port,
        timeout=timeout,
    )


def main():
    parser = argparse.ArgumentParser(description="Send simple Go2 action JSON to the dog.")
    parser.add_argument("actions", nargs="+", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=config.DOG_COMMAND_PORT)
    parser.add_argument("--distance-m", type=float, default=None)
    parser.add_argument("--degrees", type=float, default=None)
    args = parser.parse_args()

    try:
        actions = args.actions
        if len(actions) == 1 and (args.distance_m is not None or args.degrees is not None):
            params = {}
            if args.distance_m is not None:
                params["distance_m"] = args.distance_m
            if args.degrees is not None:
                params["degrees"] = args.degrees
            actions = [{"command": actions[0], "params": params}]

        print(send_actions(actions, host=args.host, port=args.port))
    except Exception as exc:
        print("SEND_ERROR:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
