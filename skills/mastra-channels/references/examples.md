# Channels examples

All examples follow the current docs at `https://mastra.ai/docs/channels`, `https://mastra.ai/reference/agents/channels`, and the platform pages. Verify against the installed version.

## Contents

1. Slack agent end to end
2. Multi-platform support agent with handlers, approvals, and identity
3. Serverless deployment on Vercel
4. Provider-managed Telegram bot

---

## 1. Slack agent end to end

```bash
npm install @chat-adapter/slack @mastra/memory @mastra/libsql
```

```typescript
// src/mastra/agents/slack-agent.ts
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { createSlackAdapter } from '@chat-adapter/slack'

export const slackAgent = new Agent({
  id: 'slack-agent',
  name: 'Slack Agent',
  instructions: 'Help people plan tasks, answer questions, and coordinate work in Slack.',
  model: 'anthropic/claude-opus-5-5',
  memory: new Memory(),
  channels: {
    adapters: {
      slack: createSlackAdapter(),
    },
  },
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { slackAgent } from './agents/slack-agent'

export const mastra = new Mastra({
  agents: { slackAgent },
  storage: new LibSQLStore({ id: 'mastra-storage', url: process.env.DATABASE_URL }),
})
```

`.env`:

```bash
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_BOT_TOKEN=xoxb-your-bot-token
DATABASE_URL=file:./mastra.db
```

Steps:

1. Create the Slack app from the manifest in `https://mastra.ai/integrations/channels/slack` (scopes `app_mentions:read`, `channels:history`, `channels:read`, `chat:write`, `users:read`, `im:read`, `im:history`, `im:write`; events `app_mention`, `message.channels`, `message.im`; interactivity on). Install it to the workspace.
2. `npx mastra dev`, then `npx cloudflared tunnel --url http://localhost:4111`.
3. Set both Event Subscriptions and Interactivity request URLs to `https://<tunnel>/api/agents/slack-agent/channels/slack/webhook`. Reinstall if Slack asks.
4. DM the bot, or `/invite @your-bot-name` and mention it in a channel.

The webhook route is public and verified by `SLACK_SIGNING_SECRET`, even when Mastra server auth is enabled.

---

## 2. Multi-platform support agent with handlers, approvals, and identity

```bash
npm install @chat-adapter/slack @chat-adapter/discord
```

```typescript
import { promises as fs } from 'node:fs'
import { Agent } from '@mastra/core/agent'
import { createTool } from '@mastra/core/tools'
import type { ChannelContext } from '@mastra/core/channels'
import { Memory } from '@mastra/memory'
import { createDiscordAdapter } from '@chat-adapter/discord'
import { createSlackAdapter } from '@chat-adapter/slack'
import { z } from 'zod'

export const whoami = createTool({
  id: 'whoami',
  description: 'Return the platform identity of the current user',
  inputSchema: z.object({}),
  execute: async (_input, context) => {
    const channel = context?.requestContext?.get('channel') as ChannelContext | undefined
    return { platform: channel?.platform, userId: channel?.userId, isDM: channel?.isDM }
  },
})

export const deleteFile = createTool({
  id: 'delete-file',
  description: 'Delete a file from the system',
  inputSchema: z.object({ path: z.string().describe('Path to the file to delete') }),
  requireApproval: true,
  execute: async ({ path }) => {
    await fs.unlink(path)
    return { deleted: path }
  },
})

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  instructions: 'You are a helpful support assistant.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ options: { lastMessages: 11 } }), // at least threadContext.maxMessages + 1
  tools: { whoami, deleteFile },
  channels: {
    adapters: {
      slack: {
        adapter: createSlackAdapter(),
        toolApprovers: 'requester',
      },
      discord: {
        adapter: createDiscordAdapter(),
        toolDisplay: 'text',
      },
    },
    threadContext: { maxMessages: 10 },
    resolveResourceId: async ({ defaultResourceId }) => defaultResourceId,
    handlers: {
      onDirectMessage: async (thread, message, defaultHandler, ctx) => {
        try {
          ctx.signalMetadata.ticketId = await lookupTicket(message)
        } catch (error) {
          ctx.mastra?.getLogger().error('Ticket lookup failed', { error })
          await thread.post('Something went wrong looking up your ticket. Try again in a moment.')
          return
        }
        await defaultHandler(thread, message)
      },
      onMessage: async (thread, message, defaultHandler) => {
        if (thread.channelId !== 'slack:C_SUPPORT') return
        await defaultHandler(thread, message)
      },
    },
  },
})
```

`lookupTicket` is your own function. Replace the `resolveResourceId` body with a mapping to your SSO user when memory should follow the person across platforms. Discord env vars: `DISCORD_BOT_TOKEN`, `DISCORD_PUBLIC_KEY`, `DISCORD_APPLICATION_ID`; route `/api/agents/support-agent/channels/discord/webhook`.

On Discord, approvals still render as a separate card. On platforms that only render text (iMessage), avoid approval-gated tools.

---

## 3. Serverless deployment on Vercel

```bash
npm install @vercel/functions @mastra/redis-streams @chat-adapter/state-redis
```

```typescript
// src/mastra/agents/your-agent.ts
import { Agent } from '@mastra/core/agent'
import { createSlackAdapter } from '@chat-adapter/slack'
import { createRedisState } from '@chat-adapter/state-redis'
import { waitUntil } from '@vercel/functions'

export const yourAgent = new Agent({
  id: 'your-agent',
  name: 'Your Agent',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-6.1-sol',
  channels: {
    adapters: {
      slack: createSlackAdapter(),
    },
    waitUntil,               // keep the function alive after the 200 ack
    state: createRedisState(), // shared dedup across instances, reads REDIS_URL
  },
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { PostgresStore } from '@mastra/pg'
import { RedisStreamsPubSub } from '@mastra/redis-streams'
import { yourAgent } from './agents/your-agent'

// Any persistent, serverless-friendly store works (see mastra-storage)
const storage = new PostgresStore({ id: 'pg-storage', connectionString: process.env.DATABASE_URL })

export const mastra = new Mastra({
  agents: { yourAgent },
  storage,
  pubsub: new RedisStreamsPubSub({
    url: process.env.REDIS_URL,
    keyPrefix: 'mastra:my-app',
  }),
})
```

Without shared pub/sub, a follow-up message landing on another instance starts a second run on the same thread. Set the platform webhook URLs to the production host after deploy.

---

## 4. Provider-managed Telegram bot

```typescript
import { Agent } from '@mastra/core/agent'
import { Mastra } from '@mastra/core/mastra'
import { TelegramProvider } from '@mastra/telegram'
import { PostgresStore } from '@mastra/pg'

// Persistent storage keeps installations; otherwise they live in memory
const storage = new PostgresStore({ id: 'pg-storage', connectionString: process.env.DATABASE_URL })

const supportAgent = new Agent({
  id: 'support',
  name: 'Support agent',
  instructions: 'Help users with product questions.',
  model: 'openai/gpt-6.1-sol',
})

const telegram = new TelegramProvider({
  baseUrl: 'https://your-app.example.com',
  encryptionKey: process.env.MASTRA_ENCRYPTION_KEY,
})

export const mastra = new Mastra({
  agents: { supportAgent },
  storage,
  channels: { telegram },
})

await telegram.connect('support', {
  botToken: process.env.TELEGRAM_BOT_TOKEN,
})
```

Without `baseUrl` the provider falls back to polling (`mode: 'auto'`). Without `botToken`, `connect()` returns a BotFather deep link and a pending installation. `SlackProvider` follows the same pattern: `connect(agentId, { name })` returns an `authorizationUrl` for the OAuth install.
