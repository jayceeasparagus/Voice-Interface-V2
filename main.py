import argparse
import json
import queue
import threading
import traceback

from mapping.sqlite_mapper import SqliteCommandMapper
from transport.sender import send_commands


class VoiceDogPipeline:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.mapper = SqliteCommandMapper()
        self.command_queue = queue.Queue()
        self.running = True
        self.worker_thread = threading.Thread(
            target=self.command_worker,
            daemon=True,
        )
        self.worker_thread.start()

    def enqueue_text(self, text):
        text = text.strip()
        if not text:
            print("Empty command. Ignoring.")
            return

        print("Queued command:", text)
        self.command_queue.put(text)

    def command_worker(self):
        while self.running:
            try:
                text = self.command_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                self.process_text(text)
            except Exception:
                print("\n[COMMAND WORKER ERROR]")
                traceback.print_exc()
            finally:
                self.command_queue.task_done()
                print("Listening for wake word...")

    def stop(self):
        self.running = False

    def process_text(self, text):
        print("\n==============================")
        print("TRANSCRIPT:", text)

        mapping_results = self.mapper.map_text(text)
        print("MAPPING:")
        print(json.dumps(mapping_results, indent=2))

        actions = [item["command"] for item in mapping_results if item["command"] != "unknown"]
        print("ACTIONS:", actions)

        if not actions:
            print("No valid commands. Nothing sent.")
            print("==============================\n")
            return {
                "mapping": mapping_results,
                "actions": actions,
                "response": "NO_VALID_COMMANDS",
            }

        if self.dry_run:
            print("Dry run enabled. Nothing sent to dog.")
            print("==============================\n")
            return {
                "mapping": mapping_results,
                "actions": actions,
                "response": "DRY_RUN",
            }

        response = send_commands(actions)
        print("DOG_RESPONSE:", response)
        print("==============================\n")

        return {
            "mapping": mapping_results,
            "actions": actions,
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
        handler=pipeline.enqueue_text,
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
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
