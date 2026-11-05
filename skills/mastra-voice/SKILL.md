---
name: mastra-voice
description: "Add voice to Mastra agents: text-to-speech with speak(), speech-to-text with listen(), realtime speech-to-speech with connect(), send(), answer(), and events, CompositeVoice to mix providers or AI SDK speech and transcription models, and LiveKit for interruptible phone and browser calls. Use this skill whenever the user wants an agent to talk or listen, transcribe audio, build a voice assistant, pick a voice provider, combine one provider for STT with another for TTS, or run a realtime voice session with tools. Triggers on Mastra voice, agent.voice, voice.speak, voice.listen, voice.connect, voice.send, voice.on('speaker'), CompositeVoice, MastraVoice, @mastra/voice-openai, @mastra/voice-openai-realtime, @mastra/voice-elevenlabs, @mastra/voice-deepgram, @mastra/voice-azure, @mastra/voice-google, @mastra/voice-google-gemini-live, @mastra/voice-xai-realtime, @mastra/voice-aws-nova-sonic, @mastra/livekit, @mastra/node-audio, TTS, STT, speech-to-speech."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Voice for agents: speak, listen, realtime speech-to-speech, CompositeVoice, LiveKit, and every voice provider"
  display_order: 11
  docs: https://mastra.ai/reference/voice/overview
---

# Mastra Voice

Give an agent a voice provider through its `voice` option. Every provider implements one interface: `speak()` for text-to-speech, `listen()` for speech-to-text, and `connect()`/`send()`/`on()` for realtime speech-to-speech.

---

## When to use

- Turning agent replies into audio (TTS)
- Transcribing audio files or microphone input before calling an agent (STT)
- Building a realtime voice assistant with streaming audio in and out (STS)
- Mixing providers: one for listening, another for speaking
- Using AI SDK speech or transcription models inside Mastra
- Running interruptible phone or browser calls through LiveKit
- Choosing a voice provider and its package, constructor, and env vars

## When NOT to use

- Agent definition, instructions, and `generate()` (use `mastra-agents`)
- Tool schemas for realtime voice tools (use `mastra-tools`)
- Text streaming of agent output (use `mastra-streaming`)
- Chat model providers and model IDs (use `mastra-models`)
- Custom API routes and server config around voice endpoints (use `mastra-server`)
- Voice delivered through messaging channels (use `mastra-channels`)
- Tracing voice calls (use `mastra-observability`)

---

## Required inputs

- The mode: TTS only, STT only, both, or realtime speech-to-speech
- The provider(s) and their API keys or cloud credentials
- Runtime: Node server, CLI with microphone and speaker, browser, or phone (LiveKit)
- Audio format expectations (MP3, WAV, PCM, sample rate)
- Default speaker voice and language
- Whether the voice session needs tools and request context

---

## The framework: one interface, three modes

```typescript
import { Agent } from '@mastra/core/agent'
import { OpenAIVoice } from '@mastra/voice-openai'
import { playAudio } from '@mastra/node-audio'
import { createReadStream } from 'fs'

const voiceAgent = new Agent({
  id: 'voice-agent',
  name: 'Voice Agent',
  instructions: 'You are a voice assistant that can help users with their tasks.',
  model: 'openai/gpt-6.1-sol',
  voice: new OpenAIVoice(),
})

// STT: audio in, text out
const transcript = await voiceAgent.voice.listen(createReadStream('./how_can_i_help_you.mp3'))

// Agent turn
const { text } = await voiceAgent.generate(transcript)

// TTS: text in, audio stream out
const audioStream = await voiceAgent.voice.speak(text, { speaker: 'default', responseFormat: 'wav' })
playAudio(audioStream)
```

| Mode | Methods | Returns | Providers |
|---|---|---|---|
| TTS | `speak(text, options)` | `NodeJS.ReadableStream` (or `void` on realtime providers) | OpenAI, Azure, ElevenLabs, Deepgram, Google, Murf, Speechify, Cloudflare, Sarvam, Mistral, Inworld, ModelsLab |
| STT | `listen(audio, options)` | `string`, a text stream, or `void` on realtime providers | OpenAI, Azure, Deepgram, Google, Sarvam, Mistral, Inworld, Gladia, ElevenLabs |
| STS | `connect()`, `send()`, `answer()`, `on()`, `close()` | events: `speaker`, `speaking`, `writing`, `error` | OpenAI Realtime, Gemini Live, xAI Realtime, AWS Nova Sonic, Inworld Realtime |

### Combine providers

```typescript
import { CompositeVoice } from '@mastra/core/voice'
import { OpenAIVoice } from '@mastra/voice-openai'
import { ElevenLabsVoice } from '@mastra/voice-elevenlabs'

const voice = new CompositeVoice({
  input: new OpenAIVoice({ listeningModel: { name: 'whisper-1', apiKey: process.env.OPENAI_API_KEY } }),
  output: new ElevenLabsVoice(),
})
```

