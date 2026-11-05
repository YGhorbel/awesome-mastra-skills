---
name: mastra-tool-integrations
description: "Give Mastra agents ready-made third-party tools: web search and scraping through @mastra/tavily, @mastra/brightdata, @mastra/parallel, @mastra/perplexity, and Firecrawl, plus Mastra platform Connect (@mastra/connect) for platform-managed GitHub, Slack, Linear, Gmail, Notion, Jira, HubSpot, and MCP provider tools, chat channels, and raw credentials. Use this skill whenever the user wants an agent to search the web, read or crawl pages, call a SaaS API without storing OAuth tokens, filter or approve provider tools, choose between connected accounts, or wire Slack, Discord, Telegram, or Teams through Connect. Triggers on createTavilyTools, createTavilySearchTool, createBrightDataTools, createParallelTools, createPerplexitySearchTool, Firecrawl, @mastra/connect, tools() from @mastra/connect, channels(), credential(), mastra connect add, MASTRA_PLATFORM_ACCESS_TOKEN, allowTools, requireApproval, connection_name. Also triggers for any request to add an off-the-shelf integration instead of writing a custom tool."
license: Apache-2.0
metadata:
  category: connections
  catalog_summary: "Web tools (Tavily, Bright Data, Parallel, Perplexity, Firecrawl) and Mastra Connect tools, channels, and credentials"
  display_order: 4
  docs: https://mastra.ai/docs/mastra-platform/connect/overview
---

# Mastra Tool Integrations

Add prebuilt third-party tools to agents: web search packages that wrap a vendor SDK, and Mastra Connect for platform-managed SaaS tools, channels, and credentials.

---

## When to use

- Giving an agent web search, page extraction, crawling, or site mapping
- Choosing between Tavily, Bright Data, Parallel, Perplexity, and Firecrawl
- Calling GitHub, Slack, Linear, Gmail, Notion, Jira, HubSpot, and similar APIs without handling OAuth in the app
- Restricting which provider tools an agent gets, per agent or per request
- Requiring approval for destructive provider tools
- Handling several accounts of one provider (two Slack workspaces)
- Exposing Slack, Discord, Telegram, or Teams channels with platform-managed credentials
- Fetching a raw provider credential for an SDK the toolsets do not cover

## When NOT to use

- Writing your own tool with `createTool` (use `mastra-tools`)
- Connecting to an arbitrary MCP server yourself (use `mastra-mcp`)
- Self-managed channels and channel behavior (use `mastra-channels`)
- Handling approval suspend and resume flows (use `mastra-agent-approval-hitl`)
- Browser automation (use `mastra-browser`)
- Platform projects, deploys, and tokens in general (use `mastra-platform`)
- Composio or Arcade catalogs picked in Studio (use `mastra-studio-editor`)
- Perplexity as a chat model rather than a search tool (use `mastra-models`)

---

## Required inputs

- The capability: search, fetch or extract, crawl, or a specific SaaS action
- Which provider, and its API key name (see `references/providers.md`)
- For Connect: a Mastra platform project, its ID, and a platform access token
- Which tools the agent may use, and which need human approval
- Whether access depends on the user (role, tenant)
- Whether the project has more than one connection per provider

---

## The framework: two integration styles

| Style | Packages | Credentials | Returns |
|---|---|---|---|
| Vendor tool packages | `@mastra/tavily`, `@mastra/brightdata`, `@mastra/parallel`, `@mastra/perplexity` | Vendor API key in env | Tools built with `createTool` and Zod schemas |
| Hand-built with an SDK | `firecrawl` plus `createTool` | Vendor API key in env | Your own tools |
| Mastra Connect | `@mastra/connect` | Stored on the platform, proxied per call | `tools()` resolver, `channels()` resolver, `credential()` |

Vendor package factories read their key from the environment by default and accept `{ apiKey }` to override:

```typescript
import { Agent } from '@mastra/core/agent'
import { createTavilySearchTool, createTavilyExtractTool } from '@mastra/tavily'

export const webSearchAgent = new Agent({
  id: 'web-search-agent',
  name: 'Web Search Agent',
  model: 'anthropic/claude-sonnet-5-5',
  instructions:
    'Use the search tool to find relevant pages, then use the extract tool to get full content from the best results.',
  tools: {
    search: createTavilySearchTool(),
    extract: createTavilyExtractTool(),
  },
})
```

Connect returns a resolver that Mastra calls on every `generate()` and `stream()`:

