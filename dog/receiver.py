import argparse
import json
import os
import socket
import sys
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

for extra_path in (
    "/home/unitree/unitree_sdk2_python",
    "/home/unitree/.local/lib/python3.8/site-packages",
):
    if os.path.exists(extra_path) and extra_path not in sys.path:
        sys.path.insert(0, extra_path)

from transport import config
from transport.protocol import decode_message


class DogCommandReceiver:
    def __init__(self, host, port, message_only=False):
        self.host = host
        self.port = port
        self.message_only = message_only
        self.executor = None

        if not message_only:
            from dog.go2_executor import Go2Executor
            self.executor = Go2Executor()

    def run_command(self, command_item):
        command = command_item["command"]

        if self.message_only:
            return {
                "sequence_id": command_item.get("sequence_id"),
                "ok": True,
                "command": command,
                "response": "message_only",
            }

        response = self.executor.execute(command)
        return {
            "sequence_id": command_item.get("sequence_id"),
            "ok": response.startswith("OK"),
            "command": command,
            "response": response,
        }

    def handle_connection(self, conn, addr):
        try:
            data = conn.recv(8192)
            if not data:
                return

            text = data.decode("utf-8", errors="replace")
            message = decode_message(text)
            print("Received from {}: {}".format(addr, message))

            results = []
            for command_item in message["commands"]:
                results.append(self.run_command(command_item))

            response = {
                "type": "go2_command_response",
                "ok": all(result["ok"] for result in results),
                "results": results,
            }
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))

        except Exception:
            traceback.print_exc()
            try:
                conn.sendall(b'{"ok": false, "error": "server_exception"}\n')
            except Exception:
                pass
        finally:
            conn.close()

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)

        print("Dog command receiver listening on {}:{}.".format(self.host, self.port))
        print("Message only:", self.message_only)

        try:
            while True:
                conn, addr = server.accept()
                self.handle_connection(conn, addr)
        except KeyboardInterrupt:
            print("\nStopping dog receiver.")
        finally:
            server.close()


def main():
    parser = argparse.ArgumentParser(description="Dog-side command receiver.")
    parser.add_argument("--host", default=config.DOG_WIRED_IP)
    parser.add_argument("--port", type=int, default=config.DOG_COMMAND_PORT)
    parser.add_argument(
        "--message-only",
        action="store_true",
        help="Acknowledge messages without moving the dog.",
    )
    args = parser.parse_args()

    receiver = DogCommandReceiver(
        host=args.host,
        port=args.port,
        message_only=args.message_only,
    )
    receiver.run()


if __name__ == "__main__":
    main()
