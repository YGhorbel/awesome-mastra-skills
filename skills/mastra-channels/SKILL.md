---
name: mastra-channels
description: "Put a Mastra agent into Slack, Microsoft Teams, Discord, Telegram, WhatsApp, iMessage, and any other Chat SDK platform with the agent channels option, webhook routes, thread context, tool approval cards, streaming replies, custom handlers, and serverless delivery; or let Mastra provision bots with SlackProvider, TeamsProvider, or TelegramProvider. Use this skill whenever the user wants an agent in a messaging app, a Slack bot, a webhook URL for a bot, approve and deny buttons in chat, multi-user threads, or a bot that keeps working on Vercel. Triggers on channels, @mastra/core/channels, @chat-adapter/slack, createSlackAdapter, createDiscordAdapter, createTeamsAdapter, createTelegramAdapter, createWhatsAppAdapter, createiMessageAdapter, createLinqAdapter, Chat SDK, SlackProvider, @mastra/slack, TeamsProvider, TelegramProvider, ChannelProvider, toolDisplay, toolApprovers, threadContext, onMention, waitUntil, channel webhook. Also covers GitHub and Ring listings."
license: Apache-2.0
metadata:
  category: connections
  catalog_summary: "Agents in Slack, Teams, Discord, Telegram, WhatsApp, iMessage: adapters, webhooks, approvals, handlers, providers, serverless"
  display_order: 3
  docs: https://mastra.ai/docs/channels
---

# Mastra Channels

Connect an agent to messaging platforms so users talk to it in DMs, mentions, and threads, with webhooks, memory, approvals, and serverless delivery set up correctly.

---

## When to use

- Adding an agent to Slack, Teams, Discord, Telegram, WhatsApp, iMessage, or another Chat SDK adapter
- Building the webhook URL and testing it locally through a tunnel
- Rendering tool calls and Approve/Deny cards in chat, or hiding them
- Handling DMs, mentions, subscribed threads, and unmentioned messages with custom handlers
- Mapping platform users to your own user IDs for memory (`resolveResourceId`)
- Images, video, PDFs, and links in chat messages (`inlineMedia`, `inlineLinks`)
- Running channel agents on Vercel, Lambda, or other serverless platforms
- Letting Mastra create and install bots (`SlackProvider`, `TeamsProvider`, `TelegramProvider`)

## When NOT to use

- GitHub pull request follow-up and Ring doorbell events: these are signal providers (use `mastra-signals`)
- Managed channel credentials through Mastra Connect (use `mastra-tool-integrations`)
- Building the agent itself (use `mastra-agents`)
- Memory, threads, and `lastMessages` tuning (use `mastra-memory`)
- Tool approval semantics outside chat (use `mastra-agent-approval-hitl`)
- Pub/sub, server middleware, and auth on other routes (use `mastra-server` and `mastra-auth`)
- Deploying the server (use `mastra-deployment`)

---

## Required inputs

- Target platforms and whether you create the bot yourself (adapter) or let Mastra provision it (provider)
- Platform credentials (bot token, signing secret, app ID and password, webhook verify token)
- A public HTTPS base URL (production URL, or a tunnel in development)
- Storage for the Mastra instance (thread subscriptions, approvals, dedup)
- Which tools need approval, and who may approve them in shared channels
- Deployment target (long-running server vs serverless)

---

## The framework: adapter on the agent, webhook route from Mastra

Channels use Chat SDK adapters. Add an adapter under `channels.adapters`; Mastra registers a webhook route for it and runs the normal agent pipeline for each message, streaming the reply back.

```typescript
import { Agent } from '@mastra/core/agent'
import { createSlackAdapter } from '@chat-adapter/slack'

export const yourAgent = new Agent({
  id: 'your-agent',
  name: 'Your Agent',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-6.1-sol',
  channels: {
    adapters: {
      slack: createSlackAdapter(),
    },
  },
})
```

```typescript
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { yourAgent } from './agents/your-agent'

export const mastra = new Mastra({
  agents: { yourAgent },
  storage: new LibSQLStore({ id: 'mastra-storage', url: process.env.DATABASE_URL }),
})
```

Webhook route: `/api/agents/<AGENT_ID>/channels/<ADAPTER_KEY>/webhook`, for example `/api/agents/your-agent/channels/slack/webhook`. Point the platform's event, interactions, or webhook URL there. The adapter key (`slack` above) also becomes the `platform` value.

| Path | Use when |
|---|---|
| Adapter on `channels.adapters` | You create the bot or app yourself and set env vars |
| `ChannelProvider` on `new Mastra({ channels })` | Mastra provisions apps, runs OAuth installs, stores encrypted tokens |

### Message routing

| Handler | Fires on | Default |
|---|---|---|
| `onDirectMessage` | DMs | Runs the agent and posts the reply |
| `onMention` | @mentions | Runs the agent, then subscribes to the thread |
| `onSubscribedMessage` | Later messages in subscribed threads | Runs the agent |
| `onMessage` | Anything else the bot can read | Off unless you supply a function |
| `onAction` | Button and select clicks | Handles built-in Approve/Deny |

