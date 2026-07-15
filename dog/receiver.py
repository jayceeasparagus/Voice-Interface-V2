import argparse
import json
import os
import socket
import subprocess
import sys
import time
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from transport import config
from transport.protocol import decode_message, receive_line


GO2_EXECUTOR_PATH = os.path.join(REPO_ROOT, "dog", "go2_executor.py")
COMMAND_PAUSE_S = 0.5
EXECUTOR_TIMEOUT_S = 30
CLIENT_TIMEOUT_S = 5


def dog_python_env():
    env = os.environ.copy()

    python_paths = [
        REPO_ROOT,
        "/home/unitree/unitree_sdk2_python",
        "/home/unitree/.local/lib/python3.8/site-packages",
        env.get("PYTHONPATH", ""),
    ]
    env["PYTHONPATH"] = ":".join([path for path in python_paths if path])

    library_paths = [
        "/home/unitree/unitree_ros2/cyclonedds_ws/install/cyclonedds/lib",
        env.get("LD_LIBRARY_PATH", ""),
    ]
    env["LD_LIBRARY_PATH"] = ":".join([path for path in library_paths if path])

    return env


class DogReceiver:
    def __init__(self, host, port, message_only=False):
        self.host = host
        self.port = port
        self.message_only = message_only

    def run_action(self, command_item):
        action = command_item["command"]
        params = command_item.get("params", {})
        print("Running:", action)

        if self.message_only:
            return {
                "command": action,
                "params": params,
                "ok": True,
                "response": "message_only",
            }

        command = ["python3", GO2_EXECUTOR_PATH, action]
        if "distance_m" in params:
            command.extend(["--distance-m", str(params["distance_m"])])
        if "degrees" in params:
            command.extend(["--degrees", str(params["degrees"])])

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=dog_python_env(),
                timeout=EXECUTOR_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            response = "ERROR {} timed out".format(action)
            print(response)
            return {
                "command": action,
                "params": params,
                "ok": False,
                "response": response,
            }

        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")

        ok = result.returncode == 0
        if ok:
            response = "OK {}".format(action)
        else:
            response = "ERROR {} returncode {}".format(action, result.returncode)

        return {"command": action, "params": params, "ok": ok, "response": response}

    def handle_client(self, conn, addr):
        try:
            conn.settimeout(CLIENT_TIMEOUT_S)
            raw_message = receive_line(conn).decode("utf-8", errors="replace")
            command_items = decode_message(raw_message)
            print("Received from {}: {}".format(addr, command_items))

            results = []
            for command_item in command_items:
                result = self.run_action(command_item)
                results.append(result)

                if not result["ok"]:
                    break

                time.sleep(COMMAND_PAUSE_S)

            reply = {
                "ok": all(result["ok"] for result in results),
                "results": results,
            }
            conn.sendall((json.dumps(reply) + "\n").encode("utf-8"))

        except Exception as exc:
            traceback.print_exc()
            reply = {"ok": False, "error": str(exc)}
            try:
                conn.sendall((json.dumps(reply) + "\n").encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)

        print("Dog receiver listening on {}:{}.".format(self.host, self.port))
        print("Message only:", self.message_only)

        try:
            while True:
                conn, addr = server.accept()
                self.handle_client(conn, addr)
        except KeyboardInterrupt:
            print("\nStopping dog receiver.")
        finally:
            server.close()


def main():
    parser = argparse.ArgumentParser(description="Receive simple Go2 action JSON.")
    parser.add_argument("--host", default=config.DOG_WIRED_IP)
    parser.add_argument("--port", type=int, default=config.DOG_COMMAND_PORT)
    parser.add_argument("--message-only", action="store_true")
    args = parser.parse_args()

    receiver = DogReceiver(
        host=args.host,
        port=args.port,
        message_only=args.message_only,
    )
    receiver.run()


if __name__ == "__main__":
    main()
