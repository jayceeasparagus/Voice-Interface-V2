import argparse
import socket
import sys

try:
    from transport import config
    from transport.protocol import build_message, encode_message
except ModuleNotFoundError:
    import config
    from protocol import build_message, encode_message


def dog_host():
    if config.COMMAND_TRANSPORT == "wired":
        return config.WIRED_DOG_HOST

    if config.COMMAND_TRANSPORT == "wireless":
        return config.WIRELESS_DOG_HOST

    raise ValueError("Unsupported COMMAND_TRANSPORT: {}".format(config.COMMAND_TRANSPORT))


def send_function_calls(
    function_calls,
    host=None,
    port=config.DOG_COMMAND_PORT,
    timeout=config.DOG_COMMAND_TIMEOUT_S,
    source="voice",
    transcript=None,
):
    host = host or dog_host()
    message = build_message(
        function_calls=function_calls,
        source=source,
        transcript=transcript,
    )

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(encode_message(message))
        response = sock.recv(4096)

    return response.decode("utf-8", errors="replace").strip()


def main():
    parser = argparse.ArgumentParser(description="Send a test function call to the dog.")
    parser.add_argument("command")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=config.DOG_COMMAND_PORT)
    args = parser.parse_args()

    call = {
        "type": "go2_function_call",
        "version": 1,
        "sequence_id": 0,
        "valid": True,
        "command": args.command,
        "function": "go2.{}".format(args.command),
        "args": {},
        "requires_motion_safety": False,
        "source": {},
    }

    try:
        print(send_function_calls([call], host=args.host, port=args.port, source="manual"))
    except Exception as exc:
        print("SEND_ERROR:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
