# Docs and API lookup protocol

Mastra changes fast. Look up the current API before writing code, in this order.

## Contents

1. Embedded docs (installed packages)
2. Installed type definitions
3. Remote docs (llms.txt and Markdown pages)
4. Docs site map
5. Package map

---

## 1. Embedded docs (installed packages)

Most `@mastra/*` packages ship docs that match the installed version exactly.

```bash
ls node_modules/@mastra/                              # which packages are installed
cat node_modules/@mastra/core/dist/docs/SKILL.md      # package overview and exports
ls node_modules/@mastra/core/dist/docs/references/    # topic docs, named <category>-<topic>.md
grep -rl "createWorkflow" node_modules/@mastra/core/dist/docs/references
```

Check the installed version: `npm ls @mastra/core` (or read `node_modules/@mastra/core/package.json`).

## 2. Installed type definitions

When docs do not answer the question, read the types. `SOURCE_MAP.json` maps each export to its files.

```bash
grep '"Agent"' node_modules/@mastra/core/dist/docs/assets/SOURCE_MAP.json
cat node_modules/@mastra/core/dist/agent/agent.d.ts
```

Types are the source of truth for constructor options and method signatures in the installed version.

## 3. Remote docs

Use when packages are not installed, or to explore features newer than the installed version (then check compatibility before adopting).

- Full page index: `https://mastra.ai/llms.txt`
- Any page as Markdown: append `.md` to its URL, for example `https://mastra.ai/reference/agents/agent.md`
- Section index example: `https://mastra.ai/docs/llms.txt`

```bash
curl -sL https://mastra.ai/llms.txt | grep -i "observational"
curl -sL https://mastra.ai/docs/memory/observational-memory.md
```

Remote docs may be ahead of the installed version. If an option is missing from the installed types, upgrade (`mastra-migrations`) or use the older API.

## 4. Docs site map

| Area | URL prefix | Holds |
|---|---|---|
| Docs | `/docs/...` | Concepts, how-to, guides |
| Reference | `/reference/...` | Exact options, signatures, defaults |
| Models | `/models/...` | Providers, model IDs, env vars, gateways, embeddings |
| Integrations | `/integrations/...` | Databases, vectors, deploy targets, frameworks, auth, voice, sandboxes, observability exporters, channels, browsers, agentic UI |
| Platform | `/docs/mastra-platform/...` | Mastra Platform deploy, environments, Connect |
| Guides | `/docs/guides/...` | Multi-agent, context engineering, lifecycle, streaming, auth, eval loop |

## 5. Package map

Most imported packages across the current docs. Import subpaths exactly as shown.

| Import | Holds | Skill |
|---|---|---|
| `@mastra/core` | `Mastra` class | `mastra-project-setup` |
| `@mastra/core/agent` | `Agent` | `mastra-agents` |
| `@mastra/core/tools` | `createTool`, built-in tools | `mastra-tools` |
| `@mastra/core/workflows` | `createWorkflow`, `createStep` | `mastra-workflows` |
| `@mastra/core/processors` | Processors and guardrails | `mastra-processors-guardrails` |
| `@mastra/core/request-context` | `RequestContext` | `mastra-agents`, `mastra-server` |
| `@mastra/core/workspace` | Workspace, filesystem, sandbox | `mastra-workspace-sandbox` |
| `@mastra/core/evals` | Scorer APIs | `mastra-evals` |
| `@mastra/core/signals` | Signals, `TaskSignalProvider` | `mastra-signals` |
| `@mastra/core/knowledge` | Knowledge | `mastra-knowledge` |
| `@mastra/core/classifier` | Classifier | `mastra-classifier` |
| `@mastra/core/voice` | Voice base classes | `mastra-voice` |
| `@mastra/core/server` | Custom API routes | `mastra-server` |
| `@mastra/memory` | `Memory` | `mastra-memory` |
| `@mastra/rag` | `MDocument`, retrieval tools | `mastra-rag` |
| `@mastra/libsql`, `@mastra/pg`, `@mastra/mongodb`, ... | Storage and vector adapters | `mastra-storage`, `mastra-vector-stores` |
| `@mastra/observability`, `@mastra/loggers` | Tracing, logging | `mastra-observability` |
| `@mastra/mcp` | `MCPClient`, `MCPServer` | `mastra-mcp` |
| `@mastra/client-js` | `MastraClient` | `mastra-client-sdk` |
| `@mastra/ai-sdk` | AI SDK routes and converters | `mastra-agentic-ui` |
| `@mastra/editor` | `MastraEditor` | `mastra-studio-editor` |
| `@mastra/auth`, `@mastra/auth-*` | Auth providers | `mastra-auth` |
| `@mastra/connect` | Platform Connect | `mastra-tool-integrations` |
| `@mastra/acp` | ACP | `mastra-a2a-acp` |
| `@mastra/inngest` | Inngest workflow runner | `mastra-deployment` |
| `mastra` (CLI) | `mastra dev`, `build`, `api`, `deploy` | `mastra-cli-api` |
