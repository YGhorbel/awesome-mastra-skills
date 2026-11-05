---
name: mastra-knowledge
description: "Give Mastra agents a shared, scoped knowledge graph of pages and notes with the Knowledge class from @mastra/core/knowledge: declare scope types and access rules, set each run's scopes from server code, seed content with upsertPage and addNote, turn on the knowledge_search, knowledge_read, knowledge_page, knowledge_note, and knowledge_pin tools, pin pages into context every turn, and browse it in Studio. Use this skill whenever the user wants agents to share policies, runbooks, docs, or learned conventions across threads, agents, teams, or tenants, or wants one agent to serve many customers with per-org content. Triggers on Mastra Knowledge, new Knowledge, knowledgeMemoryScopes, scopes, MASTRA_SCOPES_KEY, explainAccess, upsertPage, addNote, pinnedContext, knowledge_search, knowledge_read, KNOWLEDGE_ROUTES, scope declarations, viewer contributor editor owner roles. Also triggers when the user asks how Knowledge differs from RAG or memory."
license: Apache-2.0
metadata:
  category: memory-and-knowledge
  catalog_summary: "Scoped pages and notes agents search, read, write, and pin, with access roles and Studio browsing"
  display_order: 5
  docs: https://mastra.ai/docs/knowledge/overview
---

# Mastra Knowledge

Set up a Knowledge instance so agents share curated pages and notes across conversations, with scopes and roles that decide what each run can read and change.

---

## When to use

- Agents must follow rules or policies you edit, without redeploying prompts
- One agent serves many customers or teams, each with its own content
- Agents should record decisions, conventions, or runbook notes for other agents and people
- Agents hand work to each other through shared pages
- You want a page (policy, conventions, a docs index) in the agent's context every turn
- Seeding product docs or policies into a store agents can browse and search
- Deciding between Knowledge, RAG, and memory

## When NOT to use

- Semantic search over a large document corpus you chunk and embed yourself (use `mastra-rag`)
- Conversation history, threads, and working memory for one user (use `mastra-memory`)
- Recalling older messages by meaning (use `mastra-semantic-recall`)
- Compressing long threads (use `mastra-observational-memory`)
- Server middleware, auth providers, and request context plumbing in general (use `mastra-server` and `mastra-auth`)
- The state-signal mechanics behind pinned pages (use `mastra-signals`)
- Studio features beyond the Knowledge page (use `mastra-studio-editor`)

---

## Required inputs

- The audiences: orgs, teams, users, tenants, sites, or repos that need separate content
- Who may read, add to, edit, or delete each kind of content (maps to roles)
- How the server knows the user (auth, org ID, team list) so it can set run scopes
- Whether the agent only reads (docs agent) or also writes (shared learning)
- Which pages must be in context every turn, and the token budget for them
- Storage adapter, and optionally a vector store plus embedder for search by meaning

Knowledge is alpha. Tell the user access checks are not yet a guaranteed isolation boundary. Do not store data that must never reach another customer.

---

## The framework: pages, notes, scopes, roles

- **Page**: a topic with `name`, short `description`, and Markdown `body`. Pages nest: `org:acme#policies/refund`.
- **Note**: a short attributed fact on a page (at most 250 tokens). Notes link to pages with `[[scope#path]]`.
- **Scope**: a separate area of the graph, addressed `<type>:<value>` (`org:acme`, `team:acme:support`). You declare the types.
- **Role**: `viewer` reads, `contributor` adds pages and notes, `editor` edits, moves within a scope, and pins, `owner` deletes, merges, and moves across scopes. Roles come from rules and are computed per tool call.
- **Run scopes**: the scopes one agent call holds. Only server code sets them, never the model or the request body.

