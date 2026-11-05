---
name: mastra-cli-api
description: "Use the mastra CLI to develop, build, start, lint, and migrate a Mastra project, and use mastra api to inspect and call a running server: list and run agents, start and resume workflows, execute tools and MCP tools, manage memory threads, and query traces, spans, logs, metrics, scores, datasets, and experiments on a local, self-hosted, or Mastra Platform target. Use this skill whenever the user wants to run mastra dev, check what a server exposes, call an agent from the terminal, find failing tool calls or slow traces, compute error rates or token cost per agent, or script Mastra checks in CI. Triggers on mastra dev, mastra build, mastra start, mastra studio, mastra lint, mastra migrate, mastra worker, mastra api, agent run, workflow run start, tool execute, trace query, trace aggregate, span query, metric aggregate, --schema, localhost:4111, swagger-ui. Also triggers when the user asks why an agent failed in production and traces are the evidence."
license: Apache-2.0
metadata:
  category: deploy-and-platform
  catalog_summary: "mastra CLI commands, plus mastra api for agents, workflows, tools, threads, traces, spans, logs, metrics"
  display_order: 3
  docs: https://mastra.ai/reference/cli/mastra
---

# Mastra CLI and `mastra api`

Run the Mastra project lifecycle from the terminal, and call or inspect any running Mastra server with compact, JSON-in, JSON-out commands.

---

## When to use

- Starting the dev server and Studio, building, and serving the build
- Linting a project or running deploy preflight checks
- Running storage migrations after an upgrade (`mastra migrate`)
- Listing or calling agents, workflows, tools, and MCP tools on a running server
- Reading memory threads and working memory
- Finding traces or spans by condition, and aggregating error rate, latency, tokens, or cost
- Reading logs, metrics, scores, datasets, and experiments
- Scripting smoke tests against a deployment in CI

## When NOT to use

- Creating a new project from scratch (use `mastra-project-setup`)
- Deploying to Mastra Platform, environments, databases, tokens (use `mastra-platform`)
- Hosting on other clouds and Docker (use `mastra-deployment`)
- Calling a server from application code with `MastraClient` (use `mastra-client-sdk`)
- Configuring tracing exporters and span processors (use `mastra-observability`)
- Building datasets and experiments in code (use `mastra-datasets-experiments`)
- Diagnosing a specific error message (use `mastra-troubleshooting`)

---

## Required inputs

- The target: local dev server, a deployed URL, or a Mastra Platform project (`.mastra-project.json`)
- Authentication for that target: none (localhost), a bearer token header, or platform credentials
- The resource and action (for example `agent run`, `trace query`)
- For observability queries: a time range that holds the data, and the region (US or EU)

Never request secret values in chat. For custom servers, the user sets up auth outside the conversation and passes it through an env var in `--header`.

---

## The framework: lifecycle commands and one API client

### Lifecycle

| Command | What it does |
|---|---|
| `mastra dev` | Dev server and Studio on `http://localhost:4111`; Swagger at `/swagger-ui` |
| `mastra build [--studio]` | Bundle to `.mastra/output` |
| `mastra start` | Serve the build; loads `.env.production` and `.env` |
| `mastra studio` | Standalone Studio on port 3000 pointing at a server |
| `mastra lint [--preflight]` | Project checks; `--preflight` runs deploy checks on the build |
| `mastra migrate` | Storage schema migrations |
| `mastra worker build` / `worker start <name>` | Worker bundle and processes |
| `mastra init`, `mastra create` | Add Mastra to a project, or create one |
| `mastra scorers add` / `list` | Scorer templates |
| `mastra traces import langfuse` | Import Langfuse traces into a platform project |

### `mastra api`

One inline JSON argument in, JSON out. Success goes to stdout as `{ "data": ... }` (lists add `page`). Errors go to stderr as `{ "error": { code, message, details } }` with a non-zero exit code.

```bash
mastra api agent list
mastra api agent run weather-agent '{"messages":"What is the weather in London?"}'
mastra api tool execute get-weather '{"location":"San Francisco"}'
mastra api trace list '{"page":0,"perPage":20}'
```

Target resolution for runtime commands (`agent`, `workflow`, `tool`, `mcp`, `thread`, `memory`, `dataset`, `experiment`):

1. `--url <url>`
2. `http://localhost:4111`
3. `.mastra-project.json` (platform project, automatic credentials)

Observability commands (`trace`, `span`, `log`, `score`, `metric`) default to `https://observability.mastra.ai` with `MASTRA_PLATFORM_ACCESS_TOKEN` and `MASTRA_PROJECT_ID`. Pass `--url https://observability.eu.mastra.ai` for EU data, or `--url http://localhost:4111` for a local server.

---

## Workflow

