# Project setup API reference

Distilled from `https://mastra.ai/reference/cli/create-mastra.md`, `https://mastra.ai/reference/manual-install.md`, `https://mastra.ai/reference/project-structure.md`, `https://mastra.ai/reference/configuration.md`, `https://mastra.ai/reference/core/mastra-class.md`, `https://mastra.ai/reference/core/*`, and `https://mastra.ai/reference/cli/mastra.md`. Verify against the installed version before relying on an option.

## Contents

- `create-mastra` flags
- Manual install packages
- `mastra` CLI for local development
- CLI environment variables
- `Mastra` constructor options
- Server options
- Bundler options
- Instance accessors

---

## `create-mastra` flags

Run with `npx create-mastra@latest`, `pnpm dlx create-mastra@latest`, `yarn dlx create-mastra@latest`, `bun x create-mastra@latest`, or `npm create mastra@latest`.

| Flag | Notes |
|---|---|
| `[project-name]` | Lowercase, single directory, must not exist. Prompted if omitted. |
| `-l, --llm <provider>` | `mastra`, `openai`, `anthropic`, `google`, `xai`. Default starter only. |
| `-k, --llm-api-key <key>` | Writes the key to `.env`. Default starter only. With `mastra`, skips browser sign-in. |
| `-t, --template [template]` | Template slug or public GitHub URL. No value = interactive picker. |
| `--empty` | Provider-free project with no agents, examples, model SDKs, or env files. Not with `--template`. |
| `--no-skills` | Skip Mastra skills installation for coding assistants. |
| `--no-git` | Skip Git init and the initial commit. |
| `--no-install` | Skip dependency installation. |
| `--timeout <ms>` | Dependency install timeout. Default `60000`. |
| `--version`, `--help` | Info. |

Mastra Gateway: selecting it writes `MASTRA_GATEWAY_API_KEY` and uses `mastra/<provider>/<model>` IDs. Interactive setup can also connect a Mastra platform project and write `MASTRA_PLATFORM_ACCESS_TOKEN` and `MASTRA_PROJECT_ID`. Set `MASTRA_TELEMETRY_DISABLED=1` to opt out of CLI telemetry.

Templates listed in the docs: `template-docs-expert`, `template-browser-agent`, `template-meeting-notes`, `template-company-knowledge`, `template-claw-assistant`, plus the default `agent-harness`. Template authors own their models and env vars; `--llm` does not apply.

---

## Manual install packages

| Package | Kind | Purpose |
|---|---|---|
| `@mastra/core@latest` | dependency | Agents, workflows, tools, `Mastra` class |
| `zod@^4` | dependency | Schemas |
| `mastra@latest` | devDependency | CLI (`mastra dev`, `build`, `start`, `lint`) |
| `typescript`, `@types/node` | devDependency | Type checking |
| `@mastra/libsql` | optional | `LibSQLStore` storage |
| `@mastra/loggers` | optional | `PinoLogger` |

`package.json` scripts: `"dev": "mastra dev"`, `"build": "mastra build"`. Do not install AI SDK provider packages for router models.

---

## `mastra` CLI for local development

| Command | Notes |
|---|---|
| `mastra dev` | Studio and REST API on `http://localhost:4111`. API list at `/api`, OpenAPI at `/swagger-ui`. Restarts on changes in `src/mastra/`. Flags: `--https`, `--inspect[=host:port]`, `--inspect-brk`, `--custom-args`, `--request-context-presets <file>`. |
| `mastra build` | Bundles to `.mastra/output` as a Hono server. `--studio` bundles Studio. |
| `mastra start` | Serves the build. `--dir` (default `.mastra/output`). |
| `mastra init` | Adds Mastra to an existing project. Flags: `--default`, `--dir` (default `src`), `--components agents,tools,workflows,scorers`, `--llm`, `--llm-api-key`, `--example`/`--no-example`, `--mcp`, `--observability`/`--no-observability`. |
| `mastra lint` | Validates project structure. `--preflight`, `--skip-build`, `--env-file`, `--strict`, `--json`. |
| `mastra api ...` | Call agents, workflows, traces against a running server (see `mastra-cli-api`). |

Common flags: `--dir` (Mastra folder, default `src/mastra`), `--root` (default `process.cwd()`), `--env` (env file; default loads `.env.development`, `.env.local`, `.env`), `--tools` (default `src/mastra/tools`), `--debug`.

---

## CLI environment variables

| Variable | Effect |
|---|---|
| `PORT` | Overrides `server.port`. |
| `MASTRA_HOST` | Overrides `server.host`. |
| `MASTRA_SKIP_PEERDEP_CHECK=1` | Skip the peer dependency check. |
| `MASTRA_DEV_NO_CACHE=1` | Force a full rebuild under `.mastra/`. |
| `MASTRA_CONCURRENCY=<n>` | Cap parallel build and eval work. |
| `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` | Proxy built-in providers. |
| `MASTRA_TELEMETRY_DISABLED=1` | Disable CLI telemetry. |

---

## `Mastra` constructor options

Import: `import { Mastra } from '@mastra/core'` (also `@mastra/core/mastra`).

