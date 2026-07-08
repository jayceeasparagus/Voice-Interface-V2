import argparse
import socket
import sys

try:
    from transport import config
    from transport.commands import ALLOWED_COMMANDS
    from transport.protocol import actions_from_mapping, build_message, encode_message
except ModuleNotFoundError:
    import config
    from commands import ALLOWED_COMMANDS
    from protocol import actions_from_mapping, build_message, encode_message


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
        response = sock.recv(4096)

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
    args = parser.parse_args()

    try:
        print(send_actions(args.actions, host=args.host, port=args.port))
    except Exception as exc:
        print("SEND_ERROR:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