`input` and `output` also accept AI SDK models such as `openai.transcription('whisper-1')` and `elevenlabs.speech('eleven_turbo_v2')`. A `realtime` provider, when set, handles `speak()` and `listen()` too.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed provider package types (for example `node_modules/@mastra/voice-openai`). Otherwise fetch `https://mastra.ai/reference/voice/overview.md` and the provider page under `https://mastra.ai/integrations/voice/`. Trust these over memory.
2. **Pick the mode and provider.** Use `references/providers.md`. Check that the provider supports the mode (several are TTS only or STT only).
3. **Install** the provider package (`@mastra/voice-<provider>`) and `@mastra/node-audio` if you play or record audio in Node.
4. **Set credentials** in `.env` with the variable the provider reads (for example `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `DEEPGRAM_API_KEY`).
5. **Attach** the provider (or a `CompositeVoice`) to the agent's `voice` option, or use it standalone.
6. **For realtime:** register `on('speaker')` and `on('writing')` listeners, `await voice.connect()` in a `try/catch`, then `speak()`/`send()`. Call `close()` when done.
7. **For live calls:** use `@mastra/livekit` with `liveKitConnectionRoute()` and a worker from `@mastra/livekit/worker` (see `references/providers.md`).
8. **Test** with a short known audio file and a fixed phrase. Confirm format, sample rate, and latency.

---

## Deep dive: realtime speech-to-speech

```typescript
import { Agent } from '@mastra/core/agent'
import { getMicrophoneStream, playAudio } from '@mastra/node-audio'
import { XAIRealtimeVoice } from '@mastra/voice-xai-realtime'

const agent = new Agent({
  id: 'voice-agent',
  name: 'Voice Agent',
  instructions: 'You are a helpful voice assistant.',
  model: 'xai/grok-4.3',
  voice: new XAIRealtimeVoice({
    apiKey: process.env.XAI_API_KEY,
    speaker: 'eve',
    turnDetection: { type: 'server_vad' },
  }),
})

await agent.voice.connect()
agent.voice.on('speaker', audioStream => playAudio(audioStream))
agent.voice.on('writing', ({ text, role }) => console.log(`${role}: ${text}`))
agent.voice.on('error', ({ message, code }) => console.error(code, message))

await agent.voice.speak('How can I help you today?')
await agent.voice.send(getMicrophoneStream())
// later
agent.voice.close()
```

- Realtime `speak()` and `listen()` return nothing. Output arrives as `speaker`/`speaking` and `writing` events.
- `connect()` must succeed before `send()` or `answer()`. It rejects on failure. An `error` listener does not replace `try/catch`.
- When the voice is attached to an agent, providers such as Nova Sonic add the agent's tools automatically. Otherwise call `voice.addTools({...})` and `voice.addInstructions('...')` before `connect()`.
- OpenAI Realtime `connect({ requestContext })` passes request context to tools.

---

## Failure patterns

- **`speak()` returns undefined.** The provider is realtime. Listen for `speaker` events instead.
- **`listen()` throws on a TTS-only provider.** ElevenLabs is documented both ways, and Murf, Speechify, Cloudflare, and ModelsLab are TTS only. Use `CompositeVoice` with an STT provider as `input`.
- **`speak()` throws on Gladia.** Gladia is STT only. Pair it with a TTS provider.
- **Azure auth fails.** The package uses Azure Speech Services keys, not Azure OpenAI keys. Use `AZURE_API_KEY` and `AZURE_REGION` per the integration page.
- **Realtime call hangs silently.** No `connect()`, or `connect()` rejected unhandled. Await it inside `try/catch`.
- **Distorted audio.** Sample rate or format mismatch with the player. Match the provider's output (for example PCM16 at 24 kHz on realtime providers).
- **Leaked sessions and bills.** No `close()`. Close realtime sessions on hang-up, error, and process exit.
- **`CompositeVoice` throws `VOICE_COMPOSITE_NO_REALTIME_PROVIDER_SEND`.** `send()` needs a `realtime` provider.
- **Listeners pile up.** Remove them with `voice.off(event, callback)` when a UI component unmounts.
- **Wrong option names.** Options are provider-specific. `speed` is OpenAI, `stability` is ElevenLabs, `properties` is Murf. Check the provider page.

---

## Output format

A finished voice delivery contains:

- The provider package(s) in `package.json` and env vars in `.env.example`
- The agent with `voice` set, or a standalone voice module
- The audio path wired: file or microphone in, player, file, or HTTP response out
- For realtime: listeners, `connect()` error handling, and `close()` on every exit path
- Evidence: a recorded transcript and an audio file produced by `speak()`, or a working call

---

## Reference files

- [`references/api.md`](references/api.md) - Voice interface methods, events, `CompositeVoice`, `MastraVoice` base config, agent integration.
- [`references/providers.md`](references/providers.md) - Every voice provider: package, class, modes, constructor shape, env vars, defaults.
- [`references/examples.md`](references/examples.md) - TTS reply, STT then agent then TTS, CompositeVoice with AI SDK models, realtime assistant with tools, LiveKit call.
- [`references/checklist.md`](references/checklist.md) - Voice checklist.

**Live docs**

- https://mastra.ai/reference/voice/overview
- https://mastra.ai/reference/voice/composite-voice
- https://mastra.ai/reference/voice/mastra-voice
- https://mastra.ai/reference/voice/voice.speak
- https://mastra.ai/reference/voice/voice.listen
- https://mastra.ai/reference/voice/voice.connect
- https://mastra.ai/reference/voice/voice.events
- https://mastra.ai/integrations/voice/openai
- https://mastra.ai/integrations/voice/livekit
