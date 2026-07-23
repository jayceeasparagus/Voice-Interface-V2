import argparse
import os
import subprocess
import sys
import tempfile


# Turn these on or off independently.
SPEAK_ON_LOW_CONFIDENCE = True
SPEAK_ON_NON_COMMAND = True

# Unknown mappings at or above this score probably resembled a robot command.
NON_COMMAND_SCORE_CUTOFF = 0.20

LOW_CONFIDENCE_MESSAGE = "I am not sure which command you said."
NON_COMMAND_MESSAGE = "I heard you, but that was not a robot command."

# These can be changed after the SR80 speaker device is confirmed.
SPEAKER_DEVICE = "plughw:1,0"
PIPER_VOICE = "en_US-lessac-low"
VOICE_DIR = os.path.join(os.path.dirname(__file__), "voices")


def feedback_for_mapping(mapping_results):
    unknown_results = [
        result
        for result in mapping_results
        if result.get("command") == "unknown"
    ]
    if not unknown_results:
        return None

    best_score = max(float(result.get("score", 0.0)) for result in unknown_results)

    if best_score >= NON_COMMAND_SCORE_CUTOFF:
        if SPEAK_ON_LOW_CONFIDENCE:
            return "low_confidence", LOW_CONFIDENCE_MESSAGE
        return None

    if SPEAK_ON_NON_COMMAND:
        return "non_command", NON_COMMAND_MESSAGE
    return None


def print_mapping_feedback(mapping_results):
    feedback = feedback_for_mapping(mapping_results)
    if feedback is None:
        return None

    reason, message = feedback
    print("SPEAKER WOULD SAY [{}]: {}".format(reason, message))
    return feedback


def speak(text, device=SPEAKER_DEVICE):
    os.makedirs(VOICE_DIR, exist_ok=True)

    output_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    output_path = output_file.name
    output_file.close()

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "piper",
                "-m",
                PIPER_VOICE,
                "--data-dir",
                VOICE_DIR,
                "-f",
                output_path,
                "--",
                text,
            ],
            check=True,
        )
        subprocess.run(
            ["aplay", "-D", device, output_path],
            check=True,
        )
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def main():
    parser = argparse.ArgumentParser(description="Test text-to-speech output.")
    parser.add_argument("-m", "--message", required=True, help="Text to speak.")
    parser.add_argument(
        "-d",
        "--device",
        default=SPEAKER_DEVICE,
        help="ALSA playback device.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the message without using Piper or the speaker.",
    )
    args = parser.parse_args()

    if args.print_only:
        print("SPEAKER WOULD SAY:", args.message)
        return

    try:
        speak(args.message, device=args.device)
    except FileNotFoundError as error:
        print("Speaker test failed. Missing program:", error.filename)
        raise SystemExit(1)
    except subprocess.CalledProcessError as error:
        print("Speaker test failed with return code", error.returncode)
        print(
            "Download the voice with: python3 -m piper.download_voices "
            "--data-dir speaker/voices {}".format(PIPER_VOICE)
        )
        raise SystemExit(error.returncode)


if __name__ == "__main__":
    main()
