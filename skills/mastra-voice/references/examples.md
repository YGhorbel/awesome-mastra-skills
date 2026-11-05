# Voice examples

All examples follow the current docs. Model IDs and voice names come from the provider pages. Verify before copying into a project on an older version.

## Contents

1. Spoken agent reply (TTS)
2. Transcribe, answer, speak (STT plus TTS with CompositeVoice)
3. AI SDK speech and transcription models
4. Realtime assistant with tools (OpenAI Realtime)
5. Phone and browser calls with LiveKit

---

## 1. Spoken agent reply (TTS)

```typescript
import { Agent } from '@mastra/core/agent'
import { OpenAIVoice } from '@mastra/voice-openai'
import { playAudio } from '@mastra/node-audio'

const voiceAgent = new Agent({
  id: 'voice-agent',
  name: 'Voice Agent',
  instructions: 'You are a voice assistant that can help users with their tasks.',
  model: 'openai/gpt-6.1-sol',
  voice: new OpenAIVoice({ speaker: 'alloy' }),
})

const { text } = await voiceAgent.generate('What color is the sky?')

const audioStream = await voiceAgent.voice.speak(text, {
  speaker: 'nova', // override the default voice
  speed: 1.2, // OpenAI-specific option
})

playAudio(audioStream)
```

To save instead of play, pipe the returned stream to a file:

```typescript
import { createWriteStream } from 'fs'

audioStream.pipe(createWriteStream('./reply.mp3'))
```

`.env`: `OPENAI_API_KEY=...`

---

## 2. Transcribe, answer, speak (STT plus TTS with CompositeVoice)

OpenAI listens, ElevenLabs speaks.

```typescript
import { Agent } from '@mastra/core/agent'
import { CompositeVoice } from '@mastra/core/voice'
import { OpenAIVoice } from '@mastra/voice-openai'
import { ElevenLabsVoice } from '@mastra/voice-elevenlabs'
import { playAudio, getMicrophoneStream } from '@mastra/node-audio'

const voice = new CompositeVoice({
  input: new OpenAIVoice({
    listeningModel: {
      name: 'whisper-1',
      apiKey: process.env.OPENAI_API_KEY,
    },
  }),
  output: new ElevenLabsVoice(),
})

const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'Answer in one or two short spoken sentences.',
  model: 'openai/gpt-6.1-sol',
  voice,
})

const transcript = await assistant.voice.listen(getMicrophoneStream())
console.log('User said:', transcript)

const { text } = await assistant.generate(transcript)

const responseAudio = await assistant.voice.speak(text)
playAudio(responseAudio)
```

`.env`: `OPENAI_API_KEY=...`, `ELEVENLABS_API_KEY=...`

Transcribe a file with an explicit format:

```typescript
import { createReadStream } from 'fs'

const transcript = await voice.listen(createReadStream('./audio.mp3'), { filetype: 'mp3' })
```

---

## 3. AI SDK speech and transcription models

`CompositeVoice` wraps AI SDK models automatically. Provider options pass through `providerOptions`.

```typescript
import { CompositeVoice } from '@mastra/core/voice'
import { openai } from '@ai-sdk/openai'
import { elevenlabs } from '@ai-sdk/elevenlabs'
import { playAudio, getMicrophoneStream } from '@mastra/node-audio'

const voice = new CompositeVoice({
  input: openai.transcription('whisper-1'),
  output: elevenlabs.speech('eleven_turbo_v2'),
})

const transcript = await voice.listen(getMicrophoneStream(), {
  providerOptions: {
    openai: { language: 'en' },
  },
})

const audio = await voice.speak(`You said: ${transcript}`, {
  speaker: 'Rachel',
  providerOptions: {
    elevenlabs: {
      stability: 0.5,
      similarity_boost: 0.75,
    },
  },
})

playAudio(audio)
```

Mix an AI SDK model with a Mastra provider:

```typescript
import { CompositeVoice } from '@mastra/core/voice'
import { ElevenLabsVoice } from '@mastra/voice-elevenlabs'
import { groq } from '@ai-sdk/groq'

const voice = new CompositeVoice({
  input: groq.transcription('whisper-large-v3'),
  output: new ElevenLabsVoice(),
})
```

