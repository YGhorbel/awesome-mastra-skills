# Mastra CLI reference

Distilled from `https://mastra.ai/reference/cli/mastra` and the official `mastra-ai/skills` mastra-api reference. Run `mastra <command> --help` against the installed version before relying on a flag.

## Contents

- Common and global flags
- Development and build
- Workers and experiments
- Project setup and maintenance
- Platform commands (pointer)
- `mastra api` flags, output, errors
- `mastra api` resources and actions
- Route-level debugging
- Telemetry

---

## Common and global flags

| Flag | Available in | Default |
|---|---|---|
| `--dir` | `dev`, `build`, `lint`, `migrate` | `src/mastra` |
| `--root` | `dev`, `build`, `lint`, `migrate` | `process.cwd()` |
| `--tools` | `dev`, `build`, `lint` | `src/mastra/tools` |
| `--env` | `dev`, `start`, `studio`, `migrate` | `.env.development`, `.env.local`, `.env` |
| `--debug` | `dev`, `build`, `migrate` | `false` |
| `--version`, `--help` | All | |

## Development and build

| Command | Flags and notes |
|---|---|
| `mastra dev` | `--https`, `--inspect[=host:port]`, `--inspect-brk[=host:port]` (not together), `--custom-args <list>`, `--request-context-presets <file.json>`. Env: `MASTRA_SKIP_PEERDEP_CHECK=1`, `MASTRA_DEV_NO_CACHE=1`, `MASTRA_CONCURRENCY=<n>`, `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`. |
| `mastra factory dev` | Agent Builder dev server. Same flags as `dev`; shares the dev lock. |
| `mastra build` | `--studio`. Env: `MASTRA_SKIP_PEERDEP_CHECK`, `MASTRA_CONCURRENCY`. Install a deployer for serverless output. |
| `mastra start` | Requires a build. `--dir` (default `.mastra/output`), `--custom-args`. OTEL tracing on by default. |
| `mastra studio` | `--port` (3000), `--server-host` (`localhost`), `--server-port` (4111), `--server-protocol` (`http`), `--server-api-prefix` (`/api`), `--request-context-presets`. |
| `mastra lint` | `--preflight`, `--skip-build` (with preflight), `--env-file <file>` (with preflight), `--strict`, `--json`, `--debug`. |

Request context presets file:

```json
{
  "development": { "userId": "dev-user", "env": "development" },
  "production": { "userId": "prod-user", "env": "production" }
}
```

## Workers and experiments

| Command | Notes |
|---|---|
| `mastra worker build` | `--dir`, `--root`, `--tools`, `--output-dir` (default `.mastra/output`, overwrites the server bundle), `--debug`. |
| `mastra worker start [name]` | `name` sets `MASTRA_WORKERS` (`orchestration`, `scheduler`, `backgroundTasks`). `--dir`, `--env`. |
| `mastra experiment build` | NDJSON companion worker in `.mastra/experiment-worker`. Exit codes: `0` completed, `10` item errors, `20` fatal, `21` retryable, `30` cancelled, `31` timed out, `70` protocol failure. |

## Project setup and maintenance

| Command | Notes |
|---|---|
| `mastra create` | Same flow as `create-mastra`. `--template`, `--empty`, `--llm`, `--no-skills`, `--no-git`. |
| `mastra init` | `--default`, `--dir` (`src`), `--components agents,tools,workflows,scorers`, `--llm openai\|anthropic\|groq\|google\|cerebras\|mistral`, `--llm-api-key`, `--example`/`--no-example`, `--mcp cursor\|cursor-global\|windsurf\|vscode`, `--observability`/`--no-observability`, `--observability-project`. |
| `mastra migrate` | Duplicate spans migration and ClickHouse legacy-to-vNext span copy. |
| `mastra scorers add [name]` / `mastra scorers list` | Scorer templates. |
| `mastra traces import langfuse` | `--target-project`, `--since`, `--until` (30-day window max), `--dry-run`, `--resume <id>`, `-y`. Env: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`. |

## Platform commands (pointer)

`mastra deploy`, `mastra env ...`, `mastra auth ...`, `mastra connect ...`, and the legacy `mastra server ...` and `mastra studio deploy` commands are covered by `mastra-platform` (and `mastra-tool-integrations` for `connect`).

---

## `mastra api` flags, output, errors

| Flag | Notes |
|---|---|
| `--url <url>` | Explicit target. |
| `--server-api-prefix <prefix>` | Default `/api`. Or `MASTRA_API_PREFIX`. |
| `--header "Key: Value"` | Repeatable. Sent to any target, including localhost. |
| `--timeout <ms>` | Default `30000`; workflow start and resume `120000`. |
| `--pretty` | Pretty-print. Off by default. |
| `--schema` | Leaf commands that take JSON: prints `command`, `examples`, `positionals`, `input.required`, `input.schema`, `schemas`. |
| `--verbose` | `trace list` and `trace get`: full span payloads. |

Observability credential resolution (hosted targets): `--header` values, then `MASTRA_PLATFORM_ACCESS_TOKEN` and `MASTRA_PROJECT_ID`, then `.mastra-project.json`, then the CLI login token. Trace Intelligence (`learning`) commands target `https://output.signals.mastra.ai` and also send `X-Mastra-Organization-Id` (from `--header`, `MASTRA_ORGANIZATION_ID`, or `.mastra-project.json`).

