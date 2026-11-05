# Memory checklist

Run this before calling agent memory done.

## Storage

- [ ] A persistent adapter is configured on `new Mastra({ storage })` or `new Memory({ storage })` (see `mastra-storage`)
- [ ] Local file databases use an absolute path when Studio and the app share them
- [ ] No local file database in a multi-process production deployment
- [ ] Retention policy decided for `memory.messages` and `memory.threads` (see `mastra-storage`)

## Identifiers

- [ ] `resource` comes from the authenticated user or tenant on the server, never the request body
- [ ] `thread` IDs are unique per owner and never reused across resources
- [ ] Shared threads use one room-level `resource` for all participants
- [ ] Speaker tags for multi-user threads are built on the server from verified identity

## Context policy

- [ ] History policy chosen: `lastMessages` for short chats, `messageHistory.maxTokens` when tool output varies
- [ ] Long-running threads use `mastra-observational-memory` instead of a huge `lastMessages`
- [ ] Clients send only the new message
- [ ] Working memory uses `template` or `schema`, not both
- [ ] Instructions say when to update working memory
- [ ] Resource-scoped working memory runs on a supported adapter
- [ ] Subagents or routers that must not write memory use `readOnly: true`

## API and UI

- [ ] Every `listThreads`, `recall`, `cloneThread`, and `deleteMessages` call checks ownership first
- [ ] Memory HTTP endpoints sit behind `server.auth` (see `mastra-auth`)
- [ ] `generateTitle` uses a smaller model if titles are shown
- [ ] Messages converted with `toAISdkV5Messages` where the UI needs AI SDK format

## Operations

- [ ] Tests and short scripts call `await memory.settled()` before closing storage
- [ ] Large attachments uploaded externally on DynamoDB, Convex, or D1
- [ ] A trace reviewed to confirm what memory injected into the prompt (see `mastra-observability`)
