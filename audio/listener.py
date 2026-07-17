import argparse
import json
import os
import re
import select
import subprocess
import time

import numpy as np
import onnxruntime
import requests
from silero_vad import VADIterator, load_silero_vad
from tokenizers import Tokenizer


WAKE_WORDS = ["dog", "dogs"]
WAKE_WORD_ENABLED = True

AUDIO_DEVICE = "plughw:1,0"
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 512
MAX_SPEECH_SECONDS = 12
MOONSHINE_MODEL = "base"
AUDIO_READ_TIMEOUT_S = 5
AUDIO_RETRY_DELAY_S = 1


def clean_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def download_model_file(repo_id, filename):
    local_path = os.path.join("models", repo_id, filename)
    if os.path.exists(local_path):
        return local_path

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    url = "https://huggingface.co/{}/resolve/main/{}".format(repo_id, filename)

    print("Downloading:", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    with open(local_path, "wb") as file:
        file.write(response.content)

    return local_path


class MoonshineSTT:
    def __init__(self, model=MOONSHINE_MODEL):
        config_repo = "UsefulSensors/moonshine-{}".format(model)
        onnx_repo = "UsefulSensors/moonshine"

        config_path = download_model_file(config_repo, "config.json")
        tokenizer_path = download_model_file(config_repo, "tokenizer.json")
        encoder_path = download_model_file(
            onnx_repo,
            "onnx/merged/{}/quantized/encoder_model.onnx".format(model),
        )
        decoder_path = download_model_file(
            onnx_repo,
            "onnx/merged/{}/quantized/decoder_model_merged.onnx".format(model),
        )

        with open(config_path, "r") as file:
            self.model_config = json.load(file)

        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        self.encoder_session = onnxruntime.InferenceSession(encoder_path)
        self.decoder_session = onnxruntime.InferenceSession(decoder_path)

        self.eos_token_id = self.model_config["eos_token_id"]
        self.decoder_start_token_id = self.model_config["decoder_start_token_id"]
        self.num_key_value_heads = self.model_config["decoder_num_key_value_heads"]
        self.dim_kv = (
            self.model_config["hidden_size"]
            // self.model_config["decoder_num_attention_heads"]
        )
        self.decoder_layers = self.model_config["decoder_num_hidden_layers"]
        self.max_len = self.model_config["max_position_embeddings"]

        self.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32))

    def transcribe(self, audio):
        audio = audio.astype(np.float32)[np.newaxis, :]
        tokens = self.generate_tokens(audio)
        return self.tokenizer.decode_batch(tokens, skip_special_tokens=True)[0].strip()

    def generate_tokens(self, audio):
        max_len = min((audio.shape[-1] // SAMPLE_RATE) * 6, self.max_len)
        encoder_output = self.encoder_session.run(None, {"input_values": audio})[0]
        batch_size = encoder_output.shape[0]

        generated_tokens = np.array(
            [[self.decoder_start_token_id]] * batch_size,
            dtype=np.int64,
        )

        past_kv = {
            "past_key_values.{}.{}.{}".format(layer, module, key): np.zeros(
                [batch_size, self.num_key_value_heads, 0, self.dim_kv],
                dtype=np.float32,
            )
            for layer in range(self.decoder_layers)
            for module in ("decoder", "encoder")
            for key in ("key", "value")
        }

        for index in range(max_len):
            use_cache = index > 0
            decoder_inputs = {
                "input_ids": generated_tokens[:, -1:],
                "encoder_hidden_states": encoder_output,
                "use_cache_branch": [use_cache],
                **past_kv,
            }

            output = self.decoder_session.run(None, decoder_inputs)
            logits = output[0]
            present_kv = output[1:]
            next_tokens = logits[:, -1].argmax(axis=-1, keepdims=True)

            for kv_index, key in enumerate(past_kv):
                if not use_cache or "decoder" in key:
                    past_kv[key] = present_kv[kv_index]

            generated_tokens = np.concatenate([generated_tokens, next_tokens], axis=-1)

            if (next_tokens == self.eos_token_id).all():
                break

        return generated_tokens


class AudioListener:
    def __init__(
        self,
        wake_word_enabled=WAKE_WORD_ENABLED,
        handler=None,
        phrase_handler=None,
    ):
        self.wake_word_enabled = wake_word_enabled
        self.handler = handler
        self.phrase_handler = phrase_handler
        self.waiting_for_command = False
        self.last_audio = None
        self.last_heard_text = None
        self.stt = MoonshineSTT()
        self.vad_model = load_silero_vad(onnx=True)
        self.vad = VADIterator(
            model=self.vad_model,
            sampling_rate=SAMPLE_RATE,
            threshold=0.3,
            min_silence_duration_ms=300,
        )

    def run(self):
        print("Audio test running.")
        print("Device:", AUDIO_DEVICE)
        print("Wake word enabled:", self.wake_word_enabled)
        print("Wake words:", ", ".join(WAKE_WORDS))
        print("Say a wake word plus a command, like: dog stand")

        while True:
            try:
                text = self.listen_once()
            except KeyboardInterrupt:
                raise
            except Exception as error:
                print("Audio error:", error)
                print("Restarting audio in 1 second...")
                time.sleep(AUDIO_RETRY_DELAY_S)
                continue

            wake_only = text is None and self.waiting_for_command
            if (
                self.phrase_handler
                and self.last_heard_text is not None
                and not wake_only
            ):
                handled = self.phrase_handler(
                    self.last_heard_text,
                    text,
                    self.last_audio,
                )
                if handled:
                    continue

            if not text:
                continue

            if self.handler:
                self.handler(text)
            else:
                print("TEXT:", text)

    def listen_once(self):
        self.last_audio = None
        self.last_heard_text = None
        audio = self.record_one_phrase()
        if audio.size == 0 or not np.isfinite(audio).all():
            raise RuntimeError("Audio recorder returned bad data.")

        heard_text = self.stt.transcribe(audio)

        if not heard_text:
            return None

        self.last_audio = audio
        self.last_heard_text = heard_text
        print("HEARD:", heard_text)
        return self.apply_wake_word(heard_text)

    def apply_wake_word(self, text):
        text = clean_text(text)

        if not self.wake_word_enabled:
            return text

        words = text.split()
        wake_words = [clean_text(word) for word in WAKE_WORDS]

        for index, word in enumerate(words):
            if word in wake_words:
                command = " ".join(words[:index] + words[index + 1 :]).strip()
                if command:
                    self.waiting_for_command = False
                    return command

                self.waiting_for_command = True
                return None

        if self.waiting_for_command:
            self.waiting_for_command = False
            return text

        return None

    def record_one_phrase(self):
        recorder = self.start_recorder()
        lookback_size = 7 * CHUNK_SIZE
        audio = np.empty(0, dtype=np.float32)
        recording = False
        last_message = time.time()

        try:
            for chunk in self.read_chunks(recorder):
                if time.time() - last_message > 15:
                    print("Listening...")
                    last_message = time.time()

                audio = np.concatenate((audio, chunk))
                if not recording:
                    audio = audio[-lookback_size:]

                event = self.vad(chunk)

                if event and "start" in event:
                    recording = True

                if event and "end" in event and recording:
                    return audio

                if recording and len(audio) / SAMPLE_RATE > MAX_SPEECH_SECONDS:
                    return audio
        finally:
            self.stop_recorder(recorder)
            self.reset_vad()

    def start_recorder(self):
        command = [
            "arecord",
            "-D",
            AUDIO_DEVICE,
            "-f",
            "S16_LE",
            "-r",
            str(SAMPLE_RATE),
            "-c",
            str(CHANNELS),
        ]

        recorder = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=CHUNK_SIZE * CHANNELS * 2,
        )

        if recorder.stdout is None or recorder.stderr is None:
            self.stop_recorder(recorder)
            raise RuntimeError("Could not open arecord output.")

        return recorder

    def stop_recorder(self, recorder):
        if recorder.poll() is None:
            recorder.terminate()
            try:
                recorder.wait(timeout=2)
            except subprocess.TimeoutExpired:
                recorder.kill()
                recorder.wait()

        if recorder.stdout:
            recorder.stdout.close()
        if recorder.stderr:
            recorder.stderr.close()

    def read_chunks(self, recorder):
        read_size = CHUNK_SIZE * CHANNELS * 2

        while True:
            if recorder.poll() is not None:
                error_text = ""
                if recorder.stderr:
                    error_text = recorder.stderr.read().decode(errors="replace").strip()

                if error_text:
                    raise RuntimeError(
                        "arecord stopped with code {}: {}".format(
                            recorder.returncode,
                            error_text,
                        )
                    )

                raise RuntimeError(
                    "arecord stopped with code {}. Check AUDIO_DEVICE.".format(
                        recorder.returncode
                    )
                )

            ready, _, _ = select.select(
                [recorder.stdout, recorder.stderr],
                [],
                [],
                AUDIO_READ_TIMEOUT_S,
            )

            if not ready:
                raise RuntimeError("arecord stopped producing audio.")

            if recorder.stderr in ready:
                message = recorder.stderr.readline().decode(errors="replace").strip()
                if "overrun" in message.lower():
                    raise RuntimeError("arecord overrun.")

            if recorder.stdout not in ready:
                continue

            raw = recorder.stdout.read(read_size)
            if not raw:
                raise RuntimeError("arecord stopped. Check AUDIO_DEVICE.")
            if len(raw) != read_size:
                raise RuntimeError("arecord returned an incomplete audio chunk.")

            audio = np.frombuffer(raw, dtype=np.int16)
            if CHANNELS > 1:
                audio = audio.reshape(-1, CHANNELS)[:, 0]

            yield audio.astype(np.float32) / 32768.0

    def reset_vad(self):
        self.vad.triggered = False
        self.vad.temp_end = 0
        self.vad.current_sample = 0


def main():
    parser = argparse.ArgumentParser(description="Speech-to-text audio test.")
    parser.add_argument(
        "--no-wake-word",
        action="store_true",
        help="Print every phrase without requiring a wake word.",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Save each phrase and label it by saying yes or no.",
    )
    args = parser.parse_args()

    phrase_handler = None
    if args.review:
        from audio.review_logger import AudioReviewLogger

        phrase_handler = AudioReviewLogger().handle_phrase

    listener = AudioListener(
        wake_word_enabled=not args.no_wake_word,
        phrase_handler=phrase_handler,
    )
    listener.run()


if __name__ == "__main__":
    main()
