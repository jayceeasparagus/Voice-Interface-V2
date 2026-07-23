# Voice Interface V2

This repo is the clean V2 structure for the robot dog voice interface.

## Pipeline

```text
Audio
  -> Mapping
  -> Transport
  -> Dog
```

## Module Responsibilities

`audio/`

Processes speech into text. This is where microphone input, Moonshine
speech-to-text, and future SR80 audio features belong.

Current audio entry point:

```sh
python3 -m audio.listener
```

Wake words are controlled near the top of `audio/listener.py`:

```python
WAKE_WORD_ENABLED = True
WAKE_WORDS = ["dog", "dogs"]
```

For testing without a wake word:

```sh
python3 -m audio.listener --no-wake-word
```

To test the SR80 audio review logger by itself:

```sh
python3 -m audio.listener --desk-test
```

This does not send anything to the dog. Say a command phrase. The terminal
prints what it heard, then prints `SAY YES OR NO NOW`. Say `yes` if the speech
text was right or `no` if it was wrong. You can also say `success` or `failure`.

Shortcut script:

```sh
sh scripts/test_audio_desk.sh
```

```text
audio_debug/pending_audio/
audio_debug/success_audio/
audio_debug/fail_audio/
```

Command recordings are first saved in `pending_audio`. After you say `yes` or
`no`, the clip moves to `success_audio` or `fail_audio`. The normal
`python3 main.py` pipeline enables audio review by default. Use
`python3 main.py --no-audio-review` to turn it off. Feedback words do not need a
wake word and are not sent to the dog.
If `dog` is spoken by itself, the following command phrase is the clip that is
saved and labeled.
Listen to a saved clip on the SL1680 with:

```sh
aplay audio_debug/success_audio/CLIP_NAME.wav
```

`mapping/`

Processes text into robot command intent. This currently uses a lightweight
embedding-style text mapper so the project stays self-contained.

Current mapping helpers:

```sh
python3 -m mapping.text_split "sit down then walk forward"
python3 -m mapping.sqlite_mapper "set then can you walk straight"
```

`text_split.py` uses hardcoded splitting rules. `sqlite_mapper.py` loads
`qa_pairs.json` and uses lightweight text vectors to map text to commands.
Common Moonshine mishears can be configured in `mapping/fixes.py`.

Liquid AI can still be added later as another mapping backend.

`speaker/`

Contains the future spoken feedback path. The two flags near the top of
`speaker/speaker.py` independently control feedback for low-confidence command
matches and speech that does not resemble a command:

```python
SPEAK_ON_LOW_CONFIDENCE = True
SPEAK_ON_NON_COMMAND = True
```

The main pipeline currently prints what the speaker would say. To test that
without audio:

```sh
python3 speaker/speaker.py -m "test message" --print-only
```

To test real Piper speech on the SL1680, download the voice once and then run:

```sh
python3 -m piper.download_voices --data-dir speaker/voices en_US-lessac-low
python3 speaker/speaker.py -m "test message" -d plughw:1,0
```

The output device can be changed near the top of `speaker/speaker.py` or with
`-d`.

`transport/`

Validates mapped commands and sends them from the board to the dog over the
working Ethernet link.

Current transport test:

```sh
python3 -m transport.sender sit walk_forward --host 10.42.0.1
python3 -m transport.sender walk_forward --distance-m 0.5 --host 10.42.0.1
python3 -m transport.sender rotate_left --degrees 90 --host 10.42.0.1
```

`transport/protocol.py` rejects unknown commands before anything is sent to the
dog. It sends simple JSON over TCP, like `{"command": "sit"}` or
`{"commands": [{"command": "stand"}, {"command": "sit"}]}`.

Movement and rotation can include simple parameters:

```json
{"command": "walk_forward", "params": {"distance_m": 1.0}}
{"command": "rotate_left", "params": {"degrees": 90}}
```

`dog/`

Receives command batches and executes them on the Unitree Go2.

Current dog receiver:

```sh
python3 -m dog.receiver --message-only
python3 -m dog.receiver
```

Use `--message-only` to test networking without moving the dog.

`docs/`

Design notes, planning, and setup notes.

`tests/`

Focused tests for mapping and the TCP command protocol.

## End-to-End Testing

Local tests, no dog:

```sh
python3 -m unittest tests.test_pipeline
```

Board dry-run, no microphone and no dog:

```sh
python3 main.py --debug "sit then walk forward" --dry-run
python3 main.py --debug "turn around" --dry-run
```

Dog-side message-only receiver, no movement:

```sh
python3 -m dog.receiver --message-only
```

Board sends a typed command to the dog receiver:

```sh
python3 main.py --debug "sit then walk forward"
```

Live microphone pipeline:

```sh
python3 main.py
```

## Service Templates

Use only one service on each device:

- `board-voice.service`
- `dog-voice.service`

Do not make separate wired-network services. Each service already handles both
jobs:

- board service: configures `eth0` as `10.42.0.2`, then runs `main.py`
- dog service: configures `eth0` as `10.42.0.1`, then runs `dog.receiver`

Before using the scripts on Linux, make them executable:

```sh
chmod +x scripts/*.sh
```

If old V1 services still exist, disable them before using V2:

```sh
sudo systemctl disable --now board-wired-network.service 2>/dev/null || true
sudo systemctl disable --now dog-wired-network.service 2>/dev/null || true
sudo systemctl disable --now speech-to-dog.service 2>/dev/null || true
sudo systemctl disable --now dog-voice-receiver.service 2>/dev/null || true
```

Install the V2 services:

```sh
sudo cp scripts/board-voice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now board-voice.service
sudo systemctl status board-voice.service --no-pager
```

On the dog:

```sh
sudo cp scripts/dog-voice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dog-voice.service
sudo systemctl status dog-voice.service --no-pager
```
