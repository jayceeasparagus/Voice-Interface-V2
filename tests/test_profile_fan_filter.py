import math
import unittest

import numpy as np

from audio.profile_fan_filter import filter_audio


def tone_level(audio, frequency_hz, sample_rate):
    times = np.arange(len(audio)) / float(sample_rate)
    sine = np.sin(2.0 * math.pi * frequency_hz * times)
    cosine = np.cos(2.0 * math.pi * frequency_hz * times)
    return math.hypot(np.dot(audio, sine), np.dot(audio, cosine))


class ProfileFanFilterTests(unittest.TestCase):
    def test_notch_removes_fan_tone_and_keeps_other_audio(self):
        sample_rate = 16000
        times = np.arange(sample_rate) / float(sample_rate)
        fan = np.sin(2.0 * math.pi * 1000.0 * times)
        speech = np.sin(2.0 * math.pi * 1500.0 * times)
        audio = (0.4 * fan + 0.4 * speech).astype(np.float32)
        profile = {
            "fs": sample_rate,
            "suggested_highpass_hz": 120,
            "notches": [{"f0": 1000, "Q": 25}],
        }

        filtered = filter_audio(audio, sample_rate, profile)

        fan_change = tone_level(filtered, 1000, sample_rate) / tone_level(
            audio, 1000, sample_rate
        )
        speech_change = tone_level(filtered, 1500, sample_rate) / tone_level(
            audio, 1500, sample_rate
        )
        self.assertLess(fan_change, 0.1)
        self.assertGreater(speech_change, 0.8)

    def test_wrong_sample_rate_is_rejected(self):
        profile = {"fs": 16000, "notches": []}
        with self.assertRaises(ValueError):
            filter_audio(np.zeros(100, dtype=np.float32), 48000, profile)


if __name__ == "__main__":
    unittest.main()
