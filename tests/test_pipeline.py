import socket
import unittest

from mapping.sqlite_mapper import SqliteCommandMapper
from transport.protocol import build_message, decode_message, receive_line


class PipelineTests(unittest.TestCase):
    def test_mapping_splits_and_maps_commands(self):
        mapper = SqliteCommandMapper()
        results = mapper.map_text("sit then walk forward")
        commands = [item["command"] for item in results]
        self.assertEqual(commands, ["sit", "walk_forward"])
        self.assertEqual(results[1]["params"]["distance_m"], 1.0)

    def test_mapping_converts_inches(self):
        mapper = SqliteCommandMapper()
        results = mapper.map_text("walk forward 12 inches")
        self.assertEqual(results[0]["command"], "walk_forward")
        self.assertAlmostEqual(results[0]["params"]["distance_m"], 0.3048, places=4)

    def test_mapping_turn_around(self):
        mapper = SqliteCommandMapper()
        results = mapper.map_text("turn around")
        self.assertEqual(results[0]["command"], "turn_around")
        self.assertEqual(results[0]["params"]["degrees"], 180.0)

    def test_transport_rejects_unknown_commands(self):
        message = build_message(
            mapping_output=[
                {"command": "sit"},
                {"command": "unknown"},
                {"command": "walk_forward"},
                {"command": "turn_around"},
            ]
        )

        commands = [item["command"] for item in message["commands"]]
        self.assertEqual(commands, ["sit", "walk_forward", "turn_around"])

    def test_protocol_decodes_plain_command_for_manual_testing(self):
        commands = decode_message("sit")
        self.assertEqual(commands, [{"command": "sit", "params": {}}])

    def test_receive_line_handles_split_tcp_message(self):
        sender, receiver = socket.socketpair()
        try:
            sender.sendall(b'{"command":')
            sender.sendall(b'"sit"}\n')
            self.assertEqual(receive_line(receiver), b'{"command":"sit"}')
        finally:
            sender.close()
            receiver.close()


if __name__ == "__main__":
    unittest.main()
