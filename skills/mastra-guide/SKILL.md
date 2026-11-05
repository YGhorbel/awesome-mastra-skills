---
name: mastra-guide
description: "Entry point and router for building with the Mastra TypeScript AI framework: maps any goal to the right Mastra feature and the skill that covers it, and sets the rule to verify every API against current docs before writing code. Use this skill whenever the user mentions Mastra, @mastra packages, or asks what Mastra can do, which Mastra primitive to use, how the pieces fit together, or where to start. Triggers on Mastra, mastra.ai, @mastra/core, which Mastra feature, agent or workflow, how do I build X with Mastra, Mastra architecture, Mastra overview, Mastra docs lookup. Also triggers at the start of any task inside a project that has a src/mastra folder or @mastra dependencies, even if the user does not name the feature."
license: Apache-2.0
metadata:
  category: getting-started
  catalog_summary: "Router: map any goal to the right Mastra feature and skill, plus the docs lookup protocol"
  display_order: 1
  docs: https://mastra.ai/docs
---

# Mastra Guide

Route any Mastra request to the right feature and skill, and verify APIs against current docs before writing code.

---

## When to use

- The user names Mastra but not a specific feature
- Choosing between primitives (agent vs workflow, memory vs RAG vs knowledge, tool vs MCP)
- Planning a new Mastra app and deciding which features it needs
- Looking up where an API is documented or checking that an API still exists
- Onboarding someone to how Mastra's pieces fit together

## When NOT to use

- The feature is already clear: go straight to its skill (table below)
- Building a full app end to end, idea to production (use `mastra-build-playbook`)
- Creating a new project or install problems (use `mastra-project-setup`)
- An error message to fix (use `mastra-troubleshooting`)
- Upgrading between Mastra versions (use `mastra-migrations`)

---

## Required inputs

- What the user is trying to build or fix, in one sentence
- Whether a Mastra project exists (`ls node_modules/@mastra/` and `src/mastra/index.ts`)
- The installed `@mastra/core` version when the project exists

---

## The framework: one instance, many primitives

A Mastra app is one `Mastra` instance that registers primitives. Registration wires in shared storage, logging, tracing, the server API, and Studio.

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'

export const mastra = new Mastra({
  agents: { supportAgent },        // open-ended, tool-using LLM loops
  workflows: { refundWorkflow },    // fixed multi-step processes
  scorers: { answerRelevancy },     // evals
  storage,                          // persistence for memory, runs, traces
  // plus: vectors, mcpServers, server, logger, observability, ...
})
```

### Routing table

| The user wants to | Use skill |
|---|---|
| Start a project, configure `new Mastra()`, run `mastra dev` | `mastra-project-setup` |
| Build an app end to end | `mastra-build-playbook` |
| An LLM that decides what to do | `mastra-agents` |
| Give an agent abilities (APIs, DB, code) | `mastra-tools` |
| Typed JSON output | `mastra-structured-output` |
| Filter, redact, moderate, block prompt injection | `mastra-processors-guardrails` |
| Pause for approval or ask the user | `mastra-agent-approval-hitl` |
| Several cooperating agents | `mastra-multi-agent` |
| Load task instructions on demand inside a Mastra agent | `mastra-agent-skills` |
| Define agents as files instead of classes | `mastra-file-based-agents` |
| Classify or route inputs | `mastra-classifier` |
| Stream tokens, tool calls, and events | `mastra-streaming` |
| Speech in or out | `mastra-voice` |
| Pick a provider or model ID, fallbacks, gateways | `mastra-models` |
| Fixed steps, branching, parallel, loops | `mastra-workflows` |
| Pause and resume a workflow, snapshots, time travel | `mastra-workflow-suspend-resume` |
| Conversation history, threads, working memory | `mastra-memory` |
| Recall older messages by meaning | `mastra-semantic-recall` |
| Very long conversations without compaction | `mastra-observational-memory` |
| Answer from documents with retrieval | `mastra-rag` |
| Managed, scoped knowledge for agents | `mastra-knowledge` |
| Pick a database for storage | `mastra-storage` |
| Pick a vector database | `mastra-vector-stores` |
| Work that outlives a request, durable agents, coding agents | `mastra-harness` |
| Run agents or workflows on a schedule | `mastra-schedules` |
| Push events or state into a running thread | `mastra-signals` |
| Filesystem, shell, code execution in isolation | `mastra-workspace-sandbox` |
| Let an agent drive a browser | `mastra-browser` |
| Use or expose MCP servers | `mastra-mcp` |
| Agent to agent protocols (A2A, ACP) | `mastra-a2a-acp` |
| Slack, Discord, Telegram, Teams, WhatsApp bots | `mastra-channels` |
| Prebuilt search and scraping tools, Platform Connect | `mastra-tool-integrations` |
| HTTP API, custom routes, middleware | `mastra-server` |
| Call Mastra from a frontend or another service | `mastra-client-sdk` |
| Embed Mastra in Next.js, Vite, SvelteKit, and others | `mastra-framework-integration` |
| Chat UI (AI SDK UI, assistant-ui, CopilotKit) | `mastra-agentic-ui` |
| Protect the API, identify users | `mastra-auth` |
| Score output quality | `mastra-evals` |
| Datasets, experiments, CI gates | `mastra-datasets-experiments` |
| Traces, logs, metrics, cost | `mastra-observability` |
| Studio and the prompt Editor | `mastra-studio-editor` |
| Ship to a cloud or server | `mastra-deployment` |
| Ship to Mastra Platform | `mastra-platform` |
| Inspect or call a running server from the terminal | `mastra-cli-api` |
| Fix an error | `mastra-troubleshooting` |
| Upgrade versions | `mastra-migrations` |

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/<package>/dist/docs/` and installed types. Otherwise fetch the live page as Markdown by appending `.md` (for example `https://mastra.ai/docs/memory/overview.md`). The full page index is `https://mastra.ai/llms.txt`. Trust these over memory. See [`references/api.md`](references/api.md).
2. **Check for a native capability.** Before designing custom infrastructure, search the routing table and docs index. Mastra often ships the feature (task tracking, web fetch, approvals, schedules, retries).
3. **Route.** Open the matching skill and follow its workflow. Multi-feature requests chain skills (see [`references/examples.md`](references/examples.md)).
4. **Build the smallest working slice.** One agent or workflow, registered, callable.
5. **Test in Studio** with `npx mastra dev` at `http://localhost:4111`, or call it with `npx mastra api` (`mastra-cli-api`).
6. **Add quality and visibility.** Evals (`mastra-evals`) and tracing (`mastra-observability`) before production.
7. **Ship.** `mastra-deployment` or `mastra-platform`.

