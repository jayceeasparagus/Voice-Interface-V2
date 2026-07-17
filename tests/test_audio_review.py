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

    def test_yes_labels_command_audio_as_success(self):
        handled = self.logger.handle_phrase(
            "Dog sit down",
            "sit down",
            self.audio,
        )
        self.assertFalse(handled)
        self.assertTrue(os.path.exists(self.logger.pending_path))

        self.logger.command_finished()
        self.assertTrue(self.logger.waiting_for_feedback)

        handled = self.logger.handle_phrase("yes", None, self.audio)
        self.assertTrue(handled)
        self.assertIsNone(self.logger.pending_path)

        files = os.listdir(self.logger.success_dir)
        self.assertEqual(len(files), 1)

        with wave.open(os.path.join(self.logger.success_dir, files[0]), "rb") as wav:
            self.assertEqual(wav.getframerate(), 16000)
            self.assertEqual(wav.getnchannels(), 1)

    def test_no_labels_command_audio_as_fail(self):
        handled = self.logger.handle_phrase(
            "dog please sit down",
            "please sit down",
            self.audio,
        )
        self.assertFalse(handled)

        self.logger.command_finished()
        handled = self.logger.handle_phrase("know", None, self.audio)
        self.assertTrue(handled)
        files = os.listdir(self.logger.fail_dir)
        self.assertEqual(len(files), 1)

    def test_feedback_is_not_accepted_before_command_finishes(self):
        self.logger.handle_phrase("dog stand", "stand", self.audio)
        handled = self.logger.handle_phrase("yes", None, self.audio)
        self.assertTrue(handled)
        self.assertIsNotNone(self.logger.pending_path)
        self.assertTrue(
            self.logger.pending_path.startswith(self.logger.pending_dir)
        )


if __name__ == "__main__":
    unittest.main()
