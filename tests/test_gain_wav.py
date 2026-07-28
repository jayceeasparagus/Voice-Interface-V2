import os
import tempfile
import unittest
import wave

import numpy as np

from audio.gain_wav import apply_adaptive_gain, apply_fixed_gain, read_wav, write_wav


class GainWavTests(unittest.TestCase):
    def test_adaptive_gain_reaches_target(self):
        audio = np.array([-0.1, 0.0, 0.1], dtype=np.float32)
        gained, gain, old_peak = apply_adaptive_gain(audio, target_peak=0.8)

        self.assertAlmostEqual(old_peak, 0.1, places=5)
        self.assertAlmostEqual(gain, 8.0, places=5)
        self.assertAlmostEqual(float(np.max(np.abs(gained))), 0.8, places=5)

    def test_adaptive_gain_obeys_maximum(self):
        audio = np.array([-0.01, 0.01], dtype=np.float32)
        gained, gain, _ = apply_adaptive_gain(audio, target_peak=0.8, max_gain=4.0)

        self.assertEqual(gain, 4.0)
        self.assertAlmostEqual(float(np.max(np.abs(gained))), 0.04, places=5)

    def test_fixed_gain_uses_decibels(self):
        audio = np.array([-0.25, 0.25], dtype=np.float32)
        gained, gain, _ = apply_fixed_gain(audio, 6.0206)

        self.assertAlmostEqual(gain, 2.0, places=3)
        self.assertAlmostEqual(float(np.max(np.abs(gained))), 0.5, places=3)

    def test_wav_round_trip_keeps_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "test.wav")
            audio = np.array([-0.5, 0.0, 0.5], dtype=np.float32)
            write_wav(path, audio, 48000, 1)
            loaded, sample_rate, channels = read_wav(path)

            self.assertEqual(sample_rate, 48000)
            self.assertEqual(channels, 1)
            self.assertEqual(len(loaded), len(audio))

            with wave.open(path, "rb") as wav_file:
                self.assertEqual(wav_file.getsampwidth(), 2)


if __name__ == "__main__":
    unittest.main()
