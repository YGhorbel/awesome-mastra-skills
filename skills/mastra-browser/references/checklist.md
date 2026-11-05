# Browser checklist

Run this before calling a browser agent done.

## Provider and runtime

- [ ] Provider matches the task: AgentBrowser (refs, deterministic), Stagehand (natural language), Firecrawl (hosted), BrowserViewer (CLI)
- [ ] Local launches have Chromium installed (`npx playwright install chromium`), or the browser comes from `cdpUrl` or a cloud provider
- [ ] Provider credentials in `.env.example` (`FIRECRAWL_API_KEY`, `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID`, model keys for Stagehand)
- [ ] `BrowserViewer` sits on a `Workspace` with a sandbox, and its CLI plus skill are installed in that environment

## Isolation and safety

- [ ] `scope: 'thread'` for multi-user apps, with memory so each conversation has a thread
- [ ] `cdpUrl` usage reviewed: it forces shared scope; use a per-session async `cdpUrl` if users must not share
- [ ] Session cookies set with `setCookies` from app code, never placed in instructions or messages
- [ ] `browser_evaluate` excluded unless needed
- [ ] Sensitive actions (purchases, submissions, account changes) gated by approval or confirmation (see `mastra-agent-approval-hitl`)
- [ ] Page content treated as untrusted input; guardrail processors considered (see `mastra-processors-guardrails`)

## Agent behavior

- [ ] Instructions name the provider's tools and the snapshot, act, verify loop (AgentBrowser) or act, extract, observe (Stagehand)
- [ ] Screenshot tools excluded for non-vision models
- [ ] `maxSteps` large enough for multi-page tasks but bounded
- [ ] Timeouts (`timeout`, `domSettleTimeout`, Firecrawl `ttl`) fit the target sites

## Operations

- [ ] `ws` and `@hono/node-ws` installed for Studio screencast on long-running servers (omit on serverless)
- [ ] Recording `outputDir` set when runs must be reviewable; storage for recordings planned
- [ ] Browsers closed on shutdown (`browser.close()`) and per-thread sessions closed when conversations end (`closeThreadSession`)
- [ ] A Studio run shows the agent completing the task end to end
