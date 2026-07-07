import argparse
import socket
import sys

try:
    from transport import config
    from transport.commands import ALLOWED_COMMANDS
    from transport.protocol import build_message, encode_message
except ModuleNotFoundError:
    import config
    from commands import ALLOWED_COMMANDS
    from protocol import build_message, encode_message


def dog_host():
    if config.COMMAND_TRANSPORT == "wired":
        return config.WIRED_DOG_HOST

    if config.COMMAND_TRANSPORT == "wireless":
        return config.WIRELESS_DOG_HOST

    raise ValueError("Unsupported COMMAND_TRANSPORT: {}".format(config.COMMAND_TRANSPORT))


def send_commands(
    mapping_output,
    host=None,
    port=config.DOG_COMMAND_PORT,
    timeout=config.DOG_COMMAND_TIMEOUT_S,
    source="voice",
    transcript=None,
):
    host = host or dog_host()
    message = build_message(
        mapping_output=mapping_output,
        source=source,
        transcript=transcript,
    )

    if not message["commands"]:
        return "NO_VALID_COMMANDS"

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(encode_message(message))
        response = sock.recv(4096)

    return response.decode("utf-8", errors="replace").strip()


def main():
    parser = argparse.ArgumentParser(description="Send Go2 commands to the dog.")
    parser.add_argument("commands", nargs="+", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=config.DOG_COMMAND_PORT)
    args = parser.parse_args()

    try:
        print(send_commands(args.commands, host=args.host, port=args.port, source="manual"))
    except Exception as exc:
        print("SEND_ERROR:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
