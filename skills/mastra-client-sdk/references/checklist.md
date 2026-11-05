# Client SDK checklist

Run this before calling a client integration done.

## Setup

- [ ] `@mastra/client-js` version matches the server's `@mastra/core` and `@mastra/server` release line
- [ ] One shared `MastraClient` instance, configured from `MASTRA_API_URL`
- [ ] `baseUrl` is the server origin; `apiPrefix` set only when the server uses a custom prefix
- [ ] Retry settings (`retries`, `backoffMs`, `maxBackoffMs`) suit the call type; long generations are not retried blindly

## Auth and browser concerns

- [ ] Token sent in `headers.Authorization` as `Bearer <token>`, or `credentials: 'include'` for cookie sessions
- [ ] No long-lived secret tokens shipped in browser bundles
- [ ] Server CORS allows the frontend origin (concrete origin when credentials are used)
- [ ] 401 and 403 responses handled with a sign-in or permission message

## Calls

- [ ] Agent and workflow IDs confirmed with `listAgents()` and `listWorkflows()`
- [ ] Memory calls pass `memory.thread` and `memory.resource`; only the new message is sent when memory is on
- [ ] Request context passed as `RequestContext` from `@mastra/client-js` or a plain object
- [ ] Streams consumed with `processDataStream()` and awaited
- [ ] Cancellation wired: per-call `abortSignal`, `reader.cancel()`, or `abortRun()` for durable runs
- [ ] Client tools created with `createTool` from `@mastra/client-js` and passed in `clientTools`
- [ ] Suspended tool calls discovered with `listSuspendedRuns()` and resumed with approve or decline

## Reliability

- [ ] Every call wrapped in `try/catch` with user-facing error states
- [ ] Reconnecting subscriptions (`subscribeToThread`, agent controller) re-sync state after reconnect
- [ ] Calls tested against `mastra dev` and the deployed server
