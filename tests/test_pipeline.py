import unittest

from mapping.sqlite_mapper import SqliteCommandMapper
from transport.protocol import build_message, decode_message


class PipelineTests(unittest.TestCase):
    def test_mapping_splits_and_maps_commands(self):
        mapper = SqliteCommandMapper()
        results = mapper.map_text("sit then walk forward")
        commands = [item["command"] for item in results]
        self.assertEqual(commands, ["sit", "walk_forward"])

    def test_transport_rejects_unknown_commands(self):
        message = build_message(
            mapping_output=[
                {"command": "sit"},
                {"command": "unknown"},
                {"command": "walk_forward"},
            ],
            source="test",
            transcript="sit then something weird then walk forward",
        )

        commands = [item["command"] for item in message["commands"]]
        rejected = [item["command"] for item in message["rejected"]]

        self.assertEqual(commands, ["sit", "walk_forward"])
        self.assertEqual(rejected, ["unknown"])

    def test_protocol_decodes_plain_command_for_manual_testing(self):
        message = decode_message("sit")
        self.assertEqual(message["commands"][0]["command"], "sit")


if __name__ == "__main__":
    unittest.main()
