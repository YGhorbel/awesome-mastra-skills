# Troubleshooting reference

Distilled from `https://mastra.ai/reference/client-js/error-handling`, `reference/client-js/mastra-client`, `reference/manual-install`, `reference/tools/create-tool`, `reference/memory/memory-class`, `reference/migrations/upgrade-to-v1/*`, `docs/deployment/*`, and the official `mastra-ai/skills` common-errors reference. Verify against the installed version.

## Contents

- Required project configuration
- Diagnostic commands
- Error catalog: setup and modules
- Error catalog: models and env vars
- Error catalog: agents, tools, workflows
- Error catalog: memory and storage
- Error catalog: build, deploy, CLI
- Client SDK error handling
- Embedded docs lookup

---

## Required project configuration

- Node.js `22.13.0` or later.
- ESM project: `"type": "module"` in `package.json`.
- `tsconfig.json` (from the manual install guide):

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true,
    "types": ["node"],
    "noEmit": true,
    "outDir": "dist"
  },
  "include": ["src/**/*"]
}
```

- Scripts: `"dev": "mastra dev"`, `"build": "mastra build"`.
- All `@mastra/*` packages and `mastra` on matching versions.

## Diagnostic commands

| Command | Shows |
|---|---|
| `npm list @mastra/core mastra` | Installed versions |
| `node --version` | Runtime |
| `npx tsc --showConfig` | Effective compiler settings |
| `npx tsc --noEmit` | Type errors without building |
| `mastra dev` then `http://localhost:4111` | Studio: run agents, workflows, inspect traces |
| `MASTRA_DEV_NO_CACHE=1 mastra dev` | Rebuild without the `.mastra/` cache |
| `mastra lint` / `mastra lint --preflight` | Project and deploy checks |
| `mastra api agent list` | What the running server exposes |
| `curl -fsS http://localhost:4111/api/system/api-schema` | Route contracts |

Debug logging:

```typescript
import { Mastra } from '@mastra/core/mastra'
import { PinoLogger } from '@mastra/loggers'

export const mastra = new Mastra({
  logger: new PinoLogger({
    name: 'Mastra',
    level: 'debug',
  }),
})
```

---

## Error catalog: setup and modules

| Symptom | Cause | Fix |
|---|---|---|
| `SyntaxError: Cannot use import statement outside a module` | CommonJS project | `"type": "module"`, ES2022 tsconfig |
| `Error: Cannot find module '@mastra/core'` | Not installed, or wrong workspace | Install in the app package; check monorepo filter |
| `X is not exported from '@mastra/core'` | v1 root exports only `Mastra` and `Config` | Import from `@mastra/core/agent`, `/tools`, `/workflows`, etc. Codemod `v1/mastra-core-imports` |
| `Property 'x' does not exist on type 'Y'` | Example targets another version | Read installed `.d.ts`; align versions |
| Peer dependency warning at startup | Mixed versions | Update all Mastra packages together, or `MASTRA_SKIP_PEERDEP_CHECK=1` for local monorepo dev only |
| Errors after editing bundler plugins | Stale dev cache | `MASTRA_DEV_NO_CACHE=1 mastra dev` |

## Error catalog: models and env vars

| Symptom | Cause | Fix |
|---|---|---|
| Invalid model format | `openai:gpt-...` or a bare name | `'openai/gpt-6.1-sol'` style router string |
| Model not found | Wrong or retired ID | Check `https://mastra.ai/models` (see `mastra-models`) |
| 401, "API key not found" | Env var missing in this process | Set the provider variable; `.env` lives in the app directory |
| Works in dev, fails after `mastra build` | Build does not load `.env` | `mastra start` loads `.env.production` and `.env`; set variables on the host |
| Works locally, fails deployed | Variable not stored on the platform | Set it in the platform dashboard or env file used for deploy |
| Requests go to the wrong endpoint | Proxy base URL set | Check `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` |

## Error catalog: agents, tools, workflows

| Symptom | Cause | Fix |
|---|---|---|
| Agent never calls tools | Tools not on `new Agent({ tools })`, or instructions ignore them | Attach tools; name each tool and when to call it |
| Agent missing in Studio or API | Not registered | Add to `new Mastra({ agents })` |
| `MastraError` from `getAgentById` | Unknown ID | Use the agent `id`, not the variable name |
| `MastraError` before the LLM call | `requestContextSchema` failed | Set required request context keys |
| Empty final text | Last step was a tool call at `maxSteps` | Raise `maxSteps` |
| `maxTokens` ignored | Old option name | `modelSettings.maxOutputTokens` |
| Tool `execute: async ({ context, requestContext })` breaks | Pre-v1 signature | `execute: async (inputData, context)` |
| `context.runtimeContext` undefined | Renamed | `context.requestContext`. Codemod `v1/runtime-context` |
| Suspend or `resumeData` undefined in a tool | Moved to namespaces | `context.agent.suspend()`, `context.agent.resumeData`; workflows use `context.workflow` |
| `ValidationError` "Tool output validation failed" | Output does not match `outputSchema` | Fix the output, or `outputValidation: 'warn'` |
| Workflow run fails immediately | Missing `.commit()` | Call `.commit()` after chaining |
| `createRunAsync is not a function` | Renamed | `createRun()`. Codemod `v1/workflow-create-run-async` |
| Workflow input rejected | Inputs validated by default since v1 | Match `inputSchema`, or set `options: { validateInputs: false }` on `createWorkflow` |
| `getAgents`, `getWorkflows` not functions | Plural getters renamed | `listAgents()`, `listWorkflows()`. Codemod `v1/mastra-plural-apis` |
| `generateVNext` / `streamVNext` missing | Removed | `generate()` / `stream()` |

## Error catalog: memory and storage

| Symptom | Cause | Fix |
|---|---|---|
| `Memory requires a storage provider to function` | No storage on Memory or Mastra | Add `storage` to `new Mastra({...})` or `new Memory({...})` |
| History lost between calls | `threadId`/`resourceId` options (removed), or changing IDs | `memory: { thread, resource }`, stable per conversation |
| Agent "remembers" across threads | Default scope is `resource` since v1 | Set `scope: 'thread'` on working memory or semantic recall |
| Only 10 recent messages | Default `lastMessages` is 10 since v1 | Set `options.lastMessages` |
| Semantic recall does nothing | Disabled by default since v1, or no vector store or embedder | Enable it with a vector store and embedder (see `mastra-semantic-recall`) |
| Storage init error about missing `id` | `id` required since v1 | `new LibSQLStore({ id: 'mastra-storage', url })` |
| `ECONNREFUSED 127.0.0.1:5432` | Database down or wrong URL | Start the database; check `DATABASE_URL` |
| `duplicate key value violates unique constraint` on spans | Pre-v1 duplicate spans | `npx mastra migrate` |
| Data disappears after deploy | `file:` URL on an ephemeral filesystem | Remote database (see `mastra-deployment`) |
| Pods race creating the schema | Several replicas start on an empty DB | Start one replica, or init in a Job with `disableInit: true` |

## Error catalog: build, deploy, CLI

| Symptom | Fix |
|---|---|
| `JavaScript heap out of memory` | `NODE_OPTIONS="--max-old-space-size=4096" mastra build` |
| A package fails to bundle | Add to `bundler.externals` |
| Workspace package not found | List it in dependencies, refresh the lockfile, check `main`/`exports`, or add to `bundler.transpilePackages` |
| Build options ignored | Keep `bundler`/`deployer`/`server` as direct properties of `new Mastra({...})` |
| `Cannot find module '@libsql/linux-x64-gnu'` | Install dependencies inside the container image |
| `504` after 180 s | Raise `server.timeout` (and platform limits) |
| `mastra dev --port` rejected | Use `server.port` |
| `SERVER_UNREACHABLE`, `INVALID_JSON`, `MISSING_INPUT` from `mastra api` | See `mastra-cli-api` |
| Platform preflight blocks `file:./mastra.db` | See `mastra-platform` |

---

## Client SDK error handling

All `MastraClient` methods can throw. Catch around each call:

```typescript
try {
  const agent = mastraClient.getAgent('agent-id')
  const response = await agent.generate('Hello')
} catch (error) {
  console.error('An error occurred:', error.message)
}
```

Built-in retries are constructor options:

| Option | Default | Notes |
|---|---|---|
| `retries` | `3` | Attempts before throwing |
| `backoffMs` | `300` | Initial delay, doubled each retry |
| `maxBackoffMs` | `5000` | Cap on the delay |
| `headers` | | Auth headers sent on every request |
| `credentials` | | `'omit' \| 'same-origin' \| 'include'` |

See `mastra-client-sdk` for the full client.

## Embedded docs lookup

```bash
ls node_modules/@mastra/
ls node_modules/@mastra/core/dist/docs/references/
grep -r "createTool" node_modules/@mastra/core/dist/docs/references
cat node_modules/@mastra/core/dist/docs/assets/SOURCE_MAP.json | grep '"createTool"'
cat node_modules/@mastra/core/dist/<path-from-source-map>
```

Without installed packages, fetch `https://mastra.ai/<path>.md`.