Each handler is omitted (default), `false` (disabled), or `(thread, message, defaultHandler, ctx) => Promise<void>`.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` for channels and the installed `ChannelConfig` types. Otherwise fetch `https://mastra.ai/docs/channels.md`, `https://mastra.ai/reference/agents/channels.md`, and the platform page such as `https://mastra.ai/integrations/channels/slack.md`. Trust these over memory.
2. **Install the adapter** (`npm install @chat-adapter/slack`) and add it to `channels.adapters`.
3. **Configure storage** on `Mastra`. Channels need it for subscriptions, approvals, and dedup. Add `memory` to the agent so thread history persists.
4. **Set credentials** the adapter reads (for Slack: `SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN`). See [`references/providers.md`](references/providers.md).
5. **Expose the server.** Run `npx mastra dev`, then `npx cloudflared tunnel --url http://localhost:4111`, and paste `https://<tunnel>/api/agents/<id>/channels/<key>/webhook` into the platform settings (Slack: Event Subscriptions and Interactivity).
6. **Tune presentation.** `toolDisplay`, `streaming`, `textFormat`, `textDisplay`, `typingStatus` per adapter.
7. **Gate tools.** Mark risky tools `requireApproval: true`. Decide `toolApprovers: 'requester'` (default) or `'anyone'`. On platforms without cards, avoid approval-gated tools.
8. **Customize routing and identity** with `handlers`, `ctx.requestContext`, `resolveResourceId`, and `threadContext`.
9. **Prepare for production.** On Vercel pass `waitUntil`. On multi-instance or serverless, configure a shared pub/sub (`RedisStreamsPubSub`) and a shared `state` adapter. Update webhook URLs to the production host.

---

## Deep dive: identity, access, and context

- **Who can reach the agent.** Slack has no allowlist. Anyone in a DM or a channel the bot belongs to, including Slack Connect guests, can use the agent and its tools. Gate on the sender in a handler or tool.
- **Sender identity.** Every run has `requestContext.get('channel')` (type `ChannelContext` from `@mastra/core/channels`) with `platform`, `userId`, `userName`, `isDM`, `channelId`, `threadId`, `botUserId`, `botUserName`, `botMention`.

```typescript
channels: {
  adapters: { slack: createSlackAdapter() },
  handlers: {
    onDirectMessage: async (thread, message, defaultHandler, ctx) => {
      ctx.requestContext.set('locale', 'en-GB')
      await defaultHandler(thread, message)
    },
  },
},
```

- **Memory ownership.** Default `resourceId` is `${platform}:${userId}`. Use `resolveResourceId` to map platform users to your SSO user. It runs only when a thread is created.
- **Thread context.** On the first mention in a thread, Mastra saves the first message plus up to `maxMessages - 1` recent ones (default 10) into memory. Set memory `lastMessages` to at least `maxMessages + 1`. Disable with `threadContext: { maxMessages: 0 }` for adapters that cannot fetch history.
- **Webhook auth.** Channel webhooks are public routes exempt from Mastra server auth. The adapter verifies signatures, so keep signing secrets set.

---

## Failure patterns

- **No storage on `Mastra`.** Subscriptions, approvals, and dedup are lost on restart. Configure storage.
- **Webhook pointed at `localhost`.** Platforms cannot reach it. Use a tunnel, then switch to the production URL after deploy.
- **Wrong path segment.** The route uses the agent `id` and the adapter key, not the variable name.
- **Agent stops mid-reply on Vercel or Lambda.** The function froze after the `200`. Pass `waitUntil` from `@vercel/functions` (or `resolveWaitUntil`).
- **Threads processed twice on serverless.** The default pub/sub is in memory. Configure `RedisStreamsPubSub` on `Mastra`.
- **Duplicate side effects after retries.** Dedup is best effort. Use a shared `state` adapter (`createRedisState()`) and make handler side effects idempotent.
- **Custom handler throws silently.** Errors in custom handlers are only logged. Catch them and post a message to the thread.
- **Approval buttons do nothing.** `onAction: false`, a custom `onAction` that never calls `defaultHandler()`, or custom card ids not exactly `tool_approve:<toolCallId>` / `tool_deny:<toolCallId>`.
- **Approval-gated tool on iMessage or with `toolDisplay: 'text'`.** Text cannot submit approvals; the tool stays suspended. Avoid it or approve from another surface.
- **`timeline` or `grouped` without streaming.** Falls back to `cards` with a warning. Keep `streaming: true` (Slack default).
- **First message trimmed from thread context.** Memory `lastMessages` is lower than `maxMessages + 1`.
- **Expecting channel tools automatically.** `add_reaction` and `remove_reaction` are never added; pass them explicitly from the channels `getTools()`.
- **Prompting for Slack mrkdwn.** Replies post as standard markdown by default. Remove the dialect instructions or set `textFormat: 'plain'`.

---

## Output format

A finished channel delivery contains:

- The agent with `channels.adapters` (or a `ChannelProvider` on `new Mastra({ channels })`)
- Storage on `Mastra` and memory on the agent
- Adapter credentials in `.env.example` and the webhook URL documented per platform
- Approval and display settings matching the platform's card support
- Serverless settings (`waitUntil`, shared pub/sub, shared state) when deployed serverless
- Evidence: a DM and a mention answered in the real platform through a tunnel or staging URL

---

## Reference files

- [`references/api.md`](references/api.md) - `ChannelConfig`, per-adapter options, handlers, context types, `ChannelProvider` interface, Slack, Teams, and Telegram providers.
- [`references/examples.md`](references/examples.md) - Slack agent end to end, multi-platform support agent with handlers, serverless Vercel setup, provider-managed Telegram bot.
- [`references/providers.md`](references/providers.md) - Every platform page: package, factory, env vars, webhook notes, card support; plus GitHub and Ring signal providers.
- [`references/checklist.md`](references/checklist.md) - Launch checklist.

**Live docs**

- https://mastra.ai/docs/channels
- https://mastra.ai/reference/agents/channels
- https://mastra.ai/reference/channels/channel-provider
- https://mastra.ai/reference/channels/slack-provider
- https://mastra.ai/reference/channels/teams-provider
- https://mastra.ai/reference/channels/telegram-provider
- https://mastra.ai/integrations/channels/slack
