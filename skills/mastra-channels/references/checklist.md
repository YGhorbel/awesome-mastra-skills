# Channels checklist

Run this before launching a channel agent.

## Wiring

- [ ] Adapter installed and added under `channels.adapters` with the intended key (the key is in the route)
- [ ] Agent registered on `Mastra`; persistent storage configured
- [ ] Agent has memory; `lastMessages` is at least `threadContext.maxMessages + 1`
- [ ] Credentials in `.env.example`; signing secrets set so the adapter verifies requests
- [ ] Webhook, events, and interactions URLs point at `https://<host>/api/agents/<agent-id>/channels/<key>/webhook`
- [ ] Tunnel URLs replaced with the production URL after deploy

## Access and safety

- [ ] Who can reach the bot is understood (Slack: DMs and channels the bot is in, including Slack Connect guests)
- [ ] Sender identity checked from `requestContext.get('channel')` where tools touch private data
- [ ] `resolveResourceId` maps platform users to your user model if memory must follow the person
- [ ] Risky tools use `requireApproval: true`; `toolApprovers` chosen deliberately
- [ ] No approval-gated tools on text-only platforms (iMessage, `toolDisplay: 'text'`) unless another surface approves
- [ ] Custom `onAction` calls `defaultHandler()`; custom approval cards keep `tool_approve:` / `tool_deny:` ids
- [ ] `signalMetadata` holds only non-sensitive, JSON-serializable values
- [ ] Providers have `MASTRA_ENCRYPTION_KEY` so stored tokens are encrypted

## Behavior

- [ ] `toolDisplay`, `streaming`, `textFormat`, `textDisplay`, `typingStatus` fit the platform
- [ ] Instructions use standard markdown (no Slack mrkdwn workarounds)
- [ ] `inlineMedia` matches what the model accepts; `inlineLinks` added for video or image hosts if needed
- [ ] Custom handlers catch errors and post a user-facing message
- [ ] Handler side effects are idempotent (duplicate deliveries happen)

## Serverless and scale

- [ ] `waitUntil` passed on Vercel (or `resolveWaitUntil` where needed)
- [ ] Shared pub/sub (`RedisStreamsPubSub`) on `Mastra` for multi-instance or serverless
- [ ] Shared `state` adapter (`createRedisState()`) for dedup across instances
- [ ] `gateway: false` on adapters that would otherwise open listeners in serverless functions

## Verification

- [ ] A DM, a mention, and a follow-up in a subscribed thread all get answers
- [ ] An approval card approves and denies correctly, by the right user
- [ ] A forced error shows the `formatError` message in the thread