1. **Verify the API.** Run `mastra --version`, `mastra api --help`, and `mastra api <resource> <action> --help`. If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/`. Otherwise fetch `https://mastra.ai/reference/cli/mastra.md`. Trust these over memory.
2. **Confirm the target.** For local, check `curl -fsS http://localhost:4111/api/system/api-schema`. For remote, ask for the URL. For EU platform data, use the EU host.
3. **Read before you write.** Use `list` and `get` with small pages (`perPage` 1 to 10) and project with `jq` immediately.
4. **Get the input shape.** Run the leaf command with `--schema` before any mutating call (`agent run`, `workflow run start`, `tool execute`, `thread create`, `score create`).
5. **Call.** Pass exactly one JSON object. Raise `--timeout` for long workflow runs (default 30000 ms, workflow start and resume 120000 ms).
6. **Escalate queries only when needed.** `trace list` for browsing, `trace query` for predicates, `trace aggregate` for counts and measures, `span query` and `span aggregate` for nested spans.
7. **Drill into evidence.** `trace get <traceId>` for the timeline, `trace span <traceId> <spanId>` for one full span.
8. **Report.** Summarize the projected fields, not raw JSON. Treat empty lists as "no stored data yet", not as an error.

---

## Deep dive: querying traces and spans

`trace query` and `span query` take a required `timeRange` (`from` inclusive, `to` exclusive, ISO strings) and an optional recursive `where` predicate.

```bash
npx mastra api trace query \
  '{"timeRange":{"from":"2026-08-01T00:00:00.000Z","to":"2026-08-08T00:00:00.000Z"},"where":{"spans":{"some":{"op":"and","args":[{"op":"eq","left":{"path":"spanType"},"right":{"literal":"tool_call"}},{"op":"exists","path":"error"}]}}},"page":{"limit":25}}' \
  | jq '{traces: [.data.traces[] | {traceId, entityName, status, startedAt}], next: .data.page.next}'
```

Rules that prevent wrong answers:

- Conditions that must hold on the same span go in one `spans.some` clause.
- `span query` filters span fields directly. Do not wrap its predicates in `spans.some`.
- Pass `data.page.next` back unchanged as `page.after` with the identical query. Changing the query returns `409`.
- Aggregations are not paginated. When `truncated` is `true`, narrow the selection.
- Tokens and cost sit on the span that recorded them (usually `model_generation`). Use `trace aggregate` for per-trace totals.
- Report a `null` cost as unknown, not zero.
- `501` means the store does not support the operation. Report it instead of approximating client-side.

See `references/trace-query.md` for fields, operators, measures, and limits.

---

## Failure patterns

- **`SERVER_UNREACHABLE`.** Nothing on `localhost:4111`. Start `mastra dev` or pass `--url`.
- **`INVALID_JSON`.** Shell quoting broke the JSON. Wrap it in single quotes; input is one object.
- **`MISSING_INPUT` or `MISSING_ARGUMENT`.** Run the same command with `--schema` or `--help` and supply the field or positional.
- **`HTTP_ERROR` 401 on a custom server.** Add `--header "Authorization: Bearer $TOKEN"`. Localhost and arbitrary URLs get no automatic credentials.
- **`REQUEST_TIMEOUT` on workflows.** Raise `--timeout`. For EU projects on old CLIs, pass the EU `--url`.
- **Passing a file path or stdin.** Not supported. Inline the JSON.
- **Using `mastra api agent generate`.** The command is `agent run`.
- **`workflow run resume` fails.** The run is not suspended. Check `workflow run get` first.
- **`memory current update` fails.** Working memory is not enabled on the agent's memory.
- **`--schema` against Mastra Platform observability.** Not exposed there. Use the canonical query reference.
- **Huge output.** Unfiltered `--pretty` or `--verbose`. Project with `jq` and keep pages small.
- **`mastra dev --port`.** Removed. Set `server.port` on the Mastra instance.
- **`mastra dev` exits with a duplicate server error.** `mastra factory dev` or another dev server holds the lock.

---

## Output format

A finished CLI task delivers:

- The exact commands run, with the target (`--url`) and no secret values
- Compact results: projected fields, counts, and IDs for follow-up (`traceId`, `runId`)
- For queries: the time range, predicate, and whether results were truncated or paginated
- For scripts: a shell or CI step that checks the exit code and parses `.data`

---

## Reference files

- [`references/api.md`](references/api.md) - Every CLI command and flag, `mastra api` resources, actions, flags, and error codes.
- [`references/trace-query.md`](references/trace-query.md) - Trace and span query fields, operators, measures, pagination, and limits.
- [`references/examples.md`](references/examples.md) - Smoke test a deployment, run a workflow, find failing tools, error rate per agent, metrics.
- [`references/checklist.md`](references/checklist.md) - Checklist for safe, compact CLI usage.

**Live docs**

- https://mastra.ai/reference/cli/mastra
- https://mastra.ai/reference/observability/tracing/advanced-queries
- https://mastra.ai/reference/observability/metrics/queries
- https://mastra.ai/reference/configuration
- https://mastra.ai/docs/mastra-platform/observability
