"""Experimental fan-tone filter built from a saved fan profile.

This is intentionally separate from the live pipeline. It removes low-frequency
rumble and the narrow fan tones listed in the profile, then writes a new WAV.
"""

import argparse
import json
import math
import os
import wave

import numpy as np


DEFAULT_PROFILE = os.path.join(
    os.path.dirname(__file__),
    "fan_profile_corrected.json",
)


class Biquad:
    def __init__(self, b0, b1, b2, a0, a1, a2):
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0
        self.z1 = 0.0
        self.z2 = 0.0

    def process(self, audio):
        output = np.empty_like(audio, dtype=np.float64)
        for index, sample in enumerate(audio):
            value = self.b0 * sample + self.z1
            self.z1 = self.b1 * sample - self.a1 * value + self.z2
            self.z2 = self.b2 * sample - self.a2 * value
            output[index] = value
        return output


def make_highpass(sample_rate, cutoff_hz):
    frequency = 2.0 * math.pi * cutoff_hz / sample_rate
    cosine = math.cos(frequency)
    alpha = math.sin(frequency) / (2.0 * math.sqrt(0.5))
    return Biquad(
        (1.0 + cosine) / 2.0,
        -(1.0 + cosine),
        (1.0 + cosine) / 2.0,
        1.0 + alpha,
        -2.0 * cosine,
        1.0 - alpha,
    )


def make_notch(sample_rate, frequency_hz, quality):
    frequency = 2.0 * math.pi * frequency_hz / sample_rate
    cosine = math.cos(frequency)
    alpha = math.sin(frequency) / (2.0 * quality)
    return Biquad(
        1.0,
        -2.0 * cosine,
        1.0,
        1.0 + alpha,
        -2.0 * cosine,
        1.0 - alpha,
    )


def load_profile(path):
    with open(path, "r") as profile_file:
        return json.load(profile_file)


def filter_audio(audio, sample_rate, profile):
    expected_rate = int(profile["fs"])
    if sample_rate != expected_rate:
        raise ValueError(
            "Profile expects {} Hz audio, but input is {} Hz.".format(
                expected_rate, sample_rate
            )
        )

    output = np.asarray(audio, dtype=np.float64)
    cutoff = float(profile.get("suggested_highpass_hz", 0))
    if cutoff > 0:
        output = make_highpass(sample_rate, cutoff).process(output)

    for notch in profile.get("notches", []):
        frequency_hz = float(notch["f0"])
        quality = float(notch["Q"])
        if 0 < frequency_hz < sample_rate / 2 and quality > 0:
            output = make_notch(sample_rate, frequency_hz, quality).process(output)

    peak = float(np.max(np.abs(output))) if output.size else 0.0
    if peak > 0.99:
        output *= 0.99 / peak
    return output.astype(np.float32)


def read_wav(path):
    with wave.open(path, "rb") as wav_file:
        if wav_file.getsampwidth() != 2:
            raise ValueError("Only 16-bit WAV files are supported.")
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        frames = wav_file.readframes(wav_file.getnframes())

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio, sample_rate


def write_wav(path, audio, sample_rate):
    samples = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())


def filter_file(input_path, output_path, profile_path=DEFAULT_PROFILE):
    profile = load_profile(profile_path)
    audio, sample_rate = read_wav(input_path)
    filtered = filter_audio(audio, sample_rate, profile)
    write_wav(output_path, filtered, sample_rate)
    return filtered


def main():
    parser = argparse.ArgumentParser(description="Apply the fan profile to a WAV file.")
    parser.add_argument("input", help="16-bit mono or stereo WAV")
    parser.add_argument("output", help="output WAV")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    filter_file(args.input, args.output, args.profile)
    print("Wrote {}".format(args.output))


if __name__ == "__main__":
    main()
