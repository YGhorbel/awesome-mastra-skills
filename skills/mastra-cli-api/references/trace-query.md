# Trace and span queries

Distilled from `https://mastra.ai/reference/observability/tracing/advanced-queries` and the official `mastra-ai/skills` trace-query reference. The target server's capabilities decide what works; a newer local CLI does not prove a deployed server supports a feature.

## Contents

- Choosing the command
- Capabilities
- Predicate grammar
- Trace fields
- Span fields
- Query requests and pagination
- Aggregate requests
- Dimensions and measures
- Limits and errors

---

## Choosing the command

| Command | HTTP route | Returns |
|---|---|---|
| `trace list` | `GET /api/observability/traces` | Recent root spans, simple filters |
| `trace query` | `POST /api/observability/traces/query` | One row per completed trace matching a predicate |
| `trace aggregate` | `POST /api/observability/traces/aggregate` | Measures per group or time bucket |
| `span query` | `POST /api/observability/spans/query` | One row per completed span, including nested runs |
| `span aggregate` | `POST /api/observability/spans/aggregate` | Measures per span group |
| `trace get <traceId>` | | Lightweight timeline |
| `trace span <traceId> <spanId>` | | One span in full |

Confirm the installed CLI exposes a command (`--help`) and inspect the local route contract (`--schema`). Mastra Platform does not expose `--schema`.

## Capabilities

Check `getObservabilityCapabilities()` (client SDK) or `GET /api/observability/capabilities`. Missing or false means unavailable.

| Capability | Enables |
|---|---|
| `traceQuery`, `spanQuery`, `traceAggregate`, `spanAggregate` | The four operations |
| `spanQueryContextFields` | Span filters on `traceId`, `spanId`, `parentSpanId`, `threadId`, `resourceId`, `requestId`, `serviceName`, `experimentId`, `environment`, `executionSource`, parent and root entity fields |
| `spanQueryModelFields` | `model`, `provider` span filters |
| `spanQueryOutcomeFields`, `traceQueryOutcomeFields` | `outcome`, `stopReason` |
| `traceQueryRootSpanFields`, `traceQueryRootEntityId` | Trace-scope `name`, `spanType`, `entityId` |
| `traceQueryContextIds`, `traceQueryContextFields` | `runId`, `sessionId`, `userId`, `organizationId`; `requestId`, `serviceName`, `experimentId` |
| `traceQueryRootDuration`, `traceQueryTimeToFirstChunk`, `traceQueryTimeToFirstToken` (and `*Sort`) | Duration and time-to-first predicates and ordering |
| `aggregateTimeToFirstMeasures` | `timeToFirstToken.*`, `timeToFirstChunk.*` measures |
| `spanAggregateModelDimensions` | Grouping spans by `model`, `provider` |
| `traceQueryDiscovery` | Field and value discovery endpoints |

## Predicate grammar

```json
{ "op": "eq", "left": { "path": "entityName" }, "right": { "literal": "weather-agent" } }
{ "op": "in", "value": { "path": "spanType" }, "set": ["agent_run", "tool_call"] }
{ "op": "exists", "path": "error" }
{ "op": "and", "args": [ ... ] }
{ "op": "not", "arg": { ... } }
{ "spans": { "some": { ... } } }
{ "spans": { "none": { ... } } }
```

- Comparison: field on the left, literal on the right. Literals are never coerced. Strings are case-sensitive except `matches`/`notMatches` (span `name`).
- A missing value fails positive and ordered predicates but satisfies `ne` and `notIn`. Pair a negative with `exists` when the field must be present.
- `spans.some`: one span must satisfy the whole nested predicate. Separate clauses can match different spans.
- `spans.none`: no span matches. Traces with no related spans match.
- The root `timeRange` filters the root span `startedAt` only.
- For a `null` group, select with `notExists`, not `eq` with a null literal.

## Trace fields

| Fields | Operators |
|---|---|
| `traceId`, `threadId`, `resourceId`, `runId`, `sessionId`, `userId`, `organizationId`, `requestId`, `serviceName`, `experimentId`, `entityId`, `entityName`, `entityType`, `name`, `spanType`, `environment`, `status`, `outcome`, `stopReason` | `eq`, `ne`, `in`, `notIn`, `exists`, `notExists` |
| `metadata.<key>` | Same; values trimmed |
| `startedAt`, `endedAt`, `durationMs`, `timeToFirstChunkMs`, `timeToFirstTokenMs` | Above plus `lt`, `lte`, `gt`, `gte` |
| `tags` | `includes`, `notIncludes`, `exists`, `notExists` |

