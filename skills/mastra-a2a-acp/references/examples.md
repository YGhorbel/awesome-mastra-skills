# A2A, ACP, and SDK agent examples

All examples follow the current docs at `https://mastra.ai/docs/connections/*` and `https://mastra.ai/reference/acp/*`. Verify against installed packages before copying.

## Contents

1. Remote A2A subagent with card verification and human input
2. Calling a Mastra agent's A2A endpoint from another service
3. ACP coding subagent with an explicit permission policy
4. SDK agents with their own tools, registered in Mastra

---

## 1. Remote A2A subagent with card verification and human input

```typescript
// src/mastra/agents/support-agent.ts
import { Agent } from '@mastra/core/agent'
import { A2AAgent } from '@mastra/core/a2a'

const remoteWeatherAgent = new A2AAgent({
  url: 'https://weather.example.com/api/.well-known/weather-agent/agent-card.json',
  protocolVersion: '1.0',
  headers: {
    Authorization: `Bearer ${process.env.WEATHER_AGENT_TOKEN}`,
  },
  retries: 2,
  backoffMs: 250,
  maxBackoffMs: 1000,
  timeoutMs: 30_000,
  verifyAgentCard: {
    verify: async (card, context) => {
      if (card.provider?.organization !== 'Weather Inc') {
        throw new Error(`Unexpected provider for ${context.cardUrl}`)
      }
    },
  },
})

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  instructions: 'Answer user questions and delegate weather questions when needed.',
  model: 'openai/gpt-6.1-sol',
  agents: { remoteWeatherAgent },
})
```

Calling a remote agent directly and resuming when it pauses for input:

```typescript
import { A2AAgent } from '@mastra/core/a2a'

const agent = new A2AAgent({
  url: 'https://agent.example.com/api/.well-known/booking-agent/agent-card.json',
})

const result = await agent.generate('Book a flight to Paris', { runId: 'run-1' })

if (result.finishReason === 'suspended') {
  // Show result.suspendPayload to a human, collect the answer, then resume
  const resumed = await agent.resumeGenerate({ approved: true }, { runId: 'run-1' })
  console.log(resumed.text)
}
```

The remote server keeps task records in memory: the resume must reach the same process.

---

## 2. Calling a Mastra agent's A2A endpoint from another service

Server side, any registered agent is exposed. Add storage so suspended runs can resume, and optionally sign the card:

```typescript
import { Mastra } from '@mastra/core/mastra'
import { LibSQLStore } from '@mastra/libsql'
import { weatherAgent } from './agents/weather-agent'

export const mastra = new Mastra({
  agents: { weatherAgent },
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
  server: {
    a2a: {
      agentCardSigning: {
        privateKey: process.env.A2A_AGENT_CARD_PRIVATE_KEY!,
        protectedHeader: { alg: 'ES256', kid: 'agent-card-key' },
      },
    },
  },
})
```

Client side:

```typescript
import { MastraClient } from '@mastra/client-js'

const client = new MastraClient({
  baseUrl: 'https://agent.example.com',
  headers: { Authorization: `Bearer ${process.env.AGENT_API_TOKEN}` },
})

const a2a = client.getA2A('weather-agent')

const card = await a2a.getAgentCard({
  verifySignature: {
    algorithms: ['ES256'],
    keyProvider: async ({ kid, jku }) => fetchTrustedPublicJwk({ kid, jku }),
  },
})
if (!card.signatures?.length) throw new Error('Expected a signed A2A agent card.')

const stream = a2a.sendMessageStream({
  message: {
    kind: 'message',
    role: 'user',
    messageId: crypto.randomUUID(),
    parts: [{ kind: 'text', text: "What's the weather in Prague?" }],
  },
})

for await (const event of stream) {
  if (event.kind === 'artifact-update') console.log(event.artifact.parts)
}
```

`fetchTrustedPublicJwk` is your own key lookup. If the stream drops, call `a2a.resubscribeTask({ id: taskId })`.

---

## 3. ACP coding subagent with an explicit permission policy

```bash
npm install @mastra/acp
```

