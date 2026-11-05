# Voice API reference

Distilled from the pages under `https://mastra.ai/reference/voice/`. Provider-specific constructors live in [`providers.md`](providers.md). Verify against the installed version before relying on an option.

## Contents

- Agent integration
- speak()
- listen()
- getSpeakers()
- Realtime methods
- Events
- CompositeVoice
- MastraVoice (custom providers)
- Audio helpers

---

## Agent integration

Set `voice` on the agent: `voice: IMastraVoice | ({ requestContext }) => IMastraVoice | Promise<IMastraVoice>`. A function creates one provider per request. Access it as `agent.voice`, or resolve it with `await agent.getVoice({ requestContext })`. The provider supplies TTS, STT, or STS depending on its class. Realtime providers combine their own instructions and tools with the agent's.

---

## `voice.speak(input, options?)`

| Parameter | Type | Notes |
|---|---|---|
| `input` | `string \| NodeJS.ReadableStream` | Text, or a stream of text (usually converted to a string first) |
| `options.speaker` | `string` | Voice id for this call. Overrides the constructor default. |
| `options.*` | provider-specific | OpenAI `speed` (0.25 to 4.0), `responseFormat`; ElevenLabs `stability`, `similarity_boost`; Google `languageCode`, `audioConfig`; Murf `properties` (`rate`, `pitch`, `format`) |
| `options.providerOptions` | object | With AI SDK speech models inside `CompositeVoice`, for example `{ elevenlabs: { stability: 0.5 } }` |

Returns `Promise<NodeJS.ReadableStream | void>`. `void` on realtime providers, which emit audio through `speaker`/`speaking` events. Output format depends on the provider (MP3, WAV, OGG, PCM).

---

## `voice.listen(audioStream, options?)`

| Parameter | Type | Notes |
|---|---|---|
| `audioStream` | `NodeJS.ReadableStream \| unknown` | File stream or microphone stream |
| `options.*` | provider-specific | OpenAI `filetype`, `prompt`, `language`; Google `stream`, `config`; Deepgram `model`, `language` |
| `options.providerOptions` | object | With AI SDK transcription models inside `CompositeVoice` |

Returns `Promise<string>`, `Promise<NodeJS.ReadableStream>` (streaming transcription), or `Promise<void>` on realtime providers (text arrives as `writing` events). Not supported by TTS-only providers.

---

## `voice.getSpeakers(options?)`

Returns `Promise<Array<{ voiceId: string } & metadata>>`. Most providers take no options. Google accepts `{ languageCode }`. ElevenLabs adds `name`, `language`, `gender`.

---

## Realtime methods

Implemented by realtime providers. Non-realtime providers inherit no-op defaults that log a debug message and resolve.

| Method | Signature | Notes |
|---|---|---|
| `connect(options?)` | `Promise<void>` | Opens the WebSocket or WebRTC session. Required before `send()`/`answer()`. Rejects on handshake failure or timeout. OpenAI Realtime accepts `{ requestContext }` for tools. Retry on the same instance after a failure. |
| `send(audioData)` | `(NodeJS.ReadableStream \| Int16Array) => Promise<void>` | Streams audio to the provider. |
| `answer(options?)` | `Promise<void>` | Triggers a response after user input. |
| `addInstructions(text)` | `void` | Extra instructions. Call before `connect()`. Replace or append depends on the provider. |
| `addTools(tools)` | `(ToolsInput) => void` | Tools the realtime model can call, for example `{ getWeather: weatherTool }`. |
| `updateConfig(options)` | `(Record<string, unknown>) => void` | Runtime config, for example OpenAI Realtime `{ voice, turn_detection }`. Some changes need a reconnect. |
| `on(event, callback)` / `off(event, callback)` | `void` | Register and remove listeners. |
| `close()` | `void` | Ends the session and frees resources. Call `connect()` again for a new session. |

Provider extras: OpenAI Realtime `updateSession()`, `sendEvent()`; Gemini Live `sendContext()`, `updateSessionConfig()`, `disconnect()`; Nova Sonic `endAudioInput()`, `getListener()`; xAI `commitAudioBuffer()`, `clearAudioBuffer()`, `cancelResponse()`; Inworld Realtime `commitInput()`, `clearInput()`, `clearOutput()`.

---

## Events

| Event | Payload | Notes |
|---|---|---|
| `speaker` | `NodeJS.ReadableStream` (some providers pass `{ audio }`) | New audio stream to pipe to output |
| `speaking` | `{ audio?: string }` or provider shape (Nova Sonic `{ audioData }`) | Audio data available |
| `speaking.done` | object | Finished speaking |
| `writing` | `{ text, role: 'assistant' \| 'user' }` | Transcribed or generated text |
| `error` | `{ message, code?, details? }` | Errors, including tool errors on some providers |
| `session.created`, `session.updated` | object | Session lifecycle |
| `response.created`, `response.done` | object | Response lifecycle |
| `tool-call-start`, `tool-call-result` | object | Tool execution |

Not every provider emits every event. Payload shapes vary. Some providers also emit raw provider events (for example xAI `response.done`, Gemini `turnComplete`).

---

## CompositeVoice

Import: `import { CompositeVoice } from '@mastra/core/voice'`

| Option | Type | Notes |
|---|---|---|
| `input` | `IMastraVoice \| TranscriptionModel` | STT provider. AI SDK transcription models are wrapped automatically. |
| `output` | `IMastraVoice \| SpeechModel` | TTS provider. AI SDK speech models are wrapped automatically. |
| `realtime` | `IMastraVoice` | Speech-to-speech provider |

Behavior:

- `speak()` uses `realtime` if set, else `output`. `listen()` uses `realtime` if set, else `input`.
- `getSpeakers()` uses `realtime` if set, else `output`.
- Throws `MastraError` only when no provider can handle the call.
- `connect()` and `send()` forward to `realtime`. `send()` without one throws `VOICE_COMPOSITE_NO_REALTIME_PROVIDER_SEND`.

---

## MastraVoice (custom providers)

Import: `import { MastraVoice } from '@mastra/core/voice'`. Abstract base class.

Constructor config:

| Field | Type |
|---|---|
| `speechModel` | `{ name, apiKey }` (BuiltInModelConfig) |
| `listeningModel` | `{ name, apiKey }` |
| `speaker` | `string` |
| `name` | `string` |
| `realtimeConfig` | `{ model?, apiKey?, options? }` |

Abstract: `speak()`, `listen()`. Optional: `getSpeakers()`, `connect()`, `send()`, `answer()`, `addTools()`, `close()`, `on()`, `off()`. Method calls are traced automatically.

---

## Audio helpers

`@mastra/node-audio` exports `playAudio(stream)` and `getMicrophoneStream()` for Node. Some reference pages pipe `speaker` streams into `new Speaker({ sampleRate, channels, bitDepth })` from `@mastra/node-speaker`.
