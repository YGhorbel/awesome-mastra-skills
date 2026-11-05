# Project setup examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models`. Verify before copying into a project on an older version.

## Contents

1. Manual install, end to end
2. Production-leaning `src/mastra/index.ts`
3. Starting from a template
4. Empty scaffold, then a first agent with the Mastra Gateway

---

## 1. Manual install, end to end

```bash
mkdir my-first-agent && cd my-first-agent
npm init -y
npm install -D typescript @types/node mastra@latest
npm install @mastra/core@latest zod@^4
```

`package.json` (relevant fields):

```json
{
  "type": "module",
  "scripts": {
    "dev": "mastra dev",
    "build": "mastra build"
  }
}
```

`tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true,
    "types": ["node"],
    "noEmit": true,
    "outDir": "dist"
  },
  "include": ["src/**/*"]
}
```

`.env`:

```bash
GOOGLE_API_KEY=<your-api-key>
```

```typescript
// src/mastra/tools/weather-tool.ts
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const weatherTool = createTool({
  id: 'get-weather',
  description: 'Get current weather for a location',
  inputSchema: z.object({
    location: z.string().describe('City name'),
  }),
  outputSchema: z.object({
    output: z.string(),
  }),
  execute: async ({ location }) => {
    return { output: `The weather in ${location} is sunny` }
  },
})
```

```typescript
// src/mastra/agents/weather-agent.ts
import { Agent } from '@mastra/core/agent'
import { weatherTool } from '../tools/weather-tool.ts'

export const weatherAgent = new Agent({
  id: 'weather-agent',
  name: 'Weather Agent',
  instructions: `
    You are a helpful weather assistant.
    Always ask for a location if none is provided.
    Use the weatherTool to fetch current weather data.`,
  model: 'google/gemini-3.8-flash',
  tools: { weatherTool },
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { weatherAgent } from './agents/weather-agent.ts'

export const mastra = new Mastra({
  agents: { weatherAgent },
})
```

Run Studio with `npm run dev` and open `http://localhost:4111`. Or check it from a script without Studio:

```typescript
// scripts/check.ts
import { mastra } from '../src/mastra/index.ts'

const agent = mastra.getAgentById('weather-agent')
const response = await agent.generate('Weather in SF')
console.log(response.text)
```

Validate with `npx tsc --noEmit`.

---

## 2. Production-leaning `src/mastra/index.ts`

Persistent storage, a structured logger, explicit server settings, and source maps.

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { PinoLogger } from '@mastra/loggers'
import { weatherAgent } from './agents/weather-agent'
import { weatherWorkflow } from './workflows/weather-workflow'

export const mastra = new Mastra({
  agents: { weatherAgent },
  workflows: { weatherWorkflow },
  storage: new LibSQLStore({
    id: 'mastra-storage',
    url: 'file:./mastra.db',
  }),
  logger: new PinoLogger({ name: 'Mastra', level: 'info' }),
  server: {
    host: '0.0.0.0',
    timeout: 30000,
    cors: {
      origin: ['https://example.com'],
      allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowHeaders: ['Content-Type', 'Authorization'],
      credentials: false,
    },
  },
  bundler: {
    sourcemap: true,
  },
})
```

Install the extra packages: `npm install @mastra/libsql @mastra/loggers`. Add `mastra.db` and `.mastra/` to `.gitignore`. For a hosted database, swap the store (see `mastra-storage`).

---

## 3. Starting from a template

```bash
npx create-mastra@latest my-project --template template-docs-expert
cd my-project
cp .env.example .env   # fill in the keys the template README lists
npm run dev
```

Pass a GitHub URL instead of a slug for community templates:

```bash
npx create-mastra@latest my-project --template https://github.com/mastra-ai/template-agent-harness
```

Every template uses the same layout: `src/mastra/{agents,tools,workflows}/` plus `index.ts`, `.env.example`, `package.json`, `tsconfig.json`, and `README.md`.

---

## 4. Empty scaffold, then a first agent with the Mastra Gateway

```bash
npx create-mastra@latest my-empty-project --empty --no-git
cd my-empty-project
```

`.env`:

```bash
MASTRA_GATEWAY_API_KEY=<your-gateway-key>
```

```typescript
// src/mastra/agents/assistant.ts
import { Agent } from '@mastra/core/agent'

export const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'You are a concise assistant.',
  model: 'mastra/openai/gpt-6.1-sol',
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { assistant } from './agents/assistant'

export const mastra = new Mastra({ agents: { assistant } })
```

Start with `npx mastra dev` and chat with `assistant` in Studio. To call it from a coding agent instead: `npx mastra api --url http://localhost:4111 agent run assistant '{"messages":"Hello"}'`.
