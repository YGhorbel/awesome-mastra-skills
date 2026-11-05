# Channels API reference

Distilled from `https://mastra.ai/reference/agents/channels.md`, `https://mastra.ai/docs/channels.md`, and `https://mastra.ai/reference/channels/*.md`. Added in `@mastra/core@1.22.0`. Verify against the installed version.

## Contents

- ChannelConfig (agent `channels` option)
- Per-adapter options (`ChannelAdapterConfig`)
- Tool display
- Handlers and context
- Channel request context
- Resource and thread ID resolution
- Inline media and links
- ChannelProvider interface
- SlackProvider
- TeamsProvider
- TelegramProvider

---

## ChannelConfig (agent `channels` option)

| Option | Default | Notes |
|---|---|---|
| `adapters` | | `Record<string, Adapter \| ChannelAdapterConfig>`. Key = platform name in the route and `platform`. |
| `handlers` | | `ChannelHandlers` |
| `inlineMedia` | `['image/png','image/jpeg','image/webp','application/pdf']` | Globs or predicate. Non-matching files become text summaries. |
| `inlineLinks` | disabled | `(string \| { match, mimeType })[]` |
| `maxAttachmentStorageBytes` | 100 MiB | Authenticated downloads saved under `channel-attachments/` in the agent workspace (10 MiB each). |
| `tools` | `true` | Whether the channels `getTools()` returns `add_reaction`, `remove_reaction`. Never added automatically. |
| `state` | `MastraStateAdapter` from Mastra storage | Subscriptions and dedup. Requires storage. |
| `userName` | agent `name` | Bot display name. |
| `threadContext` | `{ maxMessages: 10, addSystemMessage: true }` | `maxMessages: 0` disables history fetch (non-DM only). |
| `chatOptions` | | Passed to Chat SDK: `dedupeTtlMs`, `fallbackStreamingPlaceholderText`, `lockScope`, `messageHistory`, `concurrency` (`burst`, `debounce`, `queue`). |
| `resolveResourceId` | `${platform}:${userId}` | Runs only for new threads. |
| `resolveThreadId` | random UUID | Runs only for new threads. Must be unique. |
| `waitUntil` | | Required on Vercel (`@vercel/functions`). Cloudflare Workers and Netlify are detected. |
| `resolveWaitUntil` | | `(c: HonoContext) => waitUntil \| undefined` |

Access at runtime: `agent.getChannels()?.sdk` registers extra Chat SDK handlers.

---

## Per-adapter options (`ChannelAdapterConfig`)

Wrap an adapter as `{ adapter, ...options }`.

| Option | Default | Notes |
|---|---|---|
| `adapter` | | Chat SDK adapter instance. |
| `gateway` | `true` | Persistent Gateway WebSocket listener (Discord-style). `false` for serverless webhook-only. |
| `cors` | | For browser-based adapters. |
| `formatError` | `"❌ Error: <message>"` | `(error, { requestContext }) => PostableMessage` |
| `streaming` | `false` (`true` for Slack) | `boolean \| { updateIntervalMs }`. Needs post-and-edit support. |
| `textFormat` | `'markdown'` | `'plain'` posts literal text. |
| `textDisplay` | `'show'` | `'hidden'`: replies reach the thread only through tools. |
| `toolDisplay` | `'cards'` (`'grouped'` for Slack) | `'cards' \| 'text' \| 'timeline' \| 'grouped' \| 'hidden' \| ToolDisplayFn` |
| `toolApprovers` | `'requester'` | `'anyone'` lets any channel member approve. |
| `typingStatus` | `true` | `boolean` or `(chunk, ctx) => string \| false \| null \| undefined`. `defaultTypingStatus` from `@mastra/core/channels`. |
| `cards`, `formatToolCall` | | Deprecated. Use `toolDisplay`. |

---

## Tool display

- `'cards'`: running card edited with the result. `'text'`: same lifecycle as plain text.
- `'timeline'`, `'grouped'`: inline `task_update` chunks. Require `streaming: true`; Slack only today. Without streaming they fall back to `'cards'`.
- `'hidden'`: tools run silently; with memory, `autoResumeSuspendedTools` can resume data-bearing `suspend()` flows from the next message. Approvals still need an explicit action.
- Function: receives `ToolDisplayEvent` (`running`, `result`, `error`, `approval`, `approved`, `denied`) and `{ mode, platform }`. Return `{ kind: 'post', message }`, `{ kind: 'stream', chunk, openIfEmpty? }`, or `undefined`.

Approve/Deny cards render separately in every string mode. Custom approval cards must keep button ids `tool_approve:<toolCallId>` and `tool_deny:<toolCallId>`, and the default `onAction` must stay active.

---

## Handlers and context

```typescript
type ChannelHandler = (
  thread: Thread,
  message: Message,
  defaultHandler: (thread: Thread, message: Message) => Promise<void>,
  ctx: ChannelHandlerContext,
) => Promise<void>

type ChannelHandlerContext = {
  mastra?: Mastra
  requestContext: RequestContext
  readonly signalMetadata: Record<string, unknown>
  readonly skipped: readonly Message[]
}
```

| Handler | Notes |
|---|---|
| `onDirectMessage` | DMs |
| `onMention` | @mentions; default subscribes the thread |
| `onSubscribedMessage` | Messages in subscribed threads |
| `onMessage` | Opt-in. Unmentioned, unsubscribed messages. Filter by `thread.channelId`. |
| `onAction(event, defaultHandler, ctx)` | Button and select events. Call `defaultHandler()` for unhandled ids. `false` disables approvals too. |

- `ctx.requestContext`: fresh per message; values reach the run.
- `ctx.signalMetadata`: JSON-serializable, non-sensitive; follows the message into active runs; not added to the prompt.
- `ctx.skipped`: earlier batched messages from the same sender.
- Batched dispatch runs the handler once per sender turn. Await `defaultHandler`.
- Errors in custom handlers are logged only. Catch and post yourself.