```typescript
import { Agent } from '@mastra/core/agent'
import { tools } from '@mastra/connect'

export const opsAgent = new Agent({
  id: 'ops',
  name: 'ops',
  instructions: 'You help the team track work in Linear and GitHub.',
  model: 'openai/gpt-6-luna',
  tools: tools({
    providers: {
      linear: { allowTools: ['linear_list_issues', 'linear_create_issue'] },
      github: { requireApproval: true },
    },
  }),
})
```

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/<package>/dist/docs/` and the installed types (`@mastra/connect`, `@mastra/tavily`, and so on). Otherwise fetch the integration page as Markdown, for example `https://mastra.ai/integrations/tools/tavily.md` or `https://mastra.ai/reference/connect/tools.md`. Trust these over memory. Toolsets change with each `@mastra/connect` release.
2. **Pick the provider** with `references/providers.md`: capability, cost model, and whether the app may hold the key.
3. **Install** the package and its peer (`npm install @mastra/tavily @tavily/core zod`, `npm install @mastra/parallel parallel-web zod`, `npm install @mastra/connect`).
4. **Set env vars** (`TAVILY_API_KEY`, `BRIGHTDATA_API_TOKEN`, `PARALLEL_API_KEY`, `PERPLEXITY_API_KEY`, `FIRECRAWL_API_KEY`, or `MASTRA_PLATFORM_ACCESS_TOKEN` plus `MASTRA_PROJECT_ID`). List them in `.env.example`.
5. **For Connect, connect accounts.** `mastra auth login`, `mastra auth tokens create my-app`, save it as `MASTRA_PLATFORM_ACCESS_TOKEN`, then `mastra connect add <provider-id>` and `mastra connect list`.
6. **Attach tools.** Pass the factory result or `tools()` to the agent. Merge with your own tools through a `tools` function when needed.
7. **Narrow the surface.** Allowlist tool keys, gate writes with `requireApproval`, and vary options by role with the callback form.
8. **Write instructions** that name each tool and when to call it (search first, then extract).
9. **Handle approval** for gated tools (see `mastra-agent-approval-hitl`).
10. **Test** in Studio (`npx mastra dev`) and confirm tool calls in the trace.

---

## Deep dive: Connect resolution and channels

- Connection choice per provider: explicit `connectionId` wins, then the single active connection. With several active connections the toolset gains `<provider>__list_connections` and every tool requires a `connection_name` input.
- Connections in `needs_reauth` are skipped with a warning. Replace them with the `mastra connect` CLI.
- The resolver caches for `ttlMs` (30000 default) and refreshes in the background. `await resolver.refresh()` forces a fetch.
- Callback options are memoized per distinct value, at most 32. Derive them from a closed set such as roles.

```typescript
import { Mastra } from '@mastra/core'
import { channels } from '@mastra/connect'
import { assistant } from './agents/assistant'

export const mastra = new Mastra({
  agents: { assistant },
  channels: await channels({ providers: ['slack', 'discord'] }),
})
```

Channels need a public URL for webhooks (`MASTRA_SERVER_URL` off-platform) and a Studio step to connect the channel to an agent. Set `MASTRA_ENCRYPTION_KEY` for Telegram and Teams secrets.

---

## Failure patterns

- **Token saved as `MASTRA_API_TOKEN`.** The CLI suggests it but `@mastra/connect` ignores it. Use `MASTRA_PLATFORM_ACCESS_TOKEN`.
- **`missing_project_id`.** Set `MASTRA_PROJECT_ID` or pass `projectId`.
- **`invalid_options` at resolution.** A tool key or glob in `allowTools`, `disallowTools`, or `requireApproval` matches nothing, or both allow and disallow are set at one level. Check keys in the provider toolsets reference.
- **No tools from a provider.** No active connection, wrong project, filtered out, or the installed `@mastra/connect` lacks that toolset. Run `mastra connect list` and look for `[@mastra/connect] Skipping` warnings.
- **`proxy_error` with status 401 or 403.** Expired or revoked credential, or missing scopes. Reauthorize. Filtering tools does not change credential permissions.
- **Passing `autoApproveTools`.** Removed. It throws `invalid_options`. Use `requireApproval`.
- **Per-request options from user IDs.** Each distinct value creates a cache entry (max 32). Use roles.
- **Logging `credential()` output.** It bypasses the proxy, host limits, and audit records. Never log or return it.
- **Resend will not connect.** Use an API key with Full access, not Sending access.
- **Missing search API key.** Parallel fails only when the tool runs. Check env vars at startup.
- **Mixing allow and deny domains in one Perplexity call.** Not allowed. Use one list type per call.
- **Too many provider tools on one agent.** Tool choice degrades. Allowlist or split into subagents (see `mastra-multi-agent`).

---

## Output format

A finished integration delivery contains:

- Installed packages and their peers in `package.json`
- The tool factory or `tools()` call wired into the agent, with allowlists and approval rules
- Agent instructions naming each tool and when to call it
- Required env vars in `.env.example` (never commit keys or platform tokens)
- For Connect: the `mastra connect add` commands run and the connection names chosen
- Evidence: a Studio run or trace showing the tool call and result

---

## Reference files

- [`references/api.md`](references/api.md) - Factory signatures, tool IDs, inputs and outputs for each web package, and `tools()`, `channels()`, `credential()` options and errors.
- [`references/providers.md`](references/providers.md) - Comparison of web tool packages and the Connect provider directory with IDs.
- [`references/examples.md`](references/examples.md) - Research agent, Firecrawl tools, role-based Connect tools, combined tools, multi-account Slack, raw credential.
- [`references/checklist.md`](references/checklist.md) - Integration security and readiness checklist.

**Live docs**

- https://mastra.ai/integrations/tools/tavily
- https://mastra.ai/integrations/tools/brightdata
- https://mastra.ai/integrations/tools/parallel
- https://mastra.ai/integrations/tools/perplexity
- https://mastra.ai/integrations/tools/firecrawl
- https://mastra.ai/docs/mastra-platform/connect/overview
- https://mastra.ai/docs/mastra-platform/connect/tools
- https://mastra.ai/docs/mastra-platform/connect/channels
- https://mastra.ai/reference/connect/tools
- https://mastra.ai/reference/connect/providers
