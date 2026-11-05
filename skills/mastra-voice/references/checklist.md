# Voice checklist

Run this before calling a voice feature done.

## Provider choice

- [ ] The provider supports the needed mode (TTS, STT, or realtime); TTS-only and STT-only providers are paired with `CompositeVoice`
- [ ] Package installed (`@mastra/voice-<provider>`, or `@mastra/livekit` for calls)
- [ ] Env vars listed in `.env.example` with the exact names the provider reads
- [ ] Azure uses a Speech Services key, not an Azure OpenAI key
- [ ] Default `speaker` and language chosen and tested

## Audio handling

- [ ] Input format matches what the provider accepts (for example WAV for Azure, `filetype` set for OpenAI)
- [ ] Output format and sample rate match the player or the HTTP response content type
- [ ] Returned audio streams are consumed or ended so resources are freed
- [ ] Node playback and capture use `@mastra/node-audio` (`playAudio`, `getMicrophoneStream`)

## Realtime sessions

- [ ] `on('speaker')`, `on('writing')`, and `on('error')` registered before speaking
- [ ] `await voice.connect()` wrapped in `try/catch`, with `connectTimeoutMs` set where supported
- [ ] Instructions and tools added before `connect()`
- [ ] `close()` called on hang-up, error, and process exit
- [ ] Listeners removed with `off()` when a session or component ends
- [ ] Turn detection (VAD) tuned for the environment

## Agent integration

- [ ] Agent `voice` set, or a function of `requestContext` for per-tenant voices
- [ ] Agent instructions written for speech (short sentences, no Markdown tables or code)
- [ ] Tools the realtime model calls are safe to run without a confirmation step, or gated (see `mastra-agent-approval-hitl`)

## LiveKit calls

- [ ] `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` set for both server and worker
- [ ] Route and worker use the same `agentName`
- [ ] Worker runs as its own long-lived process
- [ ] Connection route stays behind auth (`requiresAuth` default `true`)
- [ ] Memory `resourceId` is the end user's id so calls group per user
- [ ] Recording and consent requirements reviewed before enabling recording

## Verification

- [ ] A known audio file transcribes correctly
- [ ] A fixed phrase synthesizes and plays at the right speed and voice
- [ ] End-to-end latency measured for a typical turn
