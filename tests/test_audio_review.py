import os
import tempfile
import unittest
import wave

import numpy as np

from audio.review_logger import AudioReviewLogger


class AudioReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.logger = AudioReviewLogger(base_dir=self.temp_dir.name)
        self.audio = np.linspace(-0.5, 0.5, 1600, dtype=np.float32)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_yes_moves_command_audio_to_success(self):
        handled = self.logger.handle_phrase(
            "Dog sit down",
            "sit down",
            self.audio,
        )
        self.assertFalse(handled)
        self.assertTrue(os.path.exists(self.logger.pending_path))

        handled = self.logger.handle_phrase("yes", None, self.audio)
        self.assertTrue(handled)
        self.assertIsNone(self.logger.pending_path)

        files = os.listdir(self.logger.success_dir)
        self.assertEqual(len(files), 1)
        self.assertEqual(os.listdir(self.logger.fail_dir), [])

        with wave.open(os.path.join(self.logger.success_dir, files[0]), "rb") as wav:
            self.assertEqual(wav.getframerate(), 16000)
            self.assertEqual(wav.getnchannels(), 1)

    def test_no_moves_non_wake_audio_to_fail(self):
        handled = self.logger.handle_phrase(
            "please sit down",
            None,
            self.audio,
        )
        self.assertTrue(handled)

        handled = self.logger.handle_phrase("no", None, self.audio)
        self.assertTrue(handled)
        self.assertEqual(len(os.listdir(self.logger.fail_dir)), 1)
        self.assertEqual(os.listdir(self.logger.success_dir), [])


if __name__ == "__main__":
    unittest.main()

