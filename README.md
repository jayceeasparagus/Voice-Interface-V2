# Voice Interface V2

This repo is the clean V2 structure for the robot dog voice interface.

No implementation code is written yet. The current goal is to agree on the
project layout before building each module.

## Pipeline

```text
Audio
  -> Mapping
  -> Function Call
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
```

For testing without a wake word:

set `WAKE_WORD_ENABLED = False` in `audio/config.py`, then run the listener again.

`mapping/`

Processes text into robot command intent. This currently uses a lightweight
sqlite-backed text mapper so the project stays self-contained.

Current mapping helpers:

```sh
python3 -m mapping.text_split "sit down then walk forward"
python3 -m mapping.sqlite_mapper "set then can you walk straight"
```

`text_split.py` uses hardcoded splitting rules. `sqlite_mapper.py` loads
`qa_pairs.json` into a local sqlite database and uses lightweight text vectors
to map text to commands. Common Moonshine mishears can be configured in
`mapping/fixes.py`.

The repo includes `python3-sqlite3_3.10.13-r0_arm64.deb`, copied from V1, in
case the board Python is missing sqlite3 support.

If `import sqlite3` fails on the board, install the included package:

```sh
sudo dpkg -i python3-sqlite3_3.10.13-r0_arm64.deb
```

Liquid AI can still be added later as another mapping backend.

`function_call/`

Processes intent into a safe, structured function call. This layer should
validate allowed robot actions before anything is sent to the dog.

Current function-call helpers:

```sh
python3 -m function_call.builder sit
python3 -m function_call.builder sit walk_forward
```

`builder.py` accepts one mapped command or an ordered list of mapped command
results. It outputs validated `go2_function_call` objects for transport.
Unknown commands are marked invalid instead of being sent as robot actions.

`transport/`

Sends validated function calls from the board to the dog, likely over the
working Ethernet link.

Current transport test:

```sh
python3 -m transport.sender sit --host 10.42.0.1
```

`dog/`

Receives function calls and executes them on the Unitree Go2.

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

Board dry-run, no microphone and no dog:

```sh
python3 main.py --debug "sit then walk forward" --dry-run
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

Service templates live in `scripts/`:

- `board-voice.service`
- `dog-voice.service`

The board service configures `eth0` as `10.42.0.2` and runs `main.py`.
The dog service configures `eth0` as `10.42.0.1` and runs `dog.receiver`.