Trace-scope `name`, `spanType`, `entityId` read the root span. Inside `spans.some`, span fields add `model`, `provider`, entity version fields, and `error` (`exists`/`notExists`), and `name` supports `matches`.

## Span fields

`span query` filters spans directly (no `spans.some`): `traceId`, `spanId`, `parentSpanId`, `threadId`, context identifiers, `environment`, `executionSource`, entity, parent entity, and root entity `Type`/`Id`/`Name`/`VersionId`, `name`, `spanType`, `status` (`error` or `success`), `model`, `provider`, `outcome`, `stopReason`, timestamps and durations, `error`.

Span types seen in docs: `agent_run`, `workflow_run`, `processor_run`, `scorer_run`, `rag_ingestion`, `tool_call`, `mcp_tool_call`, `model_generation`, `model_step`, `model_inference`.

## Query requests and pagination

| Field | Notes |
|---|---|
| `timeRange` | Required `{ from, to }` ISO; `from` inclusive, `to` exclusive |
| `where` | Optional predicate |
| `orderBy` | One-item array: `startedAt`, `endedAt`, `timeToFirstChunkMs`, `timeToFirstTokenMs`; default `startedAt desc` |
| `page` | Keyset `{ limit, after }`; limit default 100, max 1000 |
| `pagination` | Traces only: numbered `{ page, perPage }`, perPage max 100 |
| `mode: 'delta'`, `after`, `limit` | Traces only: polling; no `orderBy`, `page`, or `pagination` |

CLI responses stay under `data`: `data.traces` or `data.spans`, plus `data.page.next`. Pass `next` unchanged as `page.after` with the identical query. A mismatched cursor returns `409`; a malformed one returns `400`. Delta mode returns `data.deltaCursor` and `data.delta.hasMore`; omitting `after` establishes a watermark and returns no history. Span queries support keyset only and return no total count.

## Aggregate requests

| Field | Notes |
|---|---|
| `timeRange` | Required, up to 365 days |
| `where` | Same predicate as queries |
| `measures` | Required, one or more |
| `groupBy` | Up to two dimensions |
| `interval` | `1m`, `5m`, `15m`, `1h`, `1d` (UTC buckets, empty buckets omitted) |
| `having` | Numeric predicate over measures, applied before ordering |
| `orderBy` | One object `{ field, direction }`; default `count desc` |
| `limit` | Groups, default 100, max 1000 |

Response: `data.rows[]` with `dimensions`, optional `bucket`, `measures`, optional `cost: { coverage, unit }`, plus `data.truncated`. Not paginated.

## Dimensions and measures

Trace dimensions (root span): `entityType`, `entityName`, `environment`, `status`, `serviceName`, `executionSource`, `threadId`, `resourceId`, `userId`, `sessionId`, `organizationId`, `experimentId`, `name`, `spanType`, `entityId`, `outcome`, `stopReason`, `metadata.<key>`. Platform adds `projectId`.

Span dimensions: `name`, `spanType`, `status`, `outcome`, `stopReason`, `entityType`, `entityId`, `entityName`, `parentEntityType`, `parentEntityName`, `rootEntityType`, `rootEntityName`, `environment`, `serviceName`, `executionSource`, context identifiers, `model`, `provider`.

Measures: `count`, `countDistinct.<field>`, `duration.avg|min|max|p50|p90|p95|p99`, `errorCount`, `errorRate`, `tokens.input|output|total|reasoning|cached.sum|avg`, `cost.sum|avg`, `timeToFirstToken.*`, `timeToFirstChunk.*`.

- Token and cost averages divide by usage-bearing traces, not `count`. A `null` cost is unknown; low `cost.coverage` means incomplete spend.
- Span token and cost measures sit on the recording span (usually `model_generation`), not rolled up to `agent_run`.

## Limits and errors

Query planner limits: nesting depth 12, 100 predicate nodes, 8 `spans` clauses, 100 values per `in` set, 1,000 literals, 4,096-byte strings, 128-byte paths, 256 KiB body.

| Error | Meaning |
|---|---|
| `422 TRACE_QUERY_INVALID` / `field_not_allowed` | Invalid request or unsupported gated field |
| `501 *_UNSUPPORTED` | Store lacks the operation or sub-feature |
| `503 TRACE_QUERY_RESOURCE_LIMIT`, `504 TRACE_QUERY_EXECUTION_TIMEOUT` | Narrow the range or filters; `--timeout` does not help |
| `404` | Server lacks the route |