---

## Deep dive: choosing what goes into context

From Mastra's context engineering guide. Pick the mechanism by what the model needs to see.

| Need | Mechanism | Skill |
|---|---|---|
| Stable identity, rules | Agent `instructions` | `mastra-agents` |
| Data from an API or DB on demand | Tools | `mastra-tools` |
| Current user or account data | Inline in the message, or `RequestContext` for runtime config | `mastra-agents` |
| Large stable knowledge base | RAG | `mastra-rag` |
| User or org managed documents | Filesystem through a workspace | `mastra-workspace-sandbox` |
| Recent conversation, durable facts | Memory | `mastra-memory` |
| Long-running conversation | Observational memory | `mastra-observational-memory` |
| Events during a run | Signals | `mastra-signals` |
| Procedures needed only sometimes | Agent skills | `mastra-agent-skills` |
| Too much context | `toModelOutput`, `ToolCallFilter`, `TokenLimiter`, subagent `messageFilter` | `mastra-processors-guardrails`, `mastra-multi-agent` |

`RequestContext` values are runtime data. They are not added to the prompt automatically.

---

## Failure patterns

- **Writing Mastra code from memory.** APIs change between releases. Look up the page first.
- **Building custom infrastructure Mastra already has.** Custom approval queues, cron runners, retry loops. Check the routing table and docs index first.
- **Using an agent for a fixed process.** If the steps are known, a workflow is cheaper and more predictable.
- **Using a workflow for open-ended reasoning.** If the steps depend on what the model finds, use an agent.
- **One giant agent with every tool.** Split by responsibility into subagents.
- **Stuffing everything into instructions.** Move per-request data, documents, and history into the right mechanism.
- **Unregistered primitives.** Anything not on `new Mastra({...})` misses storage, tracing, Studio, and the API.

---

## Output format

A routing answer contains:

- The feature(s) that solve the request and why
- The skill(s) to apply, in order
- The docs URLs to verify against
- When code follows: the files to create and where they register in `src/mastra/index.ts`

---

## Reference files

- [`references/api.md`](references/api.md) - Docs lookup protocol: embedded docs, `llms.txt`, Markdown page URLs, packages map.
- [`references/examples.md`](references/examples.md) - Worked routing examples for common app types, with the skill chain for each.
- [`references/checklist.md`](references/checklist.md) - Native-capability-first checklist before writing custom code.

**Live docs**

- https://mastra.ai/llms.txt
- https://mastra.ai/docs
- https://mastra.ai/reference
- https://mastra.ai/models
- https://mastra.ai/integrations
- https://mastra.ai/docs/guides/context-engineering
- https://mastra.ai/docs/guides/agent-lifecycle
