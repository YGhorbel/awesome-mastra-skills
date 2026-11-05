# Mastra Skills

**Feature-by-feature [Agent Skills](https://agentskills.io) for building, testing, and shipping AI agents with [Mastra](https://mastra.ai), the TypeScript AI framework.**

## What this project is

Mastra Skills is a set of 47 Agent Skills for the Mastra framework. Each skill covers one feature area, such as agents, tools, workflows, memory, RAG, evals, or deployment. A skill explains when to use the feature, the core workflow, common mistakes, and the exact APIs, with examples taken from the current Mastra docs.

The router skill `mastra-guide` sends any request to the right skill, and `mastra-build-playbook` walks a project from idea to production.

## Who should use it

- Developers building agents, workflows, or AI backends in TypeScript with Mastra
- Anyone using an AI coding assistant (Claude Code and other Agent Skills-compatible tools) on a Mastra project
- Teams evaluating Mastra who want a structured reference for its features

This repo is not for Python projects or other frameworks.

## What problems it solves

- **Outdated or invented APIs.** Assistants often guess Mastra APIs from old training data. Each skill tells the assistant to check the current docs first.
- **Fast-moving docs.** Mastra's docs are large and change between releases. The skills map each feature to the docs pages it comes from, so updates are easy to trace.
- **Finding the right feature.** The routing table in `mastra-guide` maps a goal, like "give my agent a database," to the skill that covers it.
- **Repeated setup mistakes.** Common errors (ESM setup, model string format, tool signatures, env vars) are covered in one place.
- **Loading only what you need.** One skill per feature means an assistant loads the relevant instructions, not a single large document.

## Table of contents

- [What this project is](#what-this-project-is)
- [Who should use it](#who-should-use-it)
- [What problems it solves](#what-problems-it-solves)
- [Table of contents](#table-of-contents)
- [Installation](#installation)
- [Contributing](#contributing)
- [How a skill is built](#how-a-skill-is-built)
- [Catalog](#catalog)
- [Repository structure](#repository-structure)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Installation

Pick one of these methods.

### Claude Code (plugin marketplace)

```
/plugin marketplace add YGhorbel/awesome-mastra-skills
/plugin install mastra-skills@mastra-skills
```

### Any agent that supports the skills CLI

```bash
npx skills add YGhorbel/awesome-mastra-skills
```

### Manual

```bash
git clone https://github.com/YGhorbel/awesome-mastra-skills.git
```

Then copy or symlink `skills/*` into `~/.claude/skills/` (or your agent's skills folder). Skills load on demand, so only each skill's name and description sit in context until it is needed.

### Use alongside the official Mastra skill

Mastra publishes an official skill at [mastra-ai/skills](https://github.com/mastra-ai/skills) (`npx skills add mastra-ai/skills`). It is one broad skill covering current docs lookup, the `mastra api` CLI, and Mastra Factory. This repo splits Mastra into focused per-feature skills. The two work well together.

## Contributing

Contributions are welcome, especially fixes for outdated APIs, docs that contradict each other, and better examples.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. The short version:

```bash
python3 -m pip install pyyaml
python3 scripts/validate_skills.py
python3 scripts/generate_catalog.py --write
```

Open an issue or a pull request on [GitHub](https://github.com/YGhorbel/awesome-mastra-skills).

---

## How a skill is built

```
skills/mastra-<feature>/
  SKILL.md              When to use / When NOT to use / Required inputs / The framework /
                        Workflow / Failure patterns / Output format / Reference files
  references/
    api.md              Exact options, signatures, defaults
    examples.md         Complete, runnable examples
    checklist.md        Build and production checklist
```

See [SKILL_AUTHORING.md](SKILL_AUTHORING.md) for the full conventions and [MAPPING.md](MAPPING.md) for which Mastra docs pages feed each skill.

---

## Catalog

<!-- CATALOG:START -->
**47 skills** across 11 categories.

### Getting started

| Skill | What it covers |
|---|---|
| [`mastra-guide`](skills/mastra-guide/SKILL.md) | Router: map any goal to the right Mastra feature and skill, plus the docs lookup protocol |
| [`mastra-project-setup`](skills/mastra-project-setup/SKILL.md) | create-mastra and manual install, tsconfig and ESM, src/mastra layout, the Mastra class config, env files, mastra dev and Studio |
| [`mastra-build-playbook`](skills/mastra-build-playbook/SKILL.md) | Idea to production in 9 phases: scope, scaffold, first slice, context, safety, evals, tracing, integrate, deploy |
| [`mastra-troubleshooting`](skills/mastra-troubleshooting/SKILL.md) | Diagnosis flow and fixes for ESM, tsconfig, model strings, env vars, outdated APIs, tools, storage, memory, client errors |
| [`mastra-migrations`](skills/mastra-migrations/SKILL.md) | v1 upgrade guide, codemods, AI SDK v5, supervisor agents, MCP v2, and Mastra Cloud to Platform migrations |

### Agents

| Skill | What it covers |
|---|---|
| [`mastra-agents`](skills/mastra-agents/SKILL.md) | Agent class, instructions, model strings, registration, generate and stream, dynamic config, fallbacks |
| [`mastra-tools`](skills/mastra-tools/SKILL.md) | createTool, schemas, execute context, hooks, client tools, built-in tools, code mode, and dynamic tool search |
| [`mastra-structured-output`](skills/mastra-structured-output/SKILL.md) | Typed agent output with structuredOutput, streaming objects, structuring models, prompt injection, and error strategies |
| [`mastra-processors-guardrails`](skills/mastra-processors-guardrails/SKILL.md) | Input, output, and error processors: built-in guardrails, custom processors, tripwires, retries, and caching |
| [`mastra-agent-approval-hitl`](skills/mastra-agent-approval-hitl/SKILL.md) | Tool approval, suspend and resume, auto-resume, listSuspendedRuns, and approvals through supervisor agents |
| [`mastra-multi-agent`](skills/mastra-multi-agent/SKILL.md) | Supervisor agents, subagents, delegation hooks, message filtering, rubric loops, and network() migration |
| [`mastra-agent-skills`](skills/mastra-agent-skills/SKILL.md) | Inline and filesystem skills for Mastra agents: createSkill, workspace skills, dynamic skill sets, getSkill and listSkills |
| [`mastra-file-based-agents`](skills/mastra-file-based-agents/SKILL.md) | Agents as directories: config.ts, instructions.md, tools/, skills/, subagents/, schedules/, and precedence rules |
| [`mastra-classifier`](skills/mastra-classifier/SKILL.md) | Typed choice, score, and boolean decisions with decision models, plus routing, guardrails, and model selection |
| [`mastra-streaming`](skills/mastra-streaming/SKILL.md) | Agent and workflow streaming: MastraModelOutput, chunk types, writer API, smoothStream, abort, and events |
| [`mastra-voice`](skills/mastra-voice/SKILL.md) | Voice for agents: speak, listen, realtime speech-to-speech, CompositeVoice, LiveKit, and every voice provider |

### Models

| Skill | What it covers |
|---|---|
| [`mastra-models`](skills/mastra-models/SKILL.md) | Model router strings, providers and env vars, gateways, custom gateways, fallbacks, provider options, embeddings |

### Workflows

| Skill | What it covers |
|---|---|
| [`mastra-workflows`](skills/mastra-workflows/SKILL.md) | createWorkflow and createStep, control flow, agents and tools as steps, state, retries, dynamic workflows, running and streaming |
| [`mastra-workflow-suspend-resume`](skills/mastra-workflow-suspend-resume/SKILL.md) | Suspend and resume, human-in-the-loop steps, snapshots, state reader, run status, restart, and time travel |

### Memory, RAG, and storage

| Skill | What it covers |
|---|---|
| [`mastra-memory`](skills/mastra-memory/SKILL.md) | Memory class, threads and resources, message history, working memory, multi-user threads, memory APIs |
| [`mastra-semantic-recall`](skills/mastra-semantic-recall/SKILL.md) | Semantic recall config: topK, messageRange, scope, filters, embedder and vector setup, tuning and cost |
| [`mastra-observational-memory`](skills/mastra-observational-memory/SKILL.md) | Observational memory: Observer and Reflector, thresholds, buffering, retrieval, models, limits, OM vs history vs recall |
| [`mastra-rag`](skills/mastra-rag/SKILL.md) | MDocument chunking, embeddings, vector upsert and query, filters, reranking, GraphRAG, and vector query tools |
| [`mastra-knowledge`](skills/mastra-knowledge/SKILL.md) | Scoped pages and notes agents search, read, write, and pin, with access roles and Studio browsing |
| [`mastra-storage`](skills/mastra-storage/SKILL.md) | Storage adapters, instance vs agent storage, composite domain routing, retention and pruning, provider table |
| [`mastra-vector-stores`](skills/mastra-vector-stores/SKILL.md) | Vector store adapters, common createIndex/upsert/query API, filters, index tuning, choosing a store |

### Harness: durable agents, schedules, signals

| Skill | What it covers |
|---|---|
| [`mastra-harness`](skills/mastra-harness/SKILL.md) | Durable agents, background tasks, goals, AgentController sessions, workers, and the coding agent factory |
| [`mastra-schedules`](skills/mastra-schedules/SKILL.md) | Persisted cron schedules for agents and workflows, threaded fires, hooks, pause and resume, and scheduler topology |
| [`mastra-signals`](skills/mastra-signals/SKILL.md) | Messages, typed and state signals, durable notifications, thread streams, signal providers, and cross-process leases |

### Workspaces, sandboxes, and browsers

| Skill | What it covers |
|---|---|
| [`mastra-workspace-sandbox`](skills/mastra-workspace-sandbox/SKILL.md) | Workspace class, filesystems, sandboxes, mounts, per-user isolation, tool policies, search, LSP, computer use, providers |
| [`mastra-browser`](skills/mastra-browser/SKILL.md) | Browser providers for agents: AgentBrowser, Stagehand, Firecrawl, BrowserViewer, scope, cookies, cloud CDP, screencast |

### Connections: MCP, A2A, ACP, channels, integrations

| Skill | What it covers |
|---|---|
| [`mastra-mcp`](skills/mastra-mcp/SKILL.md) | MCPClient and MCPServer: transports, static vs runtime toolsets, per-user auth, OAuth, approval, publishing MCP servers |
| [`mastra-a2a-acp`](skills/mastra-a2a-acp/SKILL.md) | Choose a connection; A2A remote agents and agent cards; ACP coding agents as subagents or tools; Claude, Cursor, OpenAI SDK agents |
| [`mastra-channels`](skills/mastra-channels/SKILL.md) | Agents in Slack, Teams, Discord, Telegram, WhatsApp, iMessage: adapters, webhooks, approvals, handlers, providers, serverless |
| [`mastra-tool-integrations`](skills/mastra-tool-integrations/SKILL.md) | Web tools (Tavily, Bright Data, Parallel, Perplexity, Firecrawl) and Mastra Connect tools, channels, and credentials |

### Server, client, frontend, and auth

| Skill | What it covers |
|---|---|
| [`mastra-server`](skills/mastra-server/SKILL.md) | Server config, built-in routes, custom routes, middleware, request context, server adapters, pub/sub |
| [`mastra-client-sdk`](skills/mastra-client-sdk/SKILL.md) | MastraClient for agents, workflows, memory, tools, vectors, traces, datasets, Responses API, agent controller |
| [`mastra-framework-integration`](skills/mastra-framework-integration/SKILL.md) | Add Mastra to Next.js, Vite, Astro, SvelteKit, Nuxt, Angular, Electron, Express, Hono, NestJS, TanStack Start |
| [`mastra-agentic-ui`](skills/mastra-agentic-ui/SKILL.md) | AI SDK UI routes and converters, useChat, tool and workflow rendering, assistant-ui, CopilotKit, OpenUI |
| [`mastra-auth`](skills/mastra-auth/SKILL.md) | Server and Studio auth: SimpleAuth, JWT, composite, custom providers, identity providers, RBAC, FGA, workers |

### Evals, observability, and Studio

| Skill | What it covers |
|---|---|
| [`mastra-evals`](skills/mastra-evals/SKILL.md) | Built-in and custom scorers, Quick Checks, createScorer pipeline, live scoring with sampling, runEvals, multi-turn and memory evals |
| [`mastra-datasets-experiments`](skills/mastra-datasets-experiments/SKILL.md) | Versioned datasets, experiments, comparisons, gates and verdicts, CI and Vitest integration, the eval loop |
| [`mastra-observability`](skills/mastra-observability/SKILL.md) | Tracing, exporters (Langfuse, Datadog, OTel, and more), sampling, custom spans, PinoLogger, metrics and cost, feedback |
| [`mastra-studio-editor`](skills/mastra-studio-editor/SKILL.md) | Studio (run, auth, deploy, observability and knowledge views) and the Editor (prompt blocks, tools, versioning) |

### Deployment, Mastra Platform, and CLI

| Skill | What it covers |
|---|---|
| [`mastra-deployment`](skills/mastra-deployment/SKILL.md) | Server build, cloud deployers, containers, Kubernetes, sandbox previews, workers, Inngest and Temporal runners |
| [`mastra-platform`](skills/mastra-platform/SKILL.md) | mastra deploy, environments, regions, hosted databases, GitHub deploys, workspaces, hosted observability, alerts |
| [`mastra-cli-api`](skills/mastra-cli-api/SKILL.md) | mastra CLI commands, plus mastra api for agents, workflows, tools, threads, traces, spans, logs, metrics |
<!-- CATALOG:END -->

---

## Repository structure

```
.claude-plugin/     plugin.json and marketplace.json for Claude Code
skills/             one folder per skill
scripts/
  validate_skills.py    structure and frontmatter checks
  generate_catalog.py   regenerates the catalog above
CONTRIBUTING.md     how to contribute
SKILL_AUTHORING.md  conventions every skill follows
MAPPING.md          skill to Mastra docs source map
```

## Acknowledgments

- Content is distilled from the [Mastra documentation](https://mastra.ai/docs) (`https://mastra.ai/llms.txt`).
- The `mastra-models` provider registry script and parts of the troubleshooting, CLI, and platform guidance are adapted from [mastra-ai/skills](https://github.com/mastra-ai/skills) (Apache-2.0).
- Repository structure and SKILL.md section conventions are inspired by [RampStack Claude Skills](https://github.com/rampstackco/claude-skills).

Not affiliated with or endorsed by Mastra.

## License

[Apache-2.0](LICENSE)
