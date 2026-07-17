import os
import re
import threading
import wave
from datetime import datetime

import numpy as np


AUDIO_REVIEW_ENABLED = True

YES_WORDS = {"yes", "yeah", "yep", "correct", "worked", "success"}
NO_WORDS = {"no", "know", "nope", "failed", "failure", "wrong"}


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
        self.waiting_for_feedback = False
        self.lock = threading.Lock()

        self.pending_dir = os.path.join(self.base_dir, "pending_audio")
        self.success_dir = os.path.join(self.base_dir, "success_audio")
        self.fail_dir = os.path.join(self.base_dir, "fail_audio")

        os.makedirs(self.pending_dir, exist_ok=True)
        os.makedirs(self.success_dir, exist_ok=True)
        os.makedirs(self.fail_dir, exist_ok=True)

    def handle_phrase(self, heard_text, command_text, audio):
        with self.lock:
            if self.waiting_for_feedback:
                label = self.get_label(heard_text)
                if label:
                    self.label_pending_file(label)
                else:
                    print("\nFeedback not recognized.")
                    print("SAY YES OR NO NOW. You can also say success or failure.\n")
                return True

            if self.pending_path:
                print("Command is still being processed. Wait for the result prompt.")
                return True

            if not command_text:
                return True

            self.pending_path = self.save_wav(heard_text, audio)
            print("Saved command audio:", self.pending_path)
            return False

    def command_finished(self):
        with self.lock:
            if not self.pending_path:
                return

            self.waiting_for_feedback = True
            print("\n========================================")
            print("COMMAND ATTEMPT FINISHED")
            print("Recording your result now.")
            print("SAY YES if it worked, or NO if it failed.")
            print("You can also say SUCCESS or FAILURE.")
            print("========================================\n")

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
        path = os.path.join(self.pending_dir, filename)

        samples = np.clip(audio, -1.0, 1.0)
        samples = (samples * 32767).astype(np.int16)

        with wave.open(path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples.tobytes())

        return path

    def label_pending_file(self, label):
        filename = os.path.basename(self.pending_path)
        if label == "success":
            target_dir = self.success_dir
        else:
            target_dir = self.fail_dir

        target_path = os.path.join(target_dir, filename)
        os.replace(self.pending_path, target_path)
        self.pending_path = None
        self.waiting_for_feedback = False

        print("Audio labeled {}: {}".format(label, target_path))
