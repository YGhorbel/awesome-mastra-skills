# Agentic UI checklist

Run this before calling an agentic UI done.

## Wiring

- [ ] `@mastra/ai-sdk`, `ai`, and the UI binding installed at compatible versions
- [ ] `version` set on routes, handlers, `toAISdkStream()`, and converters to match the installed `ai`
- [ ] Route path outside the server API prefix (for example `/chat/:agentId`, not `/api/chat`) on the Mastra server
- [ ] Frontend `api` URL points at the right host, port, and agent ID
- [ ] CORS allows the frontend origin when the UI and Mastra run on different origins

## Memory and history

- [ ] With memory: only the last message sent, plus `memory.thread` and `memory.resource`
- [ ] Thread and resource IDs come from authenticated app state, not constants
- [ ] History loaded with `toAISdkMessages()` (or the matching versioned converter) on page load
- [ ] Failed turns (`error` parts) render a readable message

## Rendering

- [ ] Text, reasoning (if `sendReasoning`), and every tool part (`tool-{toolKey}`) handled
- [ ] All tool states handled: `input-streaming`, `input-available`, `output-available`, `output-error`
- [ ] Tools rendered as components define an `outputSchema`
- [ ] Custom events use `data-` types and are awaited on the server
- [ ] Subagent parts (`data-tool-agent*`) shown, hidden, or disabled with `includeSubAgentMetadata: false`

## Interaction

- [ ] Client tools defined without `execute` on the agent the route calls; results added with `addToolOutput()`
- [ ] Suspended tools resumed with `runId` and `resumeData`
- [ ] Stop button calls the chat `stop()`; disconnect behavior matches product needs
- [ ] `heartbeatMs` or `withSseHeartbeat()` set when a proxy or load balancer sits in front
- [ ] `onError` on handlers sanitizes server errors

## Library-specific

- [ ] CopilotKit: `@copilotkit/runtime` in `bundler.externals`, `agent` prop matches an agents key
- [ ] OpenUI: system prompt regenerated after component library changes
- [ ] No new code on `networkRoute()` or `handleNetworkStream()` (deprecated)