```typescript
// src/mastra/agents/code-supervisor.ts
import { AcpAgent } from '@mastra/acp'
import { Agent } from '@mastra/core/agent'
import { LocalFilesystem, Workspace } from '@mastra/core/workspace'

const repoPath = process.env.REPO_PATH!

const codeAgent = new AcpAgent({
  id: 'claude-code-agent',
  name: 'Claude Code Agent',
  description: 'Use Claude Code through ACP to inspect and edit the repository.',
  command: 'npx',
  args: ['@agentclientprotocol/claude-agent-acp'],
  cwd: repoPath,
  model: 'claude-sonnet-5-5',
  workspace: new Workspace({
    filesystem: new LocalFilesystem({ basePath: repoPath }),
  }),
  async onPermissionRequest(request) {
    const allowOption = request.options.find(option => option.name === 'Allow')
    if (!allowOption) {
      return { outcome: { outcome: 'cancelled' } }
    }
    return { outcome: { outcome: 'selected', optionId: allowOption.optionId } }
  },
})

export const codeSupervisor = new Agent({
  id: 'code-supervisor',
  name: 'Code Supervisor',
  instructions: 'Delegate code editing tasks to the claude-code-agent subagent. Summarize the changes it reports.',
  model: 'openai/gpt-6.1-sol',
  agents: { codeAgent },
})
```

The workspace governs only file requests made through ACP. The process itself is not sandboxed, so point `cwd` at a disposable checkout or run inside a container for untrusted work.

To let the parent decide when to call it instead, use a tool:

```typescript
import { createACPTool } from '@mastra/acp'

export const codeAgentTool = createACPTool({
  id: 'code-agent',
  description: 'Use an ACP-compatible coding agent to inspect and edit code',
  command: 'opencode',
  args: ['acp'],
  cwd: process.cwd(),
  persistSession: false,
})
```

---

## 4. SDK agents with their own tools, registered in Mastra

```bash
npm install @mastra/claude @anthropic-ai/claude-agent-sdk zod
npm install @mastra/openai @openai/agents
```

```typescript
// src/mastra/agents/claude-sdk-agent.ts
import { createSdkMcpServer, tool } from '@anthropic-ai/claude-agent-sdk'
import { ClaudeSDKAgent } from '@mastra/claude'
import { z } from 'zod'

const getTemperature = tool(
  'get_temperature',
  'Get the temperature for a city using sample data.',
  { city: z.string() }, // raw Zod shape, not z.object()
  async ({ city }) => ({ content: [{ type: 'text', text: `${city}: 27 C` }] }),
)

const weatherServer = createSdkMcpServer({ name: 'weather', version: '1.0.0', tools: [getTemperature] })

export const claudeSDKAgent = new ClaudeSDKAgent({
  id: 'claude-sdk-agent',
  name: 'Claude SDK Agent',
  description: 'Use Claude Agent SDK through Mastra.',
  sdkOptions: {
    model: 'claude-sonnet-5-5',
    cwd: process.cwd(),
    mcpServers: { weather: weatherServer },
    allowedTools: ['mcp__weather__get_temperature'],
  },
})
```

```typescript
// src/mastra/agents/openai-sdk-agent.ts
import { tool } from '@openai/agents'
import { OpenAISDKAgent } from '@mastra/openai'
import { z } from 'zod'

const getTemperature = tool({
  name: 'get_temperature',
  description: 'Get the current temperature for a city.',
  parameters: z.object({ city: z.string() }),
  execute: async ({ city }) => `${city}: 27 C`,
})

export const openaiSDKAgent = new OpenAISDKAgent({
  id: 'openai-sdk-agent',
  name: 'OpenAI SDK Agent',
  description: 'Use OpenAI Agents SDK through Mastra.',
  sdkOptions: { name: 'Weather assistant', model: 'gpt-5.6', tools: [getTemperature] },
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { claudeSDKAgent } from './agents/claude-sdk-agent'
import { openaiSDKAgent } from './agents/openai-sdk-agent'

export const mastra = new Mastra({ agents: { claudeSDKAgent, openaiSDKAgent } })

const stream = await mastra.getAgentById('openai-sdk-agent').stream('How warm is Lisbon?')
for await (const chunk of stream.textStream) process.stdout.write(chunk)
```

`.env`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. Model IDs inside `sdkOptions` use the vendor SDK format, not Mastra router strings.
