import argparse
import json
import traceback

from function_call.builder import build_function_calls
from mapping.sqlite_mapper import SqliteCommandMapper
from transport.sender import send_function_calls


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

        function_calls = build_function_calls(mapping_results)
        print("FUNCTION_CALLS:")
        print(json.dumps(function_calls, indent=2))

        valid_calls = [call for call in function_calls if call["valid"]]
        if not valid_calls:
            print("No valid function calls. Nothing sent.")
            print("==============================\n")
            return {
                "mapping": mapping_results,
                "function_calls": function_calls,
                "response": "NO_VALID_CALLS",
            }

        if self.dry_run:
            print("Dry run enabled. Nothing sent to dog.")
            print("==============================\n")
            return {
                "mapping": mapping_results,
                "function_calls": function_calls,
                "response": "DRY_RUN",
            }

        response = send_function_calls(
            valid_calls,
            source="voice",
            transcript=text,
        )
        print("DOG_RESPONSE:", response)
        print("==============================\n")

        return {
            "mapping": mapping_results,
            "function_calls": function_calls,
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
        help="Run mapping and function calling, but do not send to the dog.",
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
