import argparse
import json
import traceback

from mapping.sqlite_mapper import SqliteCommandMapper
from transport.protocol import build_message
from transport.sender import send_commands


class VoiceDogPipeline:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.mapper = SqliteCommandMapper()

    def process_text(self, text):
        print("\n==============================")
        print("TRANSCRIPT:", text)

        mapping_results = self.mapper.map_text(text)
        print("MAPPING:")
        print(json.dumps(mapping_results, indent=2))

        message_preview = build_message(
            mapping_output=mapping_results,
            source="voice",
            transcript=text,
        )
        print("TRANSPORT_MESSAGE:")
        print(json.dumps(message_preview, indent=2))

        if not message_preview["commands"]:
            print("No valid commands. Nothing sent.")
            print("==============================\n")
            return {
                "mapping": mapping_results,
                "transport_message": message_preview,
                "response": "NO_VALID_COMMANDS",
            }

        if self.dry_run:
            print("Dry run enabled. Nothing sent to dog.")
            print("==============================\n")
            return {
                "mapping": mapping_results,
                "transport_message": message_preview,
                "response": "DRY_RUN",
            }

        response = send_commands(
            mapping_results,
            source="voice",
            transcript=text,
        )
        print("DOG_RESPONSE:", response)
        print("==============================\n")

        return {
            "mapping": mapping_results,
            "transport_message": message_preview,
            "response": response,
        }


def main():
    parser = argparse.ArgumentParser(description="V2 speech-to-dog command pipeline.")
    parser.add_argument(
        "--debug",
        metavar="TEXT",
        help="Run one text command through the pipeline without using the microphone.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run mapping and transport validation, but do not send to the dog.",
    )
    args = parser.parse_args()

    pipeline = VoiceDogPipeline(dry_run=args.dry_run)

    if args.debug is not None:
        pipeline.process_text(args.debug)
        return

    from audio import config as audio_config
    from audio.listener import AudioListener

    listener = AudioListener(
        wake_word_enabled=audio_config.WAKE_WORD_ENABLED,
        handler=pipeline.process_text,
    )

    print("Voice Interface V2 running.")
    print("Wake word enabled:", audio_config.WAKE_WORD_ENABLED)
    print("Wake word:", audio_config.WAKE_WORD)
    print("Dry run:", args.dry_run)
    print("Press Ctrl+C to stop.")

    try:
        listener.run()
    except KeyboardInterrupt:
        print("\nStopping pipeline.")
    except Exception:
        print("\n[PIPELINE ERROR]")
        traceback.print_exc()


if __name__ == "__main__":
    main()