| Option | Type | Default / notes |
|---|---|---|
| `agents` | `Record<string, Agent>` | `{}` |
| `workflows` | `Record<string, Workflow>` | `{}` |
| `tools` | `Record<string, ToolApi>` | `{}`. Keys used by `getTool()`. |
| `storage` | `MastraCompositeStore` | None. Example: `new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' })`. |
| `vectors` | `Record<string, MastraVector>` | None |
| `memory` | `Record<string, MastraMemory>` | `{}` |
| `logger` | `IMastraLogger \| false` | Console logger, INFO in dev, WARN in prod |
| `loggerOptions` | `{ correlation?, export? }` | `{ correlation: true, export: true }` |
| `observability` | `ObservabilityEntrypoint` | See `mastra-observability`. |
| `server` | `ServerConfig` | See below. |
| `bundler` | `BundlerConfig` | See below. |
| `deployer` | `IDeployer` | See `mastra-deployment`. |
| `gateways` | `Record<string, MastraModelGateway>` | `{}`. See `mastra-models`. |
| `scorers` | `Record<string, Scorer>` | `{}` |
| `classifiers` | `Record<string, Classifier>` | `{}` |
| `processors` | `Record<string, Processor>` | `{}` |
| `mcpServers` | `Record<string, MCPServerBase>` | See `mastra-mcp`. |
| `tts` | `Record<string, MastraVoice>` | Voice providers |
| `pubsub` | `PubSub` | `EventEmitterPubSub` |
| `events` | `Record<string, EventHandler \| EventHandler[]>` | Event handlers |
| `workspace` | `Workspace` | See `mastra-workspace-sandbox`. |
| `idGenerator` | `(context?) => string` | `crypto.randomUUID()` |
| `environment` | `string` | Tag for observability. Falls back to `development` under `mastra dev`, then `NODE_ENV`. |
| `backgroundTasks` | `{ enabled, globalConcurrency, perAgentConcurrency, backpressure, defaultTimeoutMs, ... }` | Needs storage. See `mastra-harness`. |
| `scheduler` | `{ enabled? }` | Auto-enables when a workflow declares a schedule. |
| `recovery` | `{ durableAgents, workflows, workflowConcurrency }` | `{ durableAgents: 'off', workflows: 'auto', workflowConcurrency: 5 }` |
| `workers` | `MastraWorker[] \| false` | `false` disables event processing in this instance. |
| `notifications` | `{ dispatch: { enabled, cron, batchSize } }` | Signal notification dispatch. |
| `versions` | `{ agents: Record<id, { versionId? \| status? }> }` | Editor versions for subagents. |

---

## Server options

| Option | Default | Notes |
|---|---|---|
| `server.port` | `4111` (or `PORT`) | |
| `server.host` | `localhost` (or `MASTRA_HOST`) | Use `'0.0.0.0'` in containers. |
| `server.timeout` | `180000` | Request timeout in ms. |
| `server.cors` | `origin: '*'` and standard headers | `false` disables CORS. |
| `server.studioBase` | `/` | Host Studio on a sub-path. |
| `server.drainTimeout` | `5000` | Graceful shutdown drain in ms. |
| `server.handleShutdownSignals` | `true` | Install `SIGINT`/`SIGTERM` handlers. |
| `server.https` | none | `{ key, cert }`, or `mastra dev --https`. |
| `server.apiRoutes`, `middleware`, `auth`, `onError`, `onValidationError`, `bodySizeLimit`, `build`, `mcpOptions` | | See `mastra-server` and `mastra-auth`. |

---

## Bundler options

| Option | Default | Notes |
|---|---|---|
| `bundler.externals` | `true` | `true` = all `package.json` deps external; `false` = bundle all; `string[]` = listed only. |
| `bundler.sourcemap` | `false` | Also runs dev and start with `--enable-source-maps`. |
| `bundler.minify` | `false` | Never applied to `mastra dev`. |
| `bundler.transpilePackages` | `[]` | Uncompiled TS packages. Monorepo workspace packages are added automatically. |
| `bundler.pnpmWorkspaceSettings` | `{}` | Allowed pnpm install-policy keys only. |

---

## Instance accessors

| Method | Notes |
|---|---|
| `getAgentById(id)` / `getAgent(key)` / `listAgents()` | Agents |
| `getWorkflow(key)` / `getWorkflowById(id)` / `listWorkflows()` | Workflows |
| `getTool(key)` / `getToolById(id)` / `listTools()` | Tools |
| `getStorage()` / `setStorage(store)` | Storage |
| `getLogger()` / `setLogger({ logger })` | Logger |
| `getVector(name)` / `listVectors()` | Vector stores |
| `getMemory(key)` / `listMemory()` | Memory |
| `getScorer(key)` / `getScorerById(id)` / `listScorers()` | Scorers |
| `getClassifier(key)` / `getClassifierById(id)` / `listClassifiers()` | Classifiers |
| `getMCPServer(key)` / `getMCPServerById(id)` / `listMCPServers()` | MCP servers |
| `getGateway(key)` / `getGatewayById(id)` / `listGateways()` / `addGateway(g, key?)` | Model gateways |
| `getServer()`, `getDeployer()`, `getEditor()` | Config objects |
| `addDynamicWorkflow(def)` / `addDynamicWorkflows(defs)` | Dynamic workflows (beta) |
| `listLogs(transportId)` / `listLogsByRunId(...)` | Logs |
| `shutdown()` | Graceful teardown |
