# CLI and `mastra api` examples

All commands follow the current CLI reference. Replace example timestamps with a recent range that holds data. Never put secret values in commands; reference env vars the user has set.

## Contents

1. Local development loop
2. Smoke test a deployment in CI
3. Start and inspect a workflow run
4. Find failing tool calls and drill into one
5. Error rate, latency, and cost per agent
6. Metrics on an EU platform project

---

## 1. Local development loop

```bash
mastra dev --request-context-presets ./presets.json
```

In another terminal:

```bash
MASTRA_URL="${MASTRA_URL:-http://localhost:4111}"
curl -fsS "$MASTRA_URL/api/system/api-schema" >/dev/null

npx mastra api agent list | jq '.data'
npx mastra api agent run --schema | jq '.input'
npx mastra api agent run weather-agent '{"messages":"What is the weather in London?"}'
npx mastra api tool execute get-weather '{"location":"San Francisco"}'
```

Before deploying, run the preflight checks:

```bash
mastra lint --preflight --strict
```

---

## 2. Smoke test a deployment in CI

The user stores the deployment URL and a bearer token as CI secrets (`MASTRA_URL`, `MASTRA_TOKEN`).

```bash
set -euo pipefail

curl -fsS "$MASTRA_URL/health"

npx mastra api --url "$MASTRA_URL" --header "Authorization: Bearer $MASTRA_TOKEN" agent list \
  | jq -e '.data | length > 0'

npx mastra api --url "$MASTRA_URL" --header "Authorization: Bearer $MASTRA_TOKEN" \
  agent run weather-agent '{"messages":"Say OK"}' \
  | jq -e '.data'
```

Each command exits non-zero on error, and `jq -e` fails on an empty result, so the job fails loudly. For a server mounted under a custom prefix, add `--server-api-prefix /api/mastra-studio`.

---

## 3. Start and inspect a workflow run

```bash
npx mastra api workflow list | jq '.data'
npx mastra api workflow run start --schema | jq '.input.schema'

npx mastra api --timeout 300000 workflow run start data-pipeline \
  '{"inputData":{"source":"s3://bucket/data.csv"}}' | jq '.data'

npx mastra api workflow run list data-pipeline '{"page":0,"perPage":5}' \
  | jq '.data[] | {runId, status}'

npx mastra api workflow run get data-pipeline <runId> | jq '.data.status'
```

Resume only when the run is suspended:

```bash
npx mastra api workflow run resume --schema
npx mastra api workflow run resume data-pipeline <runId> '<json from --schema>'
```

---

## 4. Find failing tool calls and drill into one

Traces that contain a tool call with an error (both conditions on the same span):

```bash
npx mastra api trace query \
  '{"timeRange":{"from":"2026-08-01T00:00:00.000Z","to":"2026-08-08T00:00:00.000Z"},"where":{"spans":{"some":{"op":"and","args":[{"op":"eq","left":{"path":"spanType"},"right":{"literal":"tool_call"}},{"op":"exists","path":"error"}]}}},"page":{"limit":25}}' \
  | jq '{traces: [.data.traces[] | {traceId, entityName, status, startedAt}], next: .data.page.next}'
```

The failing spans themselves, including tool calls nested inside other agents:

```bash
npx mastra api span query \
  '{"timeRange":{"from":"2026-08-07T00:00:00.000Z","to":"2026-08-08T00:00:00.000Z"},"where":{"op":"and","args":[{"op":"eq","left":{"path":"spanType"},"right":{"literal":"tool_call"}},{"op":"eq","left":{"path":"status"},"right":{"literal":"error"}}]},"page":{"limit":25}}' \
  | jq '{spans: [.data.spans[] | {traceId, spanId, entityName, rootEntityName, errorPreview}], next: .data.page.next}'
```

Inspect the evidence:

```bash
npx mastra api trace get <traceId> | jq '.data'
npx mastra api trace span <traceId> <spanId> | jq '.data'
```

Against a local server instead of hosted observability, add `--url http://localhost:4111`.

---

## 5. Error rate, latency, and cost per agent

```bash
npx mastra api trace aggregate \
  '{"timeRange":{"from":"2026-08-01T00:00:00.000Z","to":"2026-08-08T00:00:00.000Z"},"where":{"op":"eq","left":{"path":"entityType"},"right":{"literal":"agent"}},"groupBy":["entityName"],"measures":["count","errorRate","duration.p95","cost.sum"],"orderBy":{"field":"errorRate","direction":"desc"},"limit":10}' \
  | jq '{rows: [.data.rows[] | {agent: .dimensions.entityName, measures, coverage: .cost.coverage}], truncated: .data.truncated}'
```

Daily trend for one agent:

```bash
npx mastra api trace aggregate \
  '{"timeRange":{"from":"2026-08-01T00:00:00.000Z","to":"2026-08-08T00:00:00.000Z"},"where":{"op":"eq","left":{"path":"entityName"},"right":{"literal":"weather-agent"}},"interval":"1d","measures":["count","duration.p95"]}'
```

Slowest tools by p95:

```bash
npx mastra api span aggregate \
  '{"timeRange":{"from":"2026-08-01T00:00:00.000Z","to":"2026-08-08T00:00:00.000Z"},"where":{"op":"eq","left":{"path":"spanType"},"right":{"literal":"tool_call"}},"groupBy":["entityName"],"measures":["count","errorRate","duration.p95"],"orderBy":{"field":"errorRate","direction":"desc"},"limit":10}'
```

Report a `null` cost or low `coverage` as incomplete, not zero. If `truncated` is `true`, narrow the selection.

---

## 6. Metrics on an EU platform project

With `MASTRA_PLATFORM_ACCESS_TOKEN` and `MASTRA_PROJECT_ID` set by the user:

```bash
npx mastra api --url https://observability.eu.mastra.ai metric names '{"prefix":"mastra_model_","limit":10}'

npx mastra api --url https://observability.eu.mastra.ai metric aggregate \
  '{"name":["mastra_model_total_input_tokens","mastra_model_total_output_tokens"],"aggregation":"sum"}'

npx mastra api --url https://observability.eu.mastra.ai metric percentiles \
  '{"name":"latency_ms","percentiles":[0.5,0.95,0.99],"interval":"1h"}'
```

Querying the US host for an EU environment returns no records.
