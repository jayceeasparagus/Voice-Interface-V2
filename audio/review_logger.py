import os
import re
import wave
from datetime import datetime

import numpy as np


AUDIO_REVIEW_ENABLED = True

YES_WORDS = {"yes", "yeah", "yep", "correct", "worked", "success"}
NO_WORDS = {"no", "nope", "failed", "failure", "wrong"}


def clean_label(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text)


class AudioReviewLogger:
    def __init__(self, base_dir=None, sample_rate=16000):
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir or os.path.join(project_dir, "audio_debug")
        self.sample_rate = sample_rate
        self.pending_path = None

        self.unlabeled_dir = os.path.join(self.base_dir, "unlabeled_audio")
        self.success_dir = os.path.join(self.base_dir, "success_audio")
        self.fail_dir = os.path.join(self.base_dir, "fail_audio")

        for folder in (self.unlabeled_dir, self.success_dir, self.fail_dir):
            os.makedirs(folder, exist_ok=True)

    def handle_phrase(self, heard_text, command_text, audio):
        label = self.get_label(heard_text)

        if self.pending_path and label:
            self.move_pending_file(label)
            return True

        if self.pending_path:
            print("Feedback not recognized. Say only yes or no.")
            return True

        self.pending_path = self.save_wav(heard_text, audio)
        print("Saved audio:", self.pending_path)

        if command_text:
            print("After the command attempt, say yes or no.")
            return False

        print("No wake-word command detected. Say yes or no to label this audio.")
        return True

    def get_label(self, text):
        words = set(clean_label(text).split())
        has_yes = bool(words & YES_WORDS)
        has_no = bool(words & NO_WORDS)

        if has_yes and not has_no:
            return "success"
        if has_no and not has_yes:
            return "fail"
        return None

    def save_wav(self, heard_text, audio):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        short_text = clean_label(heard_text).replace(" ", "_")[:50]
        short_text = short_text or "unknown"
        filename = "{}_{}.wav".format(timestamp, short_text)
        path = os.path.join(self.unlabeled_dir, filename)

        samples = np.clip(audio, -1.0, 1.0)
        samples = (samples * 32767).astype(np.int16)

        with wave.open(path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples.tobytes())

        return path

    def move_pending_file(self, label):
        target_dir = self.success_dir if label == "success" else self.fail_dir
        target_path = os.path.join(target_dir, os.path.basename(self.pending_path))
        os.replace(self.pending_path, target_path)
        self.pending_path = None

        print("Audio labeled {}: {}".format(label, target_path))