---

## 4. Realtime assistant with tools (OpenAI Realtime)

```typescript
import { Agent } from '@mastra/core/agent'
import { createTool } from '@mastra/core/tools'
import { OpenAIRealtimeVoice } from '@mastra/voice-openai-realtime'
import { playAudio, getMicrophoneStream } from '@mastra/node-audio'
import { z } from 'zod'

const weatherTool = createTool({
  id: 'getWeather',
  description: 'Get the current weather for a location',
  inputSchema: z.object({
    location: z.string().describe('The city and state, e.g. San Francisco, CA'),
  }),
  outputSchema: z.object({ message: z.string() }),
  execute: async inputData => {
    return { message: `It is sunny in ${inputData.location}.` }
  },
})

const voice = new OpenAIRealtimeVoice({
  apiKey: process.env.OPENAI_API_KEY,
  speaker: 'alloy',
  connectTimeoutMs: 30_000,
})

const agent = new Agent({
  id: 'customer-support-agent',
  name: 'Customer Support Agent',
  instructions: 'You are a helpful customer support agent for a software company.',
  model: 'openai/gpt-6.1-sol',
  voice,
})

voice.addTools({ getWeather: weatherTool })
voice.addInstructions('Always introduce yourself and speak clearly and concisely.')

voice.on('speaker', ({ audio }) => playAudio(audio))
voice.on('writing', ({ text, role }) => console.log(`${role}: ${text}`))
voice.on('error', ({ message, code, details }) => console.error(`Error ${code}: ${message}`, details))

try {
  await agent.voice.connect()
} catch (error) {
  console.error('Could not connect to the realtime service:', error)
  process.exit(1)
}

voice.updateSession({
  turn_detection: { type: 'server_vad', threshold: 0.6, silence_duration_ms: 1200 },
})

await agent.voice.speak('How can I help you today?')
await agent.voice.send(getMicrophoneStream())

process.on('SIGINT', () => {
  agent.voice.close()
  process.exit(0)
})
```

Swap in another realtime provider by changing the class: `GeminiLiveVoice` (`@mastra/voice-google-gemini-live`), `XAIRealtimeVoice` (`@mastra/voice-xai-realtime`), `NovaSonicVoice` (`@mastra/voice-aws-nova-sonic`), or `InworldRealtimeVoice` (`@mastra/voice-inworld`). Check each page for its event payload shapes.

---

## 5. Phone and browser calls with LiveKit

```bash
npm install @mastra/livekit @livekit/agents @livekit/agents-plugin-silero @livekit/agents-plugin-livekit
```

`.env`:

```bash
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core/mastra'
import { Agent } from '@mastra/core/agent'
import { liveKitConnectionRoute } from '@mastra/livekit'

const supportAgent = new Agent({
  id: 'support',
  name: 'Support',
  instructions: 'You are a friendly phone support agent. Keep replies short and conversational.',
  model: 'openai/gpt-6-luna',
})

export const mastra = new Mastra({
  agents: { support: supportAgent },
  server: {
    apiRoutes: [liveKitConnectionRoute({ agentName: 'mastra-voice' })],
  },
})
```

```typescript
// src/mastra/voice-worker.ts
import { fileURLToPath } from 'node:url'
import { createLiveKitWorker, runLiveKitWorker } from '@mastra/livekit/worker'
import { mastra } from './index'

export default createLiveKitWorker({
  mastra,
  agent: 'support',
  stt: 'deepgram/nova-3',
  tts: 'cartesia/sonic-3',
  turnDetection: 'multilingual',
  greeting: 'Hi! How can I help you today?',
})

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runLiveKitWorker({ entry: import.meta.url, agentName: 'mastra-voice' })
}
```

```bash
npx livekit-agents download-files
npx tsx src/mastra/voice-worker.ts dev   # terminal 1
npm run dev                              # terminal 2
```

Connect with the LiveKit Agents Playground, or have your frontend call `POST /voice/livekit/connection-details` for `{ serverUrl, roomName, participantName, participantToken }`. `greeting` is deprecated in favor of `configuration.greeting.text` on newer versions; check the installed package.
