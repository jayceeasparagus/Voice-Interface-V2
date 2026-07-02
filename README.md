# Voice Interface V2

This repo is the clean V2 structure for the robot dog voice interface.

No implementation code is written yet. The current goal is to agree on the
project layout before building each module.

## Pipeline

```text
Audio
  -> LLM
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

`llm/`

Processes text into intent. This is where Liquid AI should eventually run.

`function_call/`

Processes intent into a safe, structured function call. This layer should
validate allowed robot actions before anything is sent to the dog.

`transport/`

Sends validated function calls from the board to the dog, likely over the
working Ethernet link.

`dog/`

Receives function calls and executes them on the Unitree Go2.

`docs/`

Design notes, planning, and setup notes.

`tests/`

Future tests for each module.
