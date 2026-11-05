# Studio and Editor API reference

Distilled from `https://mastra.ai/docs/studio/*.md` and `https://mastra.ai/reference/editor/*.md`. Verify against the installed version.

## Contents

- Running Studio
- Studio auth and RBAC
- Deployment modes and env vars
- Knowledge routes
- MastraEditor constructor
- Editor namespaces
- Tool providers
- Prompt blocks
- Versioning and REST routes

---

## Running Studio

| Command | Result |
|---|---|
| `npm run dev` / `npx mastra dev` | Server plus Studio at `http://localhost:4111`, Swagger at `/swagger-ui` |
| `mastra dev --https` | Generates a localhost certificate |
| `mastra studio` | Standalone static UI at `http://localhost:3000`, connects to `http://localhost:4111` by default |
| `mastra build --studio` | Writes `.mastra/output/studio` |

Change host and port with `server` in `new Mastra({...})`. Settings page: Mastra instance URL, API prefix (default `/api`), custom headers, theme.

## Studio auth and RBAC

| Setting | Import | Notes |
|---|---|---|
| `server.auth` | for example `SimpleAuth` from `@mastra/core/server` | Gates Studio UI and all API routes. Studio reads `GET /api/auth/capabilities`. |
| `server.rbac` | `StaticRBACProvider`, `DEFAULT_ROLES` from `@mastra/core/auth/ee` | `{ roles, getUserRoles }` or `{ roleMapping, getUserRoles }`. |
| `studio.auth` | | When set, Studio requests use it instead of `server.auth`. |

Default roles: `owner` (`*`), `admin` (no delete), `member` (read, execute), `viewer` (read). Permission format `{resource}:{action}[:{id}]`, for example `agents:execute`, `*:read`, `agents:read:my-id`. Resources include `agents`, `workflows`, `tools`, `datasets`, `memory`, `scores`, `observability`. Actions: `read`, `write`, `create`, `delete`, `execute`, `publish`, `share`.

URL token handoff: `https://host/?auth_header=Bearer%20<token>` sets the `Authorization` header for the session (memory only).

Production SSO login, RBAC, and FGA require a Mastra EE license. Simple Auth, JWT, and API route auth do not. On Mastra platform, platform auth gates Studio unless `MASTRA_PLATFORM_STUDIO_AUTH=disabled`.

## Deployment modes and env vars

| Mode | How |
|---|---|
| Mastra platform | Hosted Studio (see `mastra-platform`) |
| Standalone | `npm install -g mastra`, `mastra studio`. Subpath: `MASTRA_STUDIO_BASE_PATH=/agents mastra studio` |
| With the server | `mastra build --studio`, then `MASTRA_STUDIO_PATH=.mastra/output/studio node .mastra/output/index.mjs` |
| Vercel | `VercelDeployer` can deploy Studio with the function |
| Static SPA | Vite build that copies `node_modules/mastra/dist/studio` and replaces `%%KEY%%` placeholders |

SPA env vars: `MASTRA_SERVER_HOST`, `MASTRA_SERVER_PORT`, `MASTRA_SERVER_PROTOCOL`, `MASTRA_API_PREFIX`, `MASTRA_HIDE_CLOUD_CTA`, `MASTRA_CLOUD_API_ENDPOINT`, `MASTRA_EXPERIMENTAL_FEATURES`, `MASTRA_TEMPLATES`, `MASTRA_TELEMETRY_DISABLED`, `MASTRA_REQUEST_CONTEXT_PRESETS`, `MASTRA_THEME_TOGGLE`, `MASTRA_EXPERIMENTAL_UI`, `MASTRA_STUDIO_BASE_PATH`.

## Knowledge routes (alpha)

```typescript
import { KNOWLEDGE_ROUTES, MASTRA_KNOWLEDGE_PRINCIPALS_KEY } from '@mastra/server/server-adapter'
```

- `new Mastra({ knowledge: { company: knowledge }, server: { apiRoutes: [...KNOWLEDGE_ROUTES] } })`. Mounts at `/api/knowledge`. Needs `@mastra/core` 1.81.0+.
- Without auth, routes return everything. With auth, set `MASTRA_KNOWLEDGE_PRINCIPALS_KEY` on `requestContext` in `authorize` to an array of scopes or `'all'`.
- NestJS adapter does not serve these routes yet.

---

## `new MastraEditor(options)` (`@mastra/editor`)