| Error code | Fix |
|---|---|
| `INVALID_JSON` | Fix quoting; one JSON object. |
| `MISSING_INPUT` | Run with `--schema`, supply required JSON. |
| `MISSING_ARGUMENT` | Provide the positional from `--help`. |
| `HTTP_ERROR` | Inspect `error.details` (server body in `details.body`). |
| `REQUEST_TIMEOUT` | Raise `--timeout`; for EU data use the EU `--url`. |
| `SERVER_UNREACHABLE` | Check the URL or start the server. |

---

## `mastra api` resources and actions

| Command | Positionals and input |
|---|---|
| `agent list [input]` / `agent get <agentId>` | |
| `agent run <agentId> <input>` | `{"messages": "..."}` or chat messages; memory thread options via `--help`. |
| `workflow list [input]` / `workflow get <workflowId>` | |
| `workflow run start <workflowId> <input>` | `{"inputData": {...}}` |
| `workflow run list <workflowId> [input]` / `workflow run get <workflowId> <runId>` | |
| `workflow run resume <workflowId> <runId> <input>` | Suspended runs only. |
| `workflow run cancel <workflowId> <runId>` | |
| `tool list [input]` / `tool get <toolId>` | |
| `tool execute <toolId> <input>` | Raw input is wrapped as `data` unless you pass `{"data": ...}`. |
| `mcp list [input]` / `mcp get <id>` | |
| `mcp tool list <serverId> [input]` / `mcp tool get <serverId> <toolId>` / `mcp tool execute <serverId> <toolId> <input>` | |
| `thread list [input]` / `thread get <threadId>` / `thread messages <threadId> [input]` | |
| `thread create <input>` | `agentId`, `resourceId`, `threadId`, `title`. The CLI splits query and body. |
| `thread update <threadId> <input>` / `thread delete <threadId> <input>` | Delete needs `agentId` and `resourceId`. |
| `memory search <input>` | `agentId`, `resourceId`, `searchQuery`. |
| `memory current get <input>` / `memory current update <input>` | Update needs working memory enabled. |
| `memory status <input>` | |
| `trace list [input]` | `page`, `perPage`, `filters` (for example `{"spanType":"agent"}`). Lightweight unless `--verbose`. |
| `trace query <input>` / `trace aggregate <input>` | See `trace-query.md`. |
| `span query <input>` / `span aggregate <input>` | See `trace-query.md`. |
| `trace get <traceId>` / `trace span <traceId> <spanId>` | |
| `log list [input]` | |
| `metric aggregate\|breakdown\|timeseries\|percentiles <input>` | `name`, `aggregation`, `groupBy`, `interval`, `percentiles` (0 to 1). |
| `metric names [input]` / `metric label-keys <input>` / `metric label-values <input>` | Discovery. |
| `score create <input>` / `score list [input]` / `score get <scoreId>` | |
| `dataset list [input]` / `dataset get <datasetId>` / `dataset create <input>` / `dataset items <datasetId> [input]` | |
| `experiment list <datasetId> [input]` / `experiment get <datasetId> <experimentId>` / `experiment run <datasetId> <input>` / `experiment results <datasetId> <experimentId> [input]` | |
| `learning entities\|snapshots\|flow\|paths ...` / `learning theme list\|get\|examples\|history ...` / `learning noise get\|examples ...` | Trace Intelligence private beta. |
| `factory ...` | Factory projects and work items; root-level `/web/factory/...` routes. |

---

## Route-level debugging

```bash
curl -fsS "$MASTRA_URL/api/system/api-schema" \
  | jq '.routes[] | select(.method == "POST" and .path == "/tools/:toolId/execute") | {pathParamSchema, queryParamSchema, bodySchema, responseShape}'
```

Hosted observability with `curl`:

```bash
curl -sS "https://observability.mastra.ai/api/observability/traces?page=0&perPage=20" \
  -H "Authorization: Bearer $MASTRA_PLATFORM_ACCESS_TOKEN" \
  -H "X-Mastra-Project-Id: $MASTRA_PROJECT_ID" | jq
```

Other paths: `/traces/<trace-id>/light`, `/traces/<trace-id>/spans/<span-id>`.

## Telemetry

The CLI, servers, and Studio send usage telemetry (token counts every 15 minutes, feature snapshots; no prompts or responses). `project_id2` can include the platform project ID unhashed. Opt out with `MASTRA_TELEMETRY_DISABLED=1`.
