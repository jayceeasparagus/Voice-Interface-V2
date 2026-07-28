import argparse
import glob
import math
import os
import wave

import numpy as np


DEFAULT_TARGET_PEAK = 0.85
DEFAULT_MAX_GAIN = 8.0


def read_wav(path):
    with wave.open(path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("Only 16-bit WAV files are supported.")

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return audio, sample_rate, channels


def write_wav(path, audio, sample_rate, channels):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)

    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def apply_adaptive_gain(audio, target_peak=DEFAULT_TARGET_PEAK, max_gain=DEFAULT_MAX_GAIN):
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak == 0.0:
        return audio.copy(), 1.0, peak

    gain = min(target_peak / peak, max_gain)
    return np.clip(audio * gain, -1.0, 1.0), gain, peak


def apply_fixed_gain(audio, gain_db):
    gain = math.pow(10.0, gain_db / 20.0)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    return np.clip(audio * gain, -1.0, 1.0), gain, peak


def find_wavs(path):
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.wav")))
    return [path]


def output_path(input_path, output_dir, suffix):
    name = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(output_dir, name + suffix + ".wav")


def main():
    parser = argparse.ArgumentParser(
        description="Create gained copies of 16-bit WAV files."
    )
    parser.add_argument("path", help="A WAV file or a folder containing WAV files.")
    parser.add_argument(
        "--output-dir",
        default="gain_output",
        help="Folder for processed copies. Default: gain_output",
    )
    parser.add_argument(
        "--gain-db",
        type=float,
        help="Use a fixed gain in dB instead of adaptive gain.",
    )
    parser.add_argument(
        "--target-peak",
        type=float,
        default=DEFAULT_TARGET_PEAK,
        help="Adaptive target from 0 to 1. Default: 0.85",
    )
    parser.add_argument(
        "--max-gain",
        type=float,
        default=DEFAULT_MAX_GAIN,
        help="Maximum adaptive multiplier. Default: 8",
    )
    args = parser.parse_args()

    if not 0.0 < args.target_peak <= 1.0:
        parser.error("--target-peak must be greater than 0 and at most 1.")
    if args.max_gain <= 0.0:
        parser.error("--max-gain must be greater than 0.")

    wav_paths = find_wavs(args.path)
    if not wav_paths or not all(os.path.isfile(path) for path in wav_paths):
        print("No WAV files found.")
        return

    for path in wav_paths:
        try:
            audio, sample_rate, channels = read_wav(path)

            if args.gain_db is None:
                gained, gain, old_peak = apply_adaptive_gain(
                    audio,
                    target_peak=args.target_peak,
                    max_gain=args.max_gain,
                )
                suffix = "_adaptive"
            else:
                gained, gain, old_peak = apply_fixed_gain(audio, args.gain_db)
                suffix = "_gain_{:+g}db".format(args.gain_db)

            destination = output_path(path, args.output_dir, suffix)
            write_wav(destination, gained, sample_rate, channels)
            new_peak = float(np.max(np.abs(gained))) if gained.size else 0.0
            print(
                "{} -> {} | peak {:.3f} -> {:.3f} | gain {:.2f}x".format(
                    os.path.basename(path),
                    destination,
                    old_peak,
                    new_peak,
                    gain,
                )
            )
        except Exception as error:
            print("{} -> ERROR: {}".format(os.path.basename(path), error))


if __name__ == "__main__":
    main()