| Option | Default | Notes |
|---|---|---|
| `source` | `'db'` | `'db'` stores overrides in storage with draft and publish. `'code'` writes per-agent JSON files. |
| `codePath` | `'./mastra/editor'` | Files at `<codePath>/agents/<agentId>.json`. |
| `toolProviders` | `{}` | `Record<string, ToolProvider>`, for example Composio, Arcade. |
| `processorProviders` | `{}` | Built-ins always included. |
| `filesystems`, `sandboxes`, `blobStores`, `browsers` | `{}` | Provider records. |
| `builder` | disabled | Agent Builder (`createBuilderAgent()` from `@mastra/editor/ee`, EE license). |
| `logger` | Mastra logger | |

Separate Editor storage: `new MastraCompositeStore({ id, default, editor: new LibSQLStore({...}) })`.

Methods: `getToolProvider(id)`, `getToolProviders()`, `getProcessorProvider(id)`, `getProcessorProviders()`, `getFilesystemProviders()`, `getSandboxProviders()`, `getBlobStoreProviders()`, `getSource()` (`undefined` when not set explicitly).

## Editor namespaces (`mastra.getEditor()`)

Every namespace has `create`, `getById`, `update`, `delete`, `list`, `listResolved`, `clearCache`.

| Namespace | Extra methods and notes |
|---|---|
| `agent` | `getById(id, { status \| versionId \| versionNumber })`, `applyStoredOverrides(agent, options?, requestContext?)`, `clone(agent, { newId, ... })`. `update()` creates an inactive draft unless `status` and `activeVersionId` are passed. Stored `memory`: `{ type: 'id', memoryId }` or `{ type: 'inline', config }`. |
| `prompt` | `preview(blocks, context)` resolves templates and conditions with drafts. |
| `mcp` | Stored MCP client configs. |
| `mcpServer` | Stored MCP server configs. |
| `scorer` | `resolve(stored)` builds a runnable `MastraScorer` for llm-judge definitions. |

## Tool providers

| Class | Import | Options | Tool ID format |
|---|---|---|---|
| `ComposioToolProvider` | `@mastra/editor/composio` | `apiKey`, `allowedToolkits`, `allowedTools`, `defaultScope` (`'per-author'` default, `'shared'`, `'caller-supplied'`), `userIdResolver`, `sharedConnections` | `GITHUB_CREATE_ISSUE` |
| `ArcadeToolProvider` | `@mastra/editor/arcade` | `apiKey`, `baseURL` | `Github.GetRepository` |

Project tools become pickable when registered on `new Mastra({ tools })`. Collaborators can also create stored MCP clients (stdio or HTTP) with tool filters.

---

## Prompt blocks

Instruction block types: `text` (inline), `prompt_block` (embedded), `prompt_block_ref` (reference to a stored, versioned block).

Templates read request context: `{{userName}}`, `{{user.name}}`, `{{task || 'request'}}`. Unresolved placeholders stay as written.

Display conditions: `{ operator: 'AND' | 'OR', conditions: [{ field, operator, value? }] }`. Operators: `equals`, `not_equals`, `contains`, `not_contains`, `greater_than`, `less_than`, `greater_than_or_equal`, `less_than_or_equal`, `in`, `not_in`, `exists`, `not_exists`. Up to three nested groups. `exists` treats `''` as present. A ref's own `rules` and the stored block's rules must both pass.

REST: `GET|POST /api/stored/prompt-blocks`, `GET|PATCH|DELETE /api/stored/prompt-blocks/:storedPromptBlockId`.

## Versioning and REST routes

- Latest, Published (`activeVersionId`), Draft (latest differing from published), Historical. Identical saves create no version. Restore creates a new draft.
- `mastra.getAgentById(id)` without a selector returns the code agent. With `{ status: 'published' }` and no override, the code agent is returned.
- HTTP selectors: `GET /api/agents/:id?status=draft` or `?versionId=...`.
- Sub-agent versions: `new Mastra({ versions: { agents: { 'id': { status } } } })`, request body `versions`, or `generate(msg, { versions })`. Precedence: direct call > request > instance default.
- Stored agents: `GET|POST /api/stored/agents`, `GET|PATCH|DELETE /api/stored/agents/:id`, `GET .../:id/dependents`, `POST .../:id/export`, `POST .../:id/versions/:versionId/activate`. `PATCH` with `autoPublish: true` publishes immediately.
- Code source: initial version publishes to create the file, later updates are drafts until activated, Git history is read-only in Studio (last 50 commits).
