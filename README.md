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

Wake word is controlled in `audio/config.py`:

```python
WAKE_WORD_ENABLED = True
WAKE_WORD = "dog"
WAKE_WORDS = ["dog", "dogs"]
```

For testing without a wake word:

set `WAKE_WORD_ENABLED = False` in `audio/config.py`, then run the listener again.

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

`transport/`

Validates mapped commands and sends them from the board to the dog over the
working Ethernet link.

Current transport test:

```sh
python3 -m transport.sender sit walk_forward --host 10.42.0.1
```

`transport/protocol.py` rejects unknown commands before anything is sent to the
dog. It sends simple JSON over TCP, like `{"command": "sit"}` or
`{"commands": ["stand", "sit"]}`.

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

Future tests for each module.

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
