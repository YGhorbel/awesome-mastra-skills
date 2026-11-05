# Channel platforms

Distilled from every page under `https://mastra.ai/integrations/channels/*` and `https://mastra.ai/reference/channels/*`. Platform setup (app creation, scopes, verification) lives in each adapter's own docs; check them for current variable names.

## Contents

- Chat SDK adapters (agent `channels.adapters`)
- Mastra-managed providers (`new Mastra({ channels })`)
- Signal providers listed with channels (GitHub, Ring)
- Other Chat SDK adapters

---

## Chat SDK adapters (agent `channels.adapters`)

Route for all: `/api/agents/<agent-id>/channels/<adapter-key>/webhook`.

| Platform | Package | Factory | Env vars (examples from docs) | Notes |
|---|---|---|---|---|
| Slack | `@chat-adapter/slack` | `createSlackAdapter()` | `SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN` | Native markdown, streaming on by default, `toolDisplay` default `'grouped'`, interactive cards. Same URL for Event Subscriptions and Interactivity. Acknowledge within 3 s; Slack retries up to three times. |
| Discord | `@chat-adapter/discord` | `createDiscordAdapter()` | `DISCORD_BOT_TOKEN`, `DISCORD_PUBLIC_KEY`, `DISCORD_APPLICATION_ID` | Interactions endpoint uses the route. Regular message events may need the Gateway (`gateway: true` default; `false` on serverless). Public CDN media. |
| Microsoft Teams | `@chat-adapter/teams` | `createTeamsAdapter({ appType: 'SingleTenant' })` | `TEAMS_APP_ID`, `TEAMS_APP_PASSWORD`, `TEAMS_APP_TENANT_ID` | Azure bot registration; bot endpoint is the route. |
| Telegram | `@chat-adapter/telegram` | `createTelegramAdapter()` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET_TOKEN`, `TELEGRAM_BOT_USERNAME` | Webhook or polling mode (polling handy for local dev). |
| WhatsApp Business Cloud | `@chat-adapter/whatsapp` | `createWhatsAppAdapter()` | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` | Route handles POST events; follow adapter docs for Meta callback verification. |
| iMessage (Photon) | `@photon-ai/chat-adapter-imessage` | `createiMessageAdapter()` | Hosted: `IMESSAGE_PROJECT_ID`, `IMESSAGE_PROJECT_SECRET`, `IMESSAGE_WEBHOOK_SECRET`. Self-hosted: `IMESSAGE_SERVER_URL`, `IMESSAGE_API_KEY`, `IMESSAGE_PHONE` | Use key `imessage`, `toolDisplay: 'text'`, `threadContext: { maxMessages: 0 }`. No cards. Webhooks in hosted mode only. |
| iMessage (Linq) | `@linqapp/chat-sdk-adapter` | `createLinqAdapter({ apiKey, signingSecret })` | `LINQ_API_KEY`, `LINQ_WEBHOOK_SECRET` | iMessage, RCS, SMS. Subscribe to `message.received`, `reaction.added`, `reaction.removed`. Use `toolDisplay: 'text'`. |

Shared state for at-least-once platforms (Photon, Linq) and serverless: `@chat-adapter/state-redis`, `createRedisState()` (reads `REDIS_URL`), set on `channels.state`.

Card support: Slack, Discord, and Teams render approval cards. Telegram degrades rich modes to text. iMessage cannot submit approvals; approval-gated tools stay suspended there.

---

## Mastra-managed providers (`new Mastra({ channels })`)

Use when Mastra should create, install, and store bots. Provide persistent storage and `MASTRA_ENCRYPTION_KEY`.

| Provider | Package | Key options | Connect |
|---|---|---|---|
| `SlackProvider` | `@mastra/slack` | `refreshToken` (`SLACK_APP_CONFIG_REFRESH_TOKEN`), `baseUrl` (`MASTRA_BASE_URL`), `encryptionKey` | `connect(agentId, { name })` returns an OAuth `authorizationUrl` |
| `TeamsProvider` | `@mastra/teams` | Self-managed `appId`/`appPassword`, or delegated `tokenResolver`; `baseUrl` | `connect(agentId)`; messaging endpoint `{baseUrl}/teams/events/{webhookId}` |
| `TelegramProvider` | `@mastra/telegram` | `baseUrl`, `mode: 'auto' \| 'webhook' \| 'polling'`, `commands` | `connect(agentId, { botToken })`, or a BotFather deep link without a token |

Mastra Connect: `channels: await channels({ projectId: process.env.MASTRA_PROJECT_ID! })` from `@mastra/connect` manages credentials on the platform (see `mastra-tool-integrations`).

Build your own by implementing `ChannelProvider` (`id`, `getRoutes`, `initialize`, `configure`, `getInfo`, `connect`, `disconnect`, `listInstallations`).

---

## Signal providers listed with channels (GitHub, Ring)

These pages sit under channels but deliver notification signals to agent threads instead of chat messages. Details belong to `mastra-signals`.

| Provider | Package | Wiring | Requirements |
|---|---|---|---|
| GitHub PR follow-up | `@mastra/github-signals` | `signals: [new GithubSignals()]`, then `githubSignals.subscribeThreadToPR({ threadId, resourceId, pr: { owner, repo, number }, mode: 'review' \| 'working' })` | Storage with memory and notifications, `gitcrawl` and `sqlite3` on `PATH`, authenticated `gh` CLI. Polls every 5 minutes. Adds `github_subscribe_pr`, `github_unsubscribe_pr` tools. |
| Ring doorbells and cameras | `@mastra/ring-signals` | `signals: [new RingSignals()]` | `RING_CLIENT_ID`, `RING_CLIENT_SECRET`, `RING_HMAC_KEY`, `MASTRA_ENCRYPTION_KEY`, optional `RING_BASE_URL`. Routes under `/ring` (`/ring/link`, `/ring/token`, `/ring/webhook`, `/ring/home`). Adds `ring_snapshot`, `ring_clip` tools. Rate-limit `/ring/token`. |

---

## Other Chat SDK adapters

The Chat SDK catalog (`https://chat-sdk.dev/adapters`) is canonical. At the time of the docs it listed AgentPhone, Baileys WhatsApp, Discord, GitHub, Google Chat, iMessage, Kapso, Lark / Feishu, Linear, Linq, Liveblocks, Matrix, Mattermost, Messenger, Novu, Resend, Sendblue, Telegram, Twilio, Velt, Web, Webex, WeChat, WhatsApp Business Cloud, X, Zalo, Zernio.

Wiring is identical: install the adapter, add its factory to `channels.adapters`, set its credentials, and point its webhook at the generated route. Before wiring, check the adapter's attachment and card support, credentials, required scopes, whether it needs a long-running listener or polling, separate setup or interaction routes, and webhook verification.
