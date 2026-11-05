# Tool integrations examples

All examples follow the current docs. Model IDs are the ones the docs use. Verify against the installed version before copying.

## Contents

1. Research agent with Bright Data search and fetch
2. Firecrawl tools built with createTool
3. Parallel tools on an agent
4. Connect tools filtered by role
5. Connect tools combined with your own tools
6. Multiple Slack workspaces and a pinned connection
7. Connect channels and a raw credential

---

## 1. Research agent with Bright Data search and fetch

```typescript
// src/mastra/agents/research-agent.ts
import { Agent } from '@mastra/core/agent'
import { createBrightDataTools } from '@mastra/brightdata'

const { webSearch, webFetch } = createBrightDataTools() // reads BRIGHTDATA_API_TOKEN

export const researchAgent = new Agent({
  id: 'research-agent',
  name: 'Research Agent',
  model: 'anthropic/claude-sonnet-5-5',
  instructions:
    'You are a research assistant. Use the search tool to find relevant pages, then use the fetch tool to read full Markdown content from the best results.',
  tools: { webSearch, webFetch },
})
```

`.env.example`: `BRIGHTDATA_API_TOKEN=` and the model provider key.

---

## 2. Firecrawl tools built with createTool

```typescript
// src/mastra/tools/firecrawl.ts
import { Firecrawl } from 'firecrawl'
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

const firecrawl = new Firecrawl({ apiKey: process.env.FIRECRAWL_API_KEY! })

export const firecrawlSearch = createTool({
  id: 'firecrawl-search',
  description: 'Search the web and return top results.',
  inputSchema: z.object({ query: z.string().min(1) }),
  outputSchema: z.object({
    results: z.array(z.object({ title: z.string().nullable(), url: z.string() })),
  }),
  execute: async ({ query }) => {
    const results = await firecrawl.search(query, { limit: 3 })
    return {
      results: (results.web ?? []).map(item => ({ title: item.title ?? null, url: item.url })),
    }
  },
})

export const firecrawlScrape = createTool({
  id: 'firecrawl-scrape',
  description: 'Scrape a URL and return markdown content.',
  inputSchema: z.object({ url: z.string().url() }),
  outputSchema: z.object({ markdown: z.string() }),
  execute: async ({ url }) => {
    const result = await firecrawl.scrape(url, { formats: ['markdown'], onlyMainContent: true })
    return { markdown: result.markdown ?? '' }
  },
})
```

```typescript
// src/mastra/agents/web-agent.ts
import { Agent } from '@mastra/core/agent'
import { firecrawlSearch, firecrawlScrape } from '../tools/firecrawl'

export const webAgent = new Agent({
  id: 'web-agent',
  name: 'Web Agent',
  instructions: 'Use Firecrawl tools to search and scrape web pages, then summarize the results.',
  model: 'openai/gpt-6.1-sol',
  tools: { firecrawlSearch, firecrawlScrape },
})
```

Register `webAgent` on `new Mastra({ agents: { webAgent } })` and test it in Studio.

---

## 3. Parallel tools on an agent

```typescript
import { Agent } from '@mastra/core/agent'
import { createParallelTools } from '@mastra/parallel'

export const researchAgent = new Agent({
  id: 'research-agent',
  name: 'Research Agent',
  model: 'anthropic/claude-sonnet-5-5',
  instructions: 'Search the web for current sources, then extract relevant content from the best pages.',
  tools: createParallelTools(), // { parallelSearch, parallelExtract }, reads PARALLEL_API_KEY
})
```

---

## 4. Connect tools filtered by role

Setup once:

```bash
npm install @mastra/connect
mastra auth login
mastra auth tokens create my-app   # save as MASTRA_PLATFORM_ACCESS_TOKEN
mastra connect add linear
```

```typescript
// src/mastra/agents/ops-agent.ts
import { Agent } from '@mastra/core/agent'
import { tools } from '@mastra/connect'

export const opsAgent = new Agent({
  id: 'ops',
  name: 'ops',
  instructions: 'You help the team track work in Linear.',
  model: 'openai/gpt-6-luna',
  tools: tools(ctx => ({
    providers: {
      linear:
        ctx?.requestContext?.get('role') === 'viewer'
          ? { allowTools: ['linear_list_*'] }
          : { requireApproval: ['linear_delete_*'] },
    },
  })),
})
```

Set `role` in trusted server middleware from the authenticated user, never from client input. Handle approval prompts with `mastra-agent-approval-hitl`.

---

## 5. Connect tools combined with your own tools

```typescript
import { Agent } from '@mastra/core/agent'
import { tools } from '@mastra/connect'
import { weatherTool } from '../tools/weather'

const connectTools = tools({ providers: ['linear', 'github'] })

export const opsAgent = new Agent({
  id: 'ops',
  name: 'ops',
  instructions: 'You help the team track work in Linear and GitHub. Use weatherTool for weather questions.',
  model: 'openai/gpt-6-luna',
  tools: async ctx => ({ ...(await connectTools(ctx)), weatherTool }), // your tools win on key collision
})
```

Or pass a plain tool record for one call:

```typescript
import { tools } from '@mastra/connect'

const connected = tools()
const response = await agent.generate('Summarize my open issues.', {
  toolsets: { connect: await connected() },
})
```

---

## 6. Multiple Slack workspaces and a pinned connection

With two active Slack connections, the agent gets `slack__list_connections` and every Slack tool requires `connection_name`. Name connections clearly when adding them. To always use one workspace:

```typescript
import { tools } from '@mastra/connect'

const slackTools = tools({
  providers: {
    slack: { connectionId: 'c_yourconnectionid' },
  },
})
```

---

## 7. Connect channels and a raw credential

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { channels } from '@mastra/connect'
import { assistant } from './agents/assistant'

export const mastra = new Mastra({
  agents: { assistant },
  channels: await channels({ providers: ['slack', 'discord'] }),
})
```

Then run `mastra connect add slack-channels` and `mastra connect add discord`, and link each channel to the agent in Studio. Off-platform, set `MASTRA_SERVER_URL` to the public URL.

When a toolset does not cover an API, fetch the credential and use the vendor SDK:

```typescript
import { credential } from '@mastra/connect'

const cred = await credential('c_yourconnectionid')

if (cred.type === 'oauth2') {
  startSdkSession(cred.accessToken)
} else if (cred.type === 'api_key') {
  startSdkSession(cred.apiKey)
} else if (cred.type === 'two_step') {
  startSdkSession(cred.token)
}
```

Raw credentials bypass the platform proxy, host limits, and audit records. Do not log them or put them in agent output. Re-fetch when `expiresAt` passes.
