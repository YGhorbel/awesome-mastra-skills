# Tool integrations checklist

Run this before calling an integration done.

## Web tool packages

- [ ] Package and its peer installed (`@tavily/core`, `parallel-web`, `firecrawl`, `zod`)
- [ ] API key in env vars and `.env.example`, never hardcoded
- [ ] Key presence checked at startup (Parallel fails only at execution)
- [ ] Search tool paired with a fetch or extract tool where full content matters
- [ ] Instructions say when to search, when to read pages, and to cite URLs
- [ ] `maxResults` and content size options bound token use
- [ ] Vendor cost per call estimated against expected traffic

## Mastra Connect

- [ ] Platform project exists and `MASTRA_PROJECT_ID` is set
- [ ] Token stored as `MASTRA_PLATFORM_ACCESS_TOKEN` (not `MASTRA_API_TOKEN`)
- [ ] Region set with `MASTRA_PLATFORM_REGION` when the project is in the EU
- [ ] Each needed provider connected with `mastra connect add`, and `mastra connect list` shows it active
- [ ] Connections named so an agent can tell them apart, or pinned with `connectionId`
- [ ] `providers` limits each agent to the providers it needs
- [ ] `allowTools` or `disallowTools` limits actions, with keys checked against the toolset reference
- [ ] Destructive tools (`*_delete_*`, sends, SQL) gated with `requireApproval`
- [ ] Per-request options derived from roles set server-side, not unbounded values
- [ ] Approval handling implemented (see `mastra-agent-approval-hitl`)
- [ ] `credential()` used only where toolsets fall short, and never logged
- [ ] Channels: public URL reachable, `MASTRA_ENCRYPTION_KEY` set for Telegram and Teams, channel linked to an agent in Studio

## Verification

- [ ] A Studio run shows the expected tool call and result in the trace
- [ ] Warnings like `[@mastra/connect] Skipping` absent from logs
- [ ] `needs_reauth` connections have an owner who reauthorizes them
