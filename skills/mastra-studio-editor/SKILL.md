---
name: mastra-studio-editor
description: "Run, secure, and deploy Mastra Studio, the local and hosted UI for chatting with agents, running workflows and tools, reviewing traces, logs, metrics, scores, datasets, experiments, and knowledge, and set up the Mastra Editor so non-developers can change agent instructions, tools, and prompt blocks with drafts, publishing, and version selection. Use this skill whenever the user wants to open or configure Studio, put Studio behind login or RBAC, host Studio standalone or alongside the server, let a team edit prompts without a deploy, reuse prompt blocks, or pin agents to a draft or published version. Triggers on mastra dev, localhost:4111, mastra studio, mastra build --studio, MASTRA_STUDIO_PATH, Studio auth, StaticRBACProvider, @mastra/editor, MastraEditor, mastra.getEditor, prompt blocks, prompt_block_ref, editor field on Agent, ComposioToolProvider, getAgentById status draft, KNOWLEDGE_ROUTES. Also triggers when a product or support team wants to tune an agent without touching code."
license: Apache-2.0
metadata:
  category: quality
  catalog_summary: "Studio (run, auth, deploy, observability and knowledge views) and the Editor (prompt blocks, tools, versioning)"
  display_order: 4
  docs: https://mastra.ai/docs/studio/overview
---

# Mastra Studio and Editor

Use Studio to build, test, and observe a Mastra app, secure and deploy it for a team, and add the Editor so collaborators can change agents without code.

---

## When to use

- Starting Studio locally and knowing what each section does
- Testing agents, workflows, tools, processors, MCP servers, and request context in the UI
- Reviewing traces, logs, metrics, scores, datasets, and experiments in Studio
- Adding login, roles, or permissions to a shared Studio
- Deploying Studio standalone, alongside the server, or as a static SPA
- Enabling the Knowledge browser
- Letting non-developers edit instructions, tools, and prompt blocks with draft and publish
- Selecting a published, draft, or exact agent version per request

## When NOT to use

- Configuring tracing, exporters, logging, metrics (use `mastra-observability`)
- Writing scorers (use `mastra-evals`) or building datasets and experiments in code (use `mastra-datasets-experiments`)
- Auth providers in depth (use `mastra-auth`)
- Hosted Studio on Mastra platform (use `mastra-platform`)
- Deploying the Mastra server itself (use `mastra-deployment`)
- Knowledge scopes, pages, and APIs (use `mastra-knowledge`)
- Defining agents in code (use `mastra-agents`) or file-based agents (use `mastra-file-based-agents`)
- Connect tool integrations (use `mastra-tool-integrations`)

---

## Required inputs

- Who uses Studio: only developers locally, or a team on a shared deployment
- Where it runs: `mastra dev`, standalone `mastra studio`, alongside the server, a CDN, or Mastra platform
- Auth provider and the roles each person needs
- For Editor: which agent fields collaborators may own (instructions, tools, tool descriptions, model)
- Where Editor changes live: database (default) or JSON files in the repo
- Which tool sources collaborators may pick from (project tools, Composio, Arcade, MCP)

---

## The framework: Studio surfaces and Editor ownership

Studio is a React SPA talking to a Mastra server. `mastra dev` serves both: UI at `http://localhost:4111`, REST explorer at `http://localhost:4111/swagger-ui`.

| Section | What it does | Needs |
|---|---|---|
| Agents | Chat, switch models, tweak settings, Models panel, Editor | Registered agents |
| Workflows | Graph view, step-by-step runs, Resource ID run option | Registered workflows |
| Tools, Processors, MCP servers, Workspaces | Run tools alone, inspect processors, browse files and skills | Registered on `Mastra` |
| Request context | JSON or schema form that flows into instructions and tools | `requestContextSchema` for the form |
| Scorers, Datasets, Experiments | Score results, CSV/JSON import, version compare, experiment compare | `storage`, registered scorers |
| Observability | Metrics, Traces, Logs | Observability storage (metrics need DuckDB, ClickHouse, or `PostgresStoreVNext`) |
| Knowledge | Read-only tree, graph, page, activity, search | `KNOWLEDGE_ROUTES` (`@mastra/core` 1.81.0+) |
| Settings | Instance URL, API prefix, custom headers, theme | none |

Editor works like a CMS for code-defined agents. The agent's `editor` field decides ownership:

```typescript
import { Agent } from '@mastra/core/agent'
import { searchOrders } from './tools/search-orders'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support agent',
  model: 'openai/gpt-6.1-sol',
  tools: { searchOrders },
  editor: {
    instructions: true, // Studio owns instructions: omit them from code
    tools: { description: true }, // collaborators only rewrite tool descriptions
  },
})
```

