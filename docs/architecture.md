# V2 Architecture

V2 is organized around one clear pipeline:

```text
Audio -> Mapping -> Function Call -> Transport -> Dog
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
- load command examples into sqlite
- map each task to a Go2 command with lightweight text vectors
- return `unknown` when similarity is too low

Liquid AI can be added later as a second backend, but the sqlite-backed mapper
is the stable default for V2 right now because it avoids a large model download.

## Function Call

The function call module turns intent into a safe robot action.

Planned responsibilities:

- allowed command list
- safety checks
- command arguments
- unknown/unsafe command rejection

## Transport

The transport module sends function calls to the dog.

Planned responsibilities:

- JSON message format
- Ethernet board-to-dog socket connection
- timeout/retry behavior
- future wireless option if needed

## Dog

The dog module receives and executes commands.

Planned responsibilities:

- receiver service
- Unitree SDK command execution
- posture commands
- movement commands
- stop/release behavior
