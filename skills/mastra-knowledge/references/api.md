# Knowledge API reference

Distilled from `https://mastra.ai/reference/knowledge/*.md`. Knowledge is alpha (added in `@mastra/core@1.82.0`). Verify against the installed version.

## Contents

- Constructor options
- knowledgeMemoryScopes() and knowledgeScopeAddress()
- Scope declaration fields
- Roles and operations
- Instance methods
- Tools
- Run scope sources and errors
- Studio routes and auth
- Limits

---

## Constructor options: `new Knowledge({...})`

Import: `import { Knowledge, knowledgeMemoryScopes } from '@mastra/core/knowledge'`

| Option | Type | Default | Notes |
|---|---|---|---|
| `scopes` | `KnowledgeScopeDeclarations` | required | Keyed by pattern (`team:$orgId:$teamId`) or concrete address (`org:acme`). `{}` declares none. |
| `id` | `string` | random | |
| `name` | `string` | `id` | Logs |
| `description` | `string` | | Not used by agents yet |
| `storage` | `MastraCompositeStore` | Mastra storage | |
| `tools` | `boolean \| { read?: boolean \| { maxTokens? }; write?: boolean }` | `false` | `true` gives list, search, read, page, note. `read.maxTokens` default 1,000, min 100. |
| `pinnedContext` | `boolean \| { maxPins?, maxTokens? }` | `false` | Adds `knowledge_pin`. Defaults 20 pins, 500 tokens. Needs Memory. |
| `vector` | `MastraVector` | | Pass with `embedder`, else throws |
| `embedder` | `MastraEmbeddingModel<string>` | | Pass with `vector` |
| `embedderOptions` | `MastraEmbeddingOptions` | | `maxRetries`, `headers`, `providerOptions`, `telemetry` |
| `instructions` | `false \| string \| ({ read, write, pins }) => string` | built-in | Function must be deterministic for prompt caching |

Throws `KnowledgeDeclarationError` for missing `scopes` or invalid declarations.

Agent options: `knowledge` (attach) and `scopes` (`string[]` adds, or `({ scopes }) => string[]` replaces). Call option: `scopes: string[]`.

Mastra options: `knowledge: { key: instance }`.

---

## knowledgeMemoryScopes() and knowledgeScopeAddress()

```typescript
knowledgeMemoryScopes({ org?: string | false, orgRole?: 'editor' | 'contributor' })
```

| Key | Access | belongsTo | pinnedContextPriority |
|---|---|---|---|
| `thread:$threadId` | self owner | `resource:$resourceId` | 2 |
| `resource:$resourceId` | self owner | `org:$orgId` | 1 |
| `org:$orgId` (default `org`) | self `orgRole` (default editor) | none | 0 |

`org: false` drops the tenant row. `orgRole: 'contributor'` makes the tenant append-only.

`knowledgeScopeAddress(pattern, params)` builds an encoded address for host APIs. Do not pass it as an agent scope (agents take raw IDs).

---

## Scope declaration fields

| Field | Notes |
|---|---|
| `access` | `{ principal: 'self' \| pattern, role }[]` |
| `description` | Read by the model |
| `displayLabel` | UI only. `$params` fill in. |
| `belongsTo` | Parent pattern in the tree. Grants nothing alone. Patterns only. |
| `children` | `{ name, description?, displayLabel?, access? }[]` created at `<address>/<name>`. No inherited rules. |
| `pages` | Template pages `{ key, name, description?, pages? }`. Cannot be moved or merged away by tools. |
| `pinnedContext` | `(string \| { list, depth? })[]` page paths or listings pinned for runs holding this scope |
| `pinnedContextPriority` | Default `0`, highest first |

Pattern rules:

- Type is text before the first `:`. `$name` segments are params. The last param takes the rest of the value.
- Patterns of one type must be pairwise disjoint.
- Principal params bind from the target address prefix or through `belongsTo`. Other bindings fail at startup.
- A concrete address (no params) adds `description`, `displayLabel`, `access`, `pinnedContext`, `pinnedContextPriority` to its pattern. Declare the pattern first.
- `belongsTo` placement happens on the first writing run that holds exactly one matching parent scope, then sticks.

---

## Roles and operations

| Operation | Role | On |
|---|---|---|
| Search, read, list | viewer | Page's scope |
| Create page | contributor | Target scope |
| Edit page, move within scope | editor | Page's scope |
| Move to another scope | owner | Both scopes |
| Merge | owner on page that goes, editor (same scope) or owner (other scope) on page that stays | |
| Delete page | owner | Page's scope |
| Add note | contributor | Page's scope and each stamp |
| Restamp, remove note | editor | Page's scope, contributor on new stamps |
| Pin, unpin | editor | Page's scope, plus holding or editor on each audience scope |