```typescript
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { Knowledge, knowledgeMemoryScopes } from '@mastra/core/knowledge'
import { LibSQLStore } from '@mastra/libsql'
import { Memory } from '@mastra/memory'
import { KNOWLEDGE_ROUTES } from '@mastra/server/server-adapter'

const storage = new LibSQLStore({ id: 'storage', url: 'file:./mastra.db' })

export const knowledge = new Knowledge({
  id: 'company',
  storage,
  scopes: {
    ...knowledgeMemoryScopes(), // org:$orgId, resource:$resourceId, thread:$threadId
    'team:$orgId:$teamId': {
      description: 'A team',
      belongsTo: 'org:$orgId',
      access: [
        { principal: 'self', role: 'editor' },
        { principal: 'org:$orgId', role: 'viewer' },
      ],
    },
  },
  tools: true, // off by default
})

export const agent = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'You help your team and keep its knowledge up to date.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ storage }),
  knowledge,
})

export const mastra = new Mastra({
  agents: { agent },
  knowledge: { company: knowledge },
  server: { apiRoutes: [...KNOWLEDGE_ROUTES] }, // Studio browsing
})

await agent.generate('Our refund window is 30 days. Save that for the team.', {
  scopes: ['org:acme', 'resource:dana', 'thread:dana-1'],
})
```

### Knowledge vs RAG vs memory

| | `mastra-knowledge` | `mastra-rag` | `mastra-memory` |
|---|---|---|---|
| Unit | Curated pages and attributed notes | Embedded chunks of your documents | Messages in one thread |
| Who writes | Agents, people, and host seeding | Your ingestion pipeline | The conversation |
| Shared across | Threads, agents, users in a scope | Whoever queries the index | One resource and thread |
| Access control | Declared scopes and roles per tool call | Your filters or tenant stores | Resource and thread ownership |
| Search | Keyword, plus meaning with `vector` + `embedder` | Vector similarity, filters, rerank | Recency, semantic recall |
| Always in context | Pinned pages via state signals | No | Working memory, recent messages |

Use RAG for large static corpora. Use Knowledge when content is curated, changes, is written by agents, or needs per-audience access.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Knowledge` types. Otherwise fetch `https://mastra.ai/docs/knowledge/overview.md`, `https://mastra.ai/reference/knowledge/knowledge-class.md`, and `https://mastra.ai/reference/knowledge/scope-declarations.md`. Knowledge is alpha. Trust these over memory.
2. **Model the audiences as scope types.** Spread `knowledgeMemoryScopes()` (rename the tenant with `{ org: 'tenant:$tenantId' }`). Add one pattern per content area (`policy:$orgId`, `docs:$orgId`, `team:$orgId:$teamId`). Patterns of one type must not overlap.
3. **Write access rules.** For each type, list `{ principal, role }`. `self` is the scope being accessed. Bind principal params from the address prefix or through `belongsTo`. Roles never inherit or chain.
4. **Choose tools.** `tools: true` for read and write, `tools: { read: true }` for read-only agents. Raise `read.maxTokens` for large-context models.
5. **Attach to agents** with `knowledge`, or wire `knowledge.createTools(opts)` plus `knowledge.getInstructions(opts)` with identical options.
6. **Set run scopes in server code.** In middleware, set `MASTRA_SCOPES_KEY` (and `MASTRA_RESOURCE_ID_KEY`) on `requestContext`. In direct calls, pass `scopes`. Use an agent-level `scopes` function to narrow access for one agent.
7. **Seed content** from trusted host code with `upsertPage()`. Re-run seeds freely. Use `addNote()` once per fact.
8. **Pin what must always be visible.** Set `pinnedContext` on the instance (needs Memory on the agent), then list page paths or `{ list, depth }` in a scope declaration.
9. **Add search by meaning** with `vector` and `embedder` together, before writing content.
10. **Test access** with `explainAccess()` in unit tests. Register on Mastra with `KNOWLEDGE_ROUTES` and check the Studio Knowledge page.

---

## Deep dive: run scopes from the server

