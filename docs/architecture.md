# V2 Architecture

V2 is organized around one clear pipeline:

```text
Audio -> Mapping -> Transport -> Dog
```

## Audio

The audio module turns speech into text.

Planned responsibilities:

- microphone input
- Moonshine speech-to-text
- SR80 support later
- optional noise filtering or background chatter handling

The first implementation listens through ALSA, uses VAD to split long pauses
into utterances, and optionally gates output behind a wake word.

## Mapping

The mapping module turns text into command intent.

Current responsibilities:

- split one utterance into ordered tasks
- apply configurable text fixes for common speech-to-text mistakes
- load command examples from `qa_pairs.json`
- map each task to a Go2 command with lightweight text vectors
- return `unknown` when similarity is too low

Liquid AI can be added later as a second backend, but the lightweight mapper is
the stable default for V2 right now because it avoids a large model download.

## Transport

The transport module validates mapped commands and sends them to the dog.

Planned responsibilities:

- allowed command list
- unknown/unsafe command rejection
- JSON message format
- Ethernet board-to-dog socket connection
- bounded socket and command execution timeouts
- future wireless option if needed

Current behavior:

- accepts mapping result dictionaries or plain command strings
- preserves the order from the original spoken sentence
- rejects unknown/disallowed commands
- sends simple JSON over TCP, like `{"command": "sit"}`
- reads complete newline-terminated messages even when TCP splits the data
- waits for a dog response
- supports wired and wireless host settings in `transport/config.py`

## Dog

The dog module receives and executes commands.

Planned responsibilities:

- receiver service
- Unitree SDK command execution
- posture commands
- movement commands
- 180-degree turn command
- stop/release behavior

Current behavior:

- listens for simple command JSON on TCP port 5005
- supports `--message-only` testing with no movement
- rejects invalid command messages
- stops a command if its executor exceeds the time limit
- executes valid commands through the tested V1 SportClient/ObstacleClient pattern
- leaves posture transitions to the Go2 high-level API
