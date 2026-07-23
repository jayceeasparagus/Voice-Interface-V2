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

    def test_command_audio_goes_to_orientation_test_folder(self):
        handled = self.logger.handle_phrase(
            "Dog sit down",
            "sit down",
            self.audio,
        )
        self.assertFalse(handled)

        files = os.listdir(self.logger.orientation_dir)
        self.assertEqual(len(files), 1)
        self.assertIn("dog_sit_down", files[0])

        with wave.open(os.path.join(self.logger.orientation_dir, files[0]), "rb") as wav:
            self.assertEqual(wav.getframerate(), 48000)
            self.assertEqual(wav.getnchannels(), 1)

    def test_command_finished_does_not_wait_for_feedback(self):
        handled = self.logger.handle_phrase(
            "dog please sit down",
            "please sit down",
            self.audio,
        )
        self.assertFalse(handled)

        self.logger.command_finished()
        files = os.listdir(self.logger.orientation_dir)
        self.assertEqual(len(files), 1)

    def test_empty_command_text_is_ignored(self):
        self.logger.handle_phrase("dog stand", "stand", self.audio)
        handled = self.logger.handle_phrase("yes", None, self.audio)
        self.assertTrue(handled)
        files = os.listdir(self.logger.orientation_dir)
        self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()