Type import: `import type { ChannelHandlers } from '@mastra/core/channels'`.

---

## Channel request context

`requestContext.get('channel')` returns `ChannelContext` (`import type { ChannelContext } from '@mastra/core/channels'`): `platform`, `userId`, `userName`, `isDM`, `channelId`, `threadId`, `botUserId`, `botUserName`, `botMention`. Group messages are prefixed `[Name (@ID)]:` so the agent can tell speakers apart. Channel messages carry a `platform` attribute.

---

## Resource and thread ID resolution

`resolveResourceId(ctx)`: `ctx` has `platform`, `thread` (`thread.isDM`), `message` (`message.author.userId`), `defaultResourceId`, `requestContext`.

`resolveThreadId(ctx)`: `platform`, `thread`, `message`, `resourceId` (resolved), `defaultThreadId`, `requestContext`. On collision Mastra logs a warning and generates an id.

---

## Inline media and links

Globs: `image/*`, `video/*`, `*` or `*/*`, exact types. Text-like attachments are downloaded and given as text (truncated over 128 KB; files over 10 MB skipped). Private CDNs (Slack) use authenticated fetch; public CDNs (Discord) pass the URL.

`inlineLinks` string entries HEAD the URL and check `inlineMedia`. Object entries `{ match: 'youtube.com', mimeType: 'video/*' }` skip HEAD and the check.

---

## ChannelProvider interface

Register under `new Mastra({ channels: { slack: provider } })`. Routes merge into the server; `initialize()` runs at startup.

| Member | Notes |
|---|---|
| `id` | Channel type id. |
| `getRoutes()` | OAuth, webhook, event routes. |
| `initialize()` | Restore installations. |
| `configure(credentials \| null)` | `null` clears credentials and stored tokens. |
| `getInfo()` | Discovery metadata for the editor. |
| `connect(agentId, options?)` | Returns `ChannelConnectResult` (for example an authorization URL). |
| `disconnect(agentId)` | Deletes the platform app and state. |
| `listInstallations()` | Public info only. |

Access: `mastra.channels.slack`, `mastra.getChannelProvider<SlackProvider>('slack')`, `mastra.getChannelProviders()`, `await mastra.resolveChannels()`. A resolver (for example `await channels({ projectId })` from `@mastra/connect`) loads providers at runtime.

---

## SlackProvider

`import { SlackProvider } from '@mastra/slack'`. Provisions Slack apps through the Manifest API and runs OAuth installs.

| Option | Notes |
|---|---|
| `refreshToken` | Slack App Configuration refresh token. Single-use; rotates on startup. |
| `token` | Optional configuration access token. |
| `baseUrl` | Public base URL. Required for `connect()`. `setBaseUrl()` also works. |
| `encryptionKey` | 32+ chars, or `MASTRA_ENCRYPTION_KEY`. Without it secrets are stored in plaintext. |
| `storage` | Defaults to Mastra channels storage. Throws without persistent storage. |
| `redirectPath` | Default `'/'`. |
| `onInstall` | `(installation) => Promise<void>` |
| `streaming` (default `true`), `textFormat`, `textDisplay`, `toolDisplay` (default `'grouped'`), `toolApprovers`, `typingStatus`, `waitUntil`, `resolveWaitUntil` | Adapter behavior. |
| `handlers`, `inlineMedia`, `inlineLinks`, `threadContext`, `tools`, `state`, `chatOptions`, `logger` | Forwarded `ChannelConfig` subset. |

Methods: `connect(agentId, { name })` returns `authorizationUrl`; `disconnect`, `getInstallation`, `listInstallations`, `configure`, `setBaseUrl`, `initialize`.

---

## TeamsProvider

`import { TeamsProvider, TEAMS_GRAPH_SCOPE, TEAMS_DEV_PORTAL_SCOPE } from '@mastra/teams'`.

Two exclusive modes: self-managed (`appId`, `appPassword` of an existing Azure Bot) or delegated (`tokenResolver(scope, tenantId?)` provisions an Entra app and bot per agent; requires `encryptionKey`). Other options: `baseUrl` (messaging endpoint `{baseUrl}/teams/events/{webhookId}`), `appTenantId`, `appType` (`'MultiTenant'` default), `storage` (in-memory fallback for dev only), `encryptionKey`, `apiUrl`. Methods: `connect`, `disconnect`, `listInstallations`, `getInstallation`, `configure`, `initialize`, `isConfigured`, `getInfo`, `getAdapter`, `getRoutes`.

---

## TelegramProvider

`import { TelegramProvider } from '@mastra/telegram'`.

| Option | Default | Notes |
|---|---|---|
| `baseUrl` | | Required in webhook mode. |
| `mode` | `'auto'` | Webhook when a base URL exists, else polling. |
| `apiBaseUrl` | `'https://api.telegram.org'` | |
| `encryptionKey` | `MASTRA_ENCRYPTION_KEY` | |
| `storage` | channels storage, else in-memory | |
| `allowedUpdates`, `longPolling`, `commands` (start, help, settings), `commandScope` | | |
| `streaming` | `true` | |
| `toolDisplay` | `'text'` | Rich modes degrade on Telegram. |
| `typingStatus`, `tools`, `waitUntil`, `resolveWaitUntil`, `handlers`, `inlineMedia`, `inlineLinks`, `state`, `threadContext`, `chatOptions`, `resolveResourceId`, `cors`, `formatError`, `logger`, `onInstall` | | |

`connect(agentId, { botToken, commands? })` validates the token with `getMe`. Without `botToken` it returns a BotFather deep link and a pending installation.
