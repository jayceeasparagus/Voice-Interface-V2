import json
import os
import re
import subprocess
import threading
import time

import numpy as np
import onnxruntime
import requests
from silero_vad import VADIterator, load_silero_vad
from tokenizers import Tokenizer

from audio import config


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


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


class MoonshineSTT:
    def __init__(self, model=config.MOONSHINE_MODEL):
        self.model = model
        self.config_repo = "UsefulSensors/moonshine-{}".format(model)
        self.onnx_repo = "UsefulSensors/moonshine"

        model_config_path = download_model_file(
            repo_id=self.config_repo,
            filename="config.json",
        )
        tokenizer_path = download_model_file(
            repo_id=self.config_repo,
            filename="tokenizer.json",
        )
        encoder_path = download_model_file(
            repo_id=self.onnx_repo,
            filename="onnx/merged/{}/quantized/encoder_model.onnx".format(model),
        )
        decoder_path = download_model_file(
            repo_id=self.onnx_repo,
            filename="onnx/merged/{}/quantized/decoder_model_merged.onnx".format(model),
        )

        with open(model_config_path, "r") as file:
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

        self.transcribe(np.zeros(config.SAMPLE_RATE, dtype=np.float32))

    def transcribe(self, audio):
        audio = audio.astype(np.float32)[np.newaxis, :]
        tokens = self._generate(audio)
        return self.tokenizer.decode_batch(tokens, skip_special_tokens=True)[0].strip()

    def _generate(self, audio):
        max_len = min((audio.shape[-1] // config.SAMPLE_RATE) * 6, self.max_len)
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
            use_cache_branch = index > 0
            decoder_inputs = {
                "input_ids": generated_tokens[:, -1:],
                "encoder_hidden_states": encoder_output,
                "use_cache_branch": [use_cache_branch],
                **past_kv,
            }
            output = self.decoder_session.run(None, decoder_inputs)
            logits = output[0]
            present_kv = output[1:]
            next_tokens = logits[:, -1].argmax(axis=-1, keepdims=True)

            for kv_index, key in enumerate(past_kv):
                if not use_cache_branch or "decoder" in key:
                    past_kv[key] = present_kv[kv_index]

            generated_tokens = np.concatenate(
                [generated_tokens, next_tokens],
                axis=-1,
            )

            if (next_tokens == self.eos_token_id).all():
                break

        return generated_tokens


class AudioListener:
    def __init__(self, wake_word_enabled=config.WAKE_WORD_ENABLED, handler=None):
        self.wake_word_enabled = wake_word_enabled
        self.handler = handler
        self.awake = False
        self.stt = MoonshineSTT()
        self.vad_model = load_silero_vad(onnx=True)
        self.vad = VADIterator(
            model=self.vad_model,
            sampling_rate=config.SAMPLE_RATE,
            threshold=0.3,
            min_silence_duration_ms=300,
        )

    def run(self):
        recorder = self.start_recorder()
        self.start_error_logger(recorder)
        lookback_size = 7 * config.CHUNK_SIZE
        speech = np.empty(0, dtype=np.float32)
        recording = False
        start_time = time.time()
        last_heartbeat = time.time()

        print("Listening on:", config.AUDIO_DEVICE)
        print("Wake word enabled:", self.wake_word_enabled)
        print("Wake words:", ", ".join(config.WAKE_WORDS))
        print("Press Ctrl+C to stop.")
        print("Recorder command: arecord -D {} -f S16_LE -r {} -c {}".format(
            config.AUDIO_DEVICE,
            config.SAMPLE_RATE,
            config.CHANNELS,
        ))

        try:
            for chunk in self.read_chunks(recorder):
                if time.time() - last_heartbeat > 15:
                    print("Still listening...")
                    last_heartbeat = time.time()

                speech = np.concatenate((speech, chunk))
                if not recording:
                    speech = speech[-lookback_size:]

                event = self.vad(chunk)

                if event and "start" in event and not recording:
                    recording = True
                    start_time = time.time()

                if event and "end" in event and recording:
                    recording = False
                    self.handle_utterance(speech)
                    speech = np.empty(0, dtype=np.float32)
                    self.reset_vad()

                if recording and (len(speech) / config.SAMPLE_RATE) > 15:
                    recording = False
                    self.handle_utterance(speech)
                    speech = np.empty(0, dtype=np.float32)
                    self.reset_vad()

                if recording and time.time() - start_time > 0.5:
                    start_time = time.time()

        finally:
            recorder.terminate()
            recorder.wait()

    def start_recorder(self):
        command = [
            "arecord",
            "-D",
            config.AUDIO_DEVICE,
            "-f",
            "S16_LE",
            "-r",
            str(config.SAMPLE_RATE),
            "-c",
            str(config.CHANNELS),
        ]
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=config.CHUNK_SIZE * config.CHANNELS * 2,
        )

    def start_error_logger(self, recorder):
        def log_errors():
            for raw_line in iter(recorder.stderr.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line:
                    print("arecord:", line)

        thread = threading.Thread(target=log_errors, daemon=True)
        thread.start()

    def read_chunks(self, recorder):
        read_size = config.CHUNK_SIZE * config.CHANNELS * 2

        while True:
            raw = recorder.stdout.read(read_size)
            if not raw:
                raise RuntimeError("arecord stopped. Check AUDIO_DEVICE and microphone connection.")

            audio = np.frombuffer(raw, dtype=np.int16)
            if config.CHANNELS > 1:
                audio = audio.reshape(-1, config.CHANNELS)[:, 0]

            yield audio.astype(np.float32) / 32768.0

    def handle_utterance(self, speech):
        text = self.stt.transcribe(speech)
        if not text:
            return

        print("HEARD:", text)
        output_text = self.apply_wake_word(text)
        if output_text:
            if self.handler is not None:
                self.handler(output_text)
                return
            print("TEXT:", output_text, flush=True)

    def apply_wake_word(self, text):
        text = normalize_text(text)

        if not self.wake_word_enabled:
            return text

        words = text.split()

        wake_words = [normalize_text(wake_word) for wake_word in config.WAKE_WORDS]
        detected_wake_words = [wake_word for wake_word in wake_words if wake_word in words]

        if detected_wake_words:
            command_words = [word for word in words if word not in wake_words]
            command = " ".join(command_words).strip()

            if command:
                self.awake = False
                return command

            self.awake = True
            return None

        if self.awake and text:
            self.awake = False
            return text

        return None

    def reset_vad(self):
        self.vad.triggered = False
        self.vad.temp_end = 0
        self.vad.current_sample = 0


def main():
    listener = AudioListener(wake_word_enabled=config.WAKE_WORD_ENABLED)
    listener.run()


if __name__ == "__main__":
    main()
