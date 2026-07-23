import os
import re
import threading
import wave
from datetime import datetime

import numpy as np


AUDIO_REVIEW_ENABLED = True


def clean_label(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text)


class AudioReviewLogger:
    def __init__(self, base_dir=None, sample_rate=48000):
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir or os.path.join(project_dir, "audio_debug")
        self.sample_rate = sample_rate
        self.lock = threading.Lock()

        self.orientation_dir = os.path.join(self.base_dir, "orientation quiet test")

        os.makedirs(self.orientation_dir, exist_ok=True)

    def handle_phrase(self, heard_text, command_text, audio):
        with self.lock:
            if not command_text:
                return True

            path = self.save_wav(heard_text, audio)
            print("Saved orientation test audio:", path)
            return False

    def command_finished(self):
        return

    def save_wav(self, heard_text, audio):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        short_text = clean_label(heard_text).replace(" ", "_")[:50]
        short_text = short_text or "unknown"
        filename = "{}_{}.wav".format(timestamp, short_text)
        path = os.path.join(self.orientation_dir, filename)

        samples = np.clip(audio, -1.0, 1.0)
        samples = (samples * 32767).astype(np.int16)

        with wave.open(path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples.tobytes())

        return path