Note visibility: a run sees a note when it can read the page and at least one stamp scope (and every linked page's scope).

---

## Instance methods

| Method | Notes |
|---|---|
| `createTools({ read?, write?, pinnedContext? })` | Returns tools for manual wiring |
| `getInstructions({ read?, write?, pinnedContext? })` | Matching instruction block |
| `explainAccess(runScopes, { scope } \| { page })` | `{ role, reasons, page?, reason? }`. Host-only. `reason`: `missing`, `hidden`, `no-rule`. |
| `readScopeFor(principals)` | Read scope for store reads |
| `scopeGrants({ address, parentAddress? })` | Roles other scopes have on this one |
| `scopeDeclaration(key)` | Display info |
| `scopeLabel(address)` | Resolved `displayLabel` |
| `upsertPage({ scope, path, name, description?, body?, author? })` | `{ page, status: 'created' \| 'updated' \| 'unchanged' }`. Creates missing scope and parents. Host-only. |
| `removePage({ scope, path, author? })` | Throws with children or for template pages |
| `addNote({ scope, path, text, when?, stamps?, author? })` | Not idempotent. Throws `KnowledgeNotFoundError` if no page. |
| `updateNote({ id, text, when?, stamps?, author? })` | Adds new note, removes old. New ID. |
| `removeNote({ id, author? })` | |
| `getStorage()` | Store for admin code. Pass `read` from `readScopeFor()`. |
| `reindexLinks()` | Rebuild link index |
| `renameScopeDeclaration(from, to)` | Move stored scopes to a renamed key |
| `onChange(listener)` | Events `scope`, `page`, `note`, `pin` with IDs only. Returns unsubscribe. |
| `pinnedContextEnabled` | boolean property |

`author` defaults to `host`.

---

## Tools

| Group | Tools | Enabled by |
|---|---|---|
| Read | `knowledge_list`, `knowledge_search`, `knowledge_read` | `tools: true` or `{ read: true }` |
| Write | `knowledge_page`, `knowledge_note` | `tools: true` or `{ write: true }` |
| Pins | `knowledge_pin` | `pinnedContext` |

Page references accept a page ID, a scope address, a path `<scope>#<key>/<key>`, or an exact page name.

| Tool | Key arguments |
|---|---|
| `knowledge_search` | `query`, `scope?: string[]`, `limit` (1 to 50, default 10) |
| `knowledge_list` | `from`, `depth` (1 to 3), `limit` (1 to 100, default 50), `descriptions`, `cursor` |
| `knowledge_read` | `page`, `outline`, `section`, `match` (up to 10 terms), `context` (0 to 20, default 2), `from: { line, col? }`, `notes`, `mentionedIn`, `cursor`, `limit` |
| `knowledge_page` | `op: 'write' \| 'move' \| 'merge' \| 'delete'`, `page`, `scope`, `parent`, `into`, `key`, `name`, `description`, `body`, `range`, `expectedVersion` |
| `knowledge_note` | `op: 'add' \| 'restamp' \| 'remove'`, `page`, `note`, `scope: string[]`, `text`, `when` |
| `knowledge_pin` | `op: 'pin' \| 'unpin'`, `page`, `audience: string[]`, `kind: 'page' \| 'list'`, `depth` |

Tool errors return to the model as tool results. Hidden pages look missing.

Keyword ranking: whole-query name matches, then pages by word count and position (name, description, body), then notes. With `vector` and `embedder`, keyword and semantic results merge by rank (at most 1,000 semantic candidates).

---

## Run scope sources and errors

Sources: `MASTRA_SCOPES_KEY` on request context (reserved, ignored in request bodies), call `scopes`, agent `scopes`. With Memory, the run also holds `resource:<id>` and `thread:<id>`.

| Error | Cause |
|---|---|
| `Knowledge run scope "x" does not match a declared scope type` | Undeclared type |
| `Knowledge tools need run scopes` | No scopes and no Memory |
| `Invalid agent scope "Org:acme"` | Type must be lowercase `<type>:<value>` |
| `The agent's scopes function dropped "resource:dana"` | Function removed a memory scope |
| `Agent scopes contain more than one resource` | Two `resource:` or `thread:` scopes |
| `conflicts with option "memory.resource"` | `resource:` differs from `memory.resource` |
| `AGENT_SCOPES_SERVER_OUTDATED` | `@mastra/server` too old |

---

## Studio routes and auth

- Import `KNOWLEDGE_ROUTES` and `MASTRA_KNOWLEDGE_PRINCIPALS_KEY` from `@mastra/server/server-adapter`.
- Routes mount under `/api/knowledge` and need `@mastra/core` 1.81.0 or later.
- Without auth, routes read as owner for anyone. With auth, set `MASTRA_KNOWLEDGE_PRINCIPALS_KEY` to scopes or `'all'` in `authorize`. Otherwise routes return 403.
- With an FGA provider, each instance is checked with `knowledge:read`.
- The NestJS adapter does not serve these routes yet.

---

## Limits

| Item | Limit |
|---|---|
| Note text | 250 tokens |
| Page description | 100 tokens |
| Page nesting | 10 levels |
| Pages per move | 500 |
| Search results, notes per read | 10 default, 50 max |
| Read body or match result | 1,000 tokens default, 100 min |
| `knowledge_list` entries | 50 default, 100 max |
| List and listing depth | 1 default, 3 max |
| Embedding chunks per page | 100, about 2,000 tokens each |
| Pinned context | 500 tokens, 20 pins by default |