| `editor` value | Collaborators can change | Code must provide |
|---|---|---|
| Omitted | Instructions, tools, tool descriptions | `instructions` |
| `false` | Nothing | `instructions` |
| `{ instructions: true }` | Instructions | No `instructions` |
| `{ tools: true }` | Tools and descriptions | `instructions`, no `tools` |
| `{ tools: { description: true } }` | Descriptions of code tools | `instructions` and the tools |
| `{ model: true }` | A static fallback list | Static model array with stable entry `id`s |

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/editor/dist/docs/`, `node_modules/@mastra/core/dist/docs/`, and the installed types. Otherwise fetch `https://mastra.ai/docs/studio/overview.md`, `https://mastra.ai/docs/studio/editor.md`, and `https://mastra.ai/reference/editor/mastra-editor.md`. Trust these over memory.
2. **Run Studio.** `npm run dev` (or `npx mastra dev`). Change host and port through `server` in `src/mastra/index.ts`. Use `mastra dev --https` for local HTTPS.
3. **Register everything** you want visible: agents, workflows, tools, scorers, MCP servers on `new Mastra({...})`.
4. **Add storage and observability** so threads, scores, datasets, and traces persist (see `mastra-observability`).
5. **Secure before sharing.** Set `server.auth` (one config covers Studio and API). Add `server.rbac` with `StaticRBACProvider`. Production SSO, RBAC, and FGA need an EE license.
6. **Deploy.** Choose: Mastra platform, `mastra studio` standalone (port 3000), `mastra build --studio` plus `MASTRA_STUDIO_PATH`, or a Vite SPA build.
7. **Add Editor.** `npm install @mastra/editor`, then `editor: new MastraEditor()` with storage. Set `editor` on agents to hand fields to Studio.
8. **Expose tools to collaborators.** Register project tools on `Mastra.tools`, add `toolProviders` (Composio, Arcade), or let them create MCP clients.
9. **Ship changes through versions.** Save drafts, test, publish. Select versions in code with `mastra.getAgentById(id, { status | versionId })`.
10. **Script changes** with `mastra.getEditor()` when bulk edits or eval-driven tuning are needed.

---

## Deep dive: versions and prompt blocks

```typescript
const live = await mastra.getAgentById('support-agent', { status: 'published' })
const draft = await mastra.getAgentById('support-agent', { status: 'draft' })
const pinned = await mastra.getAgentById('support-agent', { versionId: 'abc-123' })

const editor = mastra.getEditor()!
await editor.prompt.create({
  id: 'brand-voice',
  name: 'Brand voice',
  content: 'Write in a friendly, concise tone. Address the user as {{userName || "there"}}.',
})
await editor.agent.update({
  id: 'support-agent',
  instructions: [
    { type: 'prompt_block_ref', id: 'brand-voice' },
    { type: 'text', content: 'Answer only questions about Acme products.' },
  ],
}) // creates an inactive draft
```

`update()` never publishes by itself. Publish with `editor.agent.update({ id, status: 'published', activeVersionId })`, or `PATCH /api/stored/agents/:id` with `autoPublish: true`. Referenced prompt blocks resolve to their published version at runtime and to drafts in previews.

---

## Failure patterns

- **Studio left public.** Without `server.auth`, Studio and every API route are open. Add auth before deploying.
- **Agent fails with Studio-owned instructions.** `editor.instructions: true` fails closed until a version with instructions is published. Publish one in Studio first.
- **TypeScript error on `instructions` or `tools`.** The field is handed to Studio. Remove it from code.
- **Editor edit not visible in production.** It is still a draft. Publish, or request `status: 'draft'` on purpose.
- **Expecting Models panel edits to persist.** Without `editor: { model: true }` they change only the running server's memory.
- **Model editing on a function-valued model.** Not supported. Use a static array with stable `id`s.
- **Knowledge page says browsing is not enabled.** Add `server: { apiRoutes: [...KNOWLEDGE_ROUTES] }` and register `knowledge` on `Mastra`.
- **Knowledge returns 403 with auth.** Set `MASTRA_KNOWLEDGE_PRINCIPALS_KEY` in `authorize` for `/api/knowledge` paths, and keep the app's decision for other paths.
- **Studio under a subpath shows a blank page.** Set `MASTRA_STUDIO_BASE_PATH` before `mastra studio`.
- **Copying built Studio assets straight to a CDN.** They need runtime config. Use the Vite SPA build with `%%PLACEHOLDER%%` replacement.
- **`auth_header` URL tokens in logs.** The token rides in the URL. Generate and transmit those links carefully.
- **No metrics or token columns.** The observability store lacks metrics support (see `mastra-observability`).

---

## Output format

A finished Studio or Editor delivery contains:

- Updated `src/mastra/index.ts` with `server.auth`, optional `server.rbac`, `storage`, and `editor: new MastraEditor({...})`
- Agents with an explicit `editor` field stating what collaborators own
- Deployment instructions for the chosen mode, with env vars (`MASTRA_STUDIO_PATH`, `MASTRA_STUDIO_BASE_PATH`, provider keys)
- Tool provider keys (`COMPOSIO_API_KEY`, `ARCADE_API_KEY`) in `.env.example`
- A release note on how drafts are tested and who publishes

---

## Reference files

- [`references/api.md`](references/api.md) - Studio sections, auth and RBAC, deployment env vars, `MastraEditor` options and namespaces, prompt blocks, versioning, REST routes.
- [`references/examples.md`](references/examples.md) - Team Studio with RBAC, Studio with the server, Editor with repo files, prompt block fallback, sub-agent versions.
- [`references/checklist.md`](references/checklist.md) - Studio deployment and Editor rollout checklist.

**Live docs**

- https://mastra.ai/docs/studio/overview
- https://mastra.ai/docs/studio/auth
- https://mastra.ai/docs/studio/deployment
- https://mastra.ai/docs/studio/observability
- https://mastra.ai/docs/studio/knowledge
- https://mastra.ai/docs/studio/editor
- https://mastra.ai/reference/editor/mastra-editor
- https://mastra.ai/reference/editor/prompt-blocks
- https://mastra.ai/reference/editor/versioning
