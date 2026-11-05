# Browser examples

All examples follow the current docs at `https://mastra.ai/docs/browser` and `https://mastra.ai/integrations/browsers/*`. Verify options against the installed provider.

## Contents

1. Local AgentBrowser agent with per-thread isolation
2. Stagehand on Browserbase for adaptive extraction
3. Firecrawl hosted sessions with a persistent profile
4. BrowserViewer driving the browser-use CLI from a sandbox

---

## 1. Local AgentBrowser agent with per-thread isolation

```bash
npm install @mastra/agent-browser @mastra/memory @mastra/libsql
npm install ws @hono/node-ws   # Studio screencast (skip on serverless)
```

```typescript
// src/mastra/browsers/index.ts
import { join } from 'node:path'
import { AgentBrowser } from '@mastra/agent-browser'

export const browser = new AgentBrowser({
  headless: false,
  scope: 'thread',
  recording: {
    outputDir: join(process.cwd(), 'browser-recordings'),
  },
})
```

```typescript
// src/mastra/agents/web-agent.ts
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { browser } from '../browsers'

export const webAgent = new Agent({
  id: 'web-agent',
  name: 'Web Agent',
  description: 'A web automation assistant that can navigate websites and complete tasks.',
  model: 'openai/gpt-6.1-sol',
  browser,
  memory: new Memory(),
  instructions: `You are a web automation assistant.
When interacting with pages:
1. Use browser_snapshot to get the current page state and element refs
2. Use the refs (like @e1, @e2) to target elements for clicks and typing
3. After actions, take another snapshot to verify the result`,
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { webAgent } from './agents/web-agent'

export const mastra = new Mastra({
  agents: { webAgent },
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
})
```

If launch fails with `browser executable is missing`, run `npx playwright install chromium`. For a non-vision model add `excludeTools: ['browser_screenshot']`.

---

## 2. Stagehand on Browserbase for adaptive extraction

```bash
npm install @mastra/stagehand
```

```typescript
import { Agent } from '@mastra/core/agent'
import { StagehandBrowser } from '@mastra/stagehand'

const browser = new StagehandBrowser({
  env: 'BROWSERBASE',
  apiKey: process.env.BROWSERBASE_API_KEY,
  projectId: process.env.BROWSERBASE_PROJECT_ID,
  model: 'openai/gpt-6.1-sol',
})

export const stagehandAgent = new Agent({
  id: 'stagehand-agent',
  name: 'Stagehand Agent',
  model: 'openai/gpt-6.1-sol',
  browser,
  instructions: `You are a web automation assistant.
Use stagehand tools to interact with pages:
- stagehand_navigate to go to URLs
- stagehand_act to perform actions described in natural language
- stagehand_extract to get structured data from the page
- stagehand_observe to find available actions on the page
- stagehand_screenshot to visually inspect the page`,
})
```

`.env`: `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID`, `OPENAI_API_KEY` (used by both the agent and Stagehand's own actions).

Use `variables` in `stagehand_act` (`"type %email% into the email field"`) so values are substituted instead of written into the instruction.

---

## 3. Firecrawl hosted sessions with a persistent profile

```bash
npm install @mastra/browser-firecrawl
```

```typescript
import { Agent } from '@mastra/core/agent'
import { FirecrawlBrowser } from '@mastra/browser-firecrawl'

const browser = new FirecrawlBrowser({
  apiKey: process.env.FIRECRAWL_API_KEY,
  firecrawl: {
    ttl: 600,
    activityTtl: 120,
    profile: {
      name: 'my-profile',
      saveChanges: true,
    },
  },
})

export const firecrawlAgent = new Agent({
  id: 'firecrawl-agent',
  name: 'Firecrawl Agent',
  model: 'openai/gpt-6.1-sol',
  browser,
  instructions: `You are a web automation assistant.
When interacting with pages:
1. Use browser_snapshot to get the current page state and element refs
2. Use the refs (like @e1, @e2) to target elements for clicks and typing
3. After actions, take another snapshot to verify the result`,
})
```

`.env`: `FIRECRAWL_API_KEY=fc-...`. Each thread gets its own Firecrawl session (default `'thread'` scope), deleted when that thread's browser closes.

Sign the browser in from app code instead of the prompt:

```typescript
await browser.setCookies(
  [{ name: 'my_app_session', value: sessionToken, domain: 'app.example.com', path: '/', httpOnly: true, secure: true }],
  threadId,
)
```

---

## 4. BrowserViewer driving the browser-use CLI from a sandbox

```bash
npm install @mastra/browser-viewer
pip install browser-use
npx skills add browser-use/browser-use --skill browser-use
```

```typescript
import { Mastra } from '@mastra/core/mastra'
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { LibSQLStore } from '@mastra/libsql'
import { Workspace, LocalSandbox } from '@mastra/core/workspace'
import { BrowserViewer } from '@mastra/browser-viewer'

const workspace = new Workspace({
  sandbox: new LocalSandbox({
    workingDirectory: './workspace',
  }),
  browser: new BrowserViewer({
    cli: 'browser-use',
    headless: false,
  }),
})

const browserAgent = new Agent({
  id: 'browser-agent',
  name: 'Browser Agent',
  model: 'openai/gpt-6.1-sol',
  workspace,
  instructions: `You are a web automation assistant.
Use browser-use commands to navigate and interact with websites.`,
  memory: new Memory(),
})

export const mastra = new Mastra({
  agents: { browserAgent },
  storage: new LibSQLStore({
    id: 'mastra-storage',
    url: 'file:./mastra.db',
  }),
})
```

When the agent runs a `browser-use` command through the sandbox, Mastra launches Chrome, injects the CDP connection, and streams the screencast to Studio. The installed skill teaches the agent the CLI. Use an absolute `workingDirectory` outside development (see `mastra-workspace-sandbox`).
