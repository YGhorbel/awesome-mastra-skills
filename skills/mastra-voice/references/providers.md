# Voice providers

One row per page under `https://mastra.ai/integrations/voice/`. Defaults and env vars come from those pages. Install the package, set the env var, and confirm the constructor on the provider page before use.

## Contents

- Summary table
- Constructor shapes
- Realtime providers
- LiveKit
- Known docs inconsistencies

---

## Summary table

| Provider | Package | Class | TTS | STT | Realtime | Env vars |
|---|---|---|---|---|---|---|
| OpenAI | `@mastra/voice-openai` | `OpenAIVoice` | yes | yes | no | `OPENAI_API_KEY` |
| OpenAI Realtime | `@mastra/voice-openai-realtime` | `OpenAIRealtimeVoice` | events | events | yes | `OPENAI_API_KEY` |
| Azure | `@mastra/voice-azure` | `AzureVoice` | yes | yes | no | `AZURE_API_KEY`, `AZURE_REGION` (Speech Services, not Azure OpenAI) |
| Google | `@mastra/voice-google` | `GoogleVoice` | yes | yes | no | `GOOGLE_API_KEY`, or `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` for Vertex AI |
| Gemini Live | `@mastra/voice-google-gemini-live` | `GeminiLiveVoice` | events | events | yes | `GOOGLE_API_KEY` (or Vertex AI service account) |
| ElevenLabs | `@mastra/voice-elevenlabs` | `ElevenLabsVoice` | yes | see note | no | `ELEVENLABS_API_KEY` |
| Deepgram | `@mastra/voice-deepgram` | `DeepgramVoice` | yes | yes | no | `DEEPGRAM_API_KEY` |
| Cloudflare | `@mastra/voice-cloudflare` | `CloudflareVoice` | yes | no | no | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| Murf | `@mastra/voice-murf` | `MurfVoice` | yes | no | no | `MURF_API_KEY` |
| Speechify | `@mastra/voice-speechify` | `SpeechifyVoice` | yes | no | no | `SPEECHIFY_API_KEY` |
| Sarvam | `@mastra/voice-sarvam` | `SarvamVoice` | yes | yes | no | `SARVAM_API_KEY` |
| Mistral | `@mastra/voice-mistral` | `MistralVoice` | yes | yes | no | `MISTRAL_API_KEY` |
| Inworld | `@mastra/voice-inworld` | `InworldVoice` | yes (streaming) | yes (batch) | no | `INWORLD_API_KEY` |
| Inworld Realtime | `@mastra/voice-inworld` | `InworldRealtimeVoice` | events | events | yes | `INWORLD_API_KEY` (pre-Basic-encoded, paste verbatim) |
| Gladia | `@mastra/voice-gladia` | `GladiaVoice` | no (throws) | yes (prerecorded) | no | `GLADIA_API_KEY` |
| ModelsLab | `@mastra/voice-modelslab` | `ModelsLabVoice` | yes (async job) | no | no | `MODELSLAB_API_KEY` |
| xAI Realtime | `@mastra/voice-xai-realtime` | `XAIRealtimeVoice` | events | events | yes | `XAI_API_KEY` (or `ephemeralToken`) |
| AWS Nova Sonic | `@mastra/voice-aws-nova-sonic` | `NovaSonicVoice` | events | events | yes | AWS credential chain (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) |
| LiveKit | `@mastra/livekit` | worker and route helpers | via LiveKit | via LiveKit | yes (calls) | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` |

"events" means `speak()`/`listen()` return nothing and results arrive as `speaker`, `speaking`, and `writing` events.

---

## Constructor shapes

Most TTS and STT providers use the shared `{ speechModel, listeningModel, speaker }` shape. Every field is optional when the env var is set.

| Class | Shape and defaults |
|---|---|
| `OpenAIVoice` | `speechModel: { name: 'tts-1' \| 'tts-1-hd', apiKey }` (default `tts-1`), `listeningModel: { name: 'whisper-1', apiKey }`, `speaker` (default `'alloy'`) |
| `AzureVoice` | `speechModel: { apiKey, region, voiceName }`, `listeningModel: { apiKey, region, language }`, `speaker` (for example `'en-US-JennyNeural'`). WAV in and out. |
| `GoogleVoice` | `speechModel` and `listeningModel`: `{ apiKey, keyFilename, credentials }`, `speaker` (default `'en-US-Casual-K'`), `vertexAI` (default `false`), `project`, `location` (default `'us-central1'`) |
| `ElevenLabsVoice` | `speechModel: { name, apiKey }` (default `eleven_multilingual_v2`), `speaker` (default Aria, `'9BWtsMINqrJLrRacOk9x'`) |
| `DeepgramVoice` | `speechModel: { name, apiKey, properties, language }` (default `aura`), `listeningModel` (default `nova`), `speaker` (default `'asteria-en'`) |
| `CloudflareVoice` | `speechModel: { name, apiKey, accountId }`, `speaker` (default `'en-US-1'`) |
| `MurfVoice` | `speechModel: { name: 'GEN1' \| 'GEN2', apiKey, properties: { style, rate, pitch, sampleRate, format, channelType, ... } }` (default `GEN2`), `speaker` (default `'en-UK-hazel'`) |
| `SpeechifyVoice` | `speechModel: { name, apiKey }` (default `simba-3.5`), `speaker` (default `'harper_32'` on Simba 3 models) |
| `SarvamVoice` | `speechModel: { model, apiKey, language, properties }` (default `bulbul:v3`, `en-IN`), `listeningModel: { model, apiKey, languageCode, filetype, mode }` (default `saarika:v2.5`), `speaker` (default `'shubh'`). Note `model`, not `name`. |
| `MistralVoice` | `speechModel: { name, apiKey }` (default `voxtral-mini-tts-2603`), `listeningModel` (default `voxtral-mini-latest`), `speaker` (default `'en_paul_neutral'`) |
| `InworldVoice` | `speechModel: { name, apiKey }` (default `inworld-tts-2`), `listeningModel` (default `groq/whisper-large-v3`), `speaker` (default `'Dennis'`), `audioEncoding` (default `'MP3'`), `sampleRateHertz` (default `48000`), `language` (default `'en-US'`) |
| `GladiaVoice` | `listeningModel: { apiKey }`. Throws at construction without a key. `listen(audio, { fileName, mimeType, options })`. |
| `ModelsLabVoice` | `speechModel: { name: 'default', apiKey }`, `speaker` (default `'1'`, OpenAI-style aliases accepted) |

---

## Realtime providers

| Class | Constructor (top-level options) | Defaults |
|---|---|---|
| `OpenAIRealtimeVoice` | `apiKey`, `model`, `speaker`, `connectTimeoutMs`. VAD via `updateSession({ turn_detection })`. | model `'gpt-5.1-realtime-preview-2024-12-17'`, speaker `'alloy'`, timeout 15000 ms |
| `GeminiLiveVoice` | `apiKey`, `model`, `speaker`, `vertexAI`, `project`, `location`, `serviceAccountKeyFile`, `serviceAccountEmail`, `instructions`, `sessionConfig`, `inputAudioTranscription`, `outputAudioTranscription`, `debug`. Also accepts `speechModel` and `realtimeConfig`. | model `'gemini-2.0-flash-exp'`, speaker `'Puck'` |
| `XAIRealtimeVoice` | `apiKey`, `ephemeralToken`, `model`, `speaker`, `instructions`, `turnDetection`, `audio`, `serverTools`, `session`, `url`, `debug`. Also accepts `realtimeConfig`. | model `'grok-voice-think-fast-1.0'`, speaker `'eve'`, server VAD, 24 kHz PCM |
| `NovaSonicVoice` | `region`, `model`, `credentials`, `speaker`, `languageCode`, `instructions`, `tools`, `sessionConfig`, `debug` | region `'us-east-1'`, model `'amazon.nova-2-sonic-v1:0'`, speaker `'matthew'` |
| `InworldRealtimeVoice` | `apiKey`, `url`, `model`, `speaker`, `sessionId`, `instructions`, `session`, `providerData`, `debug`, `connectTimeoutMs` | model `'inworld/models/gemma-4-26b-a4b-it'`, speaker `'Sarah'`, PCM16 24 kHz |

All call `connect()` first and `close()` at the end.

---

## LiveKit

`@mastra/livekit` hands the audio loop (VAD, streaming STT, semantic turn detection, barge-in, TTS) to LiveKit. Your agent generates each reply with its own model, tools, and memory.

Install: `@mastra/livekit @livekit/agents @livekit/agents-plugin-silero @livekit/agents-plugin-livekit`. Download models once with `npx livekit-agents download-files`.

| Piece | Import | Purpose |
|---|---|---|
| `liveKitConnectionRoute({ agentName })` | `@mastra/livekit` | Adds `POST /voice/livekit/connection-details`. Body: optional `agentId`, `threadId`, `resourceId`. Returns `{ serverUrl, roomName, participantName, participantToken }`. Defaults: `requiresAuth: true`, `ttl: '15m'`, credentials from env. |
| `createLiveKitWorker({ mastra, agent, stt, tts, turnDetection, ... })` | `@mastra/livekit/worker` | Worker definition. `stt`/`tts` accept LiveKit plugin instances or inference strings such as `'deepgram/nova-3'` and `'cartesia/sonic-3'`. `vad` default `'silero'`. Also `workflow`, `memory`, `toolFeedback`, `onTurnComplete`, `configuration` (greeting, consent, endCall, per-call stt/tts/turnDetection), `observability`. |
| `runLiveKitWorker({ entry: import.meta.url, agentName })` | `@mastra/livekit/worker` | Starts the worker CLI (`dev`, `start`, `connect`). `agentName` must match the route. |
| `dispatchVoiceSession()` | `@mastra/livekit` | Server-initiated sessions. |

With agent memory, each call is one thread: `thread` defaults to the dispatch `threadId` or room name, `resource` to the dispatch `resourceId` or the thread. Run the worker as a separate process from the Mastra server.

---

## Known docs inconsistencies

Check the installed package when these matter:

- `OpenAIRealtimeVoice`: the integration page uses top-level `apiKey`, `model`, `speaker`, while several method reference pages pass `realtimeConfig: { model, apiKey }`.
- Azure env vars: the integration page says `AZURE_API_KEY` and `AZURE_REGION`. The voice overview example reads `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` explicitly.
- ElevenLabs STT: the page documents a `listen()` method and calls the provider TTS and STT, but its notes say speech-to-text isn't supported.
- PlayAI: `CompositeVoice` examples import `@mastra/voice-playai`, which has no integration page. Prefer a listed provider.