```typescript
import { Mastra } from '@mastra/core/mastra'
import { MASTRA_RESOURCE_ID_KEY, MASTRA_SCOPES_KEY } from '@mastra/core/request-context'

export const mastra = new Mastra({
  agents: { support },
  server: {
    middleware: [
      async (c, next) => {
        const user = await getUser(c.req.header('Authorization')) // your auth lookup
        const requestContext = c.get('requestContext')
        requestContext.set(MASTRA_SCOPES_KEY, [
          `org:${user.orgId}`,
          ...user.teams.map(team => `team:${user.orgId}:${team}`),
          `resource:${user.id}`,
        ])
        requestContext.set(MASTRA_RESOURCE_ID_KEY, user.id)
        await next()
      },
    ],
  },
})
```

Rules a run must satisfy:

- Every run scope matches a declared type, even one that only names a role (`'role:$orgId:support': {}`).
- At most one `resource:` and one `thread:` scope. A `resource:` scope must equal `memory.resource`.
- Pass raw IDs. Knowledge encodes them.
- An agent `scopes` function must return every `resource:` and `thread:` scope it receives.

---

## Failure patterns

- **`Knowledge needs scopes` at construction.** Pass `scopes`, at least `{ ...knowledgeMemoryScopes() }` or `{}`.
- **`Knowledge tools need run scopes`.** The run has no scopes and no Memory. Pass `scopes` on the call or set `MASTRA_SCOPES_KEY` in middleware.
- **`run scope ... does not match a declared scope type`.** Declare every type the server passes.
- **Agent has Knowledge but no tools.** `tools` defaults to `false`. Set `tools: true` or `{ read: true }`.
- **Pinned pages never appear.** The instance lacks `pinnedContext`, the agent has no Memory, the page has no body yet, or the run cannot read the page.
- **Overlapping patterns** (`kb:$orgId` and `kb:$orgId:public`) fail at startup. Use two types.
- **Expecting inheritance.** A role on `org:acme` grants nothing on scopes under it unless a rule says so.
- **Seed run twice duplicates notes.** `upsertPage()` is idempotent. `addNote()` is not. Use `updateNote()`.
- **Exposing host methods.** `upsertPage`, `addNote`, `removePage`, and `explainAccess` skip access checks. Never wrap them in an agent tool or an unauthenticated route.
- **Renaming a scope key** makes the instance refuse to run. Call `renameScopeDeclaration(from, to)` right after deploying.
- **Switching embedders** on existing content gives keyword-only or poor matches. Knowledge cannot re-embed yet.
- **Studio shows everything to everyone.** Without `server.auth` or `studio.auth`, routes read as owner. Set `MASTRA_KNOWLEDGE_PRINCIPALS_KEY` in `authorize`.

---

## Output format

A finished Knowledge delivery contains:

- `src/mastra/knowledge.ts` exporting the `Knowledge` instance with scope declarations and tool settings
- Agents with `knowledge` attached (and Memory when pins are used)
- Server middleware or call sites that set run scopes from authenticated identity
- A seed script using `upsertPage()` for preloaded content
- Registration on `new Mastra({ knowledge: { ... } })` with `KNOWLEDGE_ROUTES`, plus auth mapping if deployed
- `explainAccess()` tests covering each access rule

---

## Reference files

- [`references/api.md`](references/api.md) - Constructor options, scope declaration fields, roles, host methods, tools and their arguments, limits.
- [`references/examples.md`](references/examples.md) - Docs agent, multi-tenant support agent, pinned policy, access tests, Studio auth.
- [`references/checklist.md`](references/checklist.md) - Scope design, access, and deployment checklist.

**Live docs**

- https://mastra.ai/docs/knowledge/overview
- https://mastra.ai/docs/knowledge/scopes-and-access
- https://mastra.ai/docs/knowledge/agents-and-tools
- https://mastra.ai/docs/knowledge/pinned-context
- https://mastra.ai/docs/knowledge/search
- https://mastra.ai/docs/knowledge/load-your-content
- https://mastra.ai/docs/knowledge/patterns
- https://mastra.ai/docs/studio/knowledge
- https://mastra.ai/reference/knowledge/knowledge-class
- https://mastra.ai/reference/knowledge/scope-declarations
- https://mastra.ai/reference/knowledge/knowledge-tools
