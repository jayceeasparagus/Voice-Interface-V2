# V2 Architecture

V2 is organized around one clear pipeline:

```text
Audio -> LLM -> Function Call -> Transport -> Dog
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

## LLM

The LLM module turns text into intent.

Planned responsibilities:

- Liquid AI integration
- prompt design
- intent JSON output
- fallback if the model fails

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
