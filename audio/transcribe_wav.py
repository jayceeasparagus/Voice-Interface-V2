import argparse
import glob
import os
import wave

import numpy as np

from audio.listener import MoonshineSTT, SAMPLE_RATE


def read_wav(path):
    with wave.open(path, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("Only 16-bit WAV files are supported.")

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    if channels > 1:
        audio = audio.reshape(-1, channels)[:, 0]

    return audio, sample_rate


def resample_to_moonshine(audio, sample_rate):
    if sample_rate == SAMPLE_RATE:
        return audio.astype(np.float32)

    if sample_rate == 48000 and SAMPLE_RATE == 16000:
        trim_len = len(audio) - (len(audio) % 3)
        audio = audio[:trim_len]
        return audio.reshape(-1, 3).mean(axis=1).astype(np.float32)

    old_times = np.arange(len(audio)) / float(sample_rate)
    new_len = int(len(audio) * SAMPLE_RATE / sample_rate)
    new_times = np.arange(new_len) / float(SAMPLE_RATE)
    return np.interp(new_times, old_times, audio).astype(np.float32)


def find_wavs(path):
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.wav")))
    return [path]


def main():
    parser = argparse.ArgumentParser(description="Run Moonshine on saved WAV files.")
    parser.add_argument("path", help="A WAV file or a folder of WAV files.")
    args = parser.parse_args()

    wav_paths = find_wavs(args.path)
    if not wav_paths:
        print("No WAV files found.")
        return

    stt = MoonshineSTT()

    for path in wav_paths:
        try:
            audio, sample_rate = read_wav(path)
            audio = resample_to_moonshine(audio, sample_rate)
            text = stt.transcribe(audio)
            print("{} -> {}".format(os.path.basename(path), text))
        except Exception as error:
            print("{} -> ERROR: {}".format(os.path.basename(path), error))


if __name__ == "__main__":
    main()
