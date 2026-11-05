# Observability API reference

Distilled from `https://mastra.ai/reference/observability/*.md`, `https://mastra.ai/reference/logging/pino-logger.md`, and `https://mastra.ai/docs/observability/*.md`. Verify against the installed version.

## Contents

- Observability registry config
- Instance config
- Sampling
- Span types
- Span methods
- tracingOptions
- SensitiveDataFilter and custom processors
- Logging
- Metrics
- Feedback

---

## `new Observability(config)` (`@mastra/observability`)

| Field | Notes |
|---|---|
| `configs` | `Record<string, InstanceConfig \| ObservabilityInstance>`. Named configs. |
| `configSelector` | `(options: { requestContext? }, availableConfigs) => string \| undefined`. Picks the config at runtime. |
| `default` | `{ enabled?: boolean }`. Default config with `MastraStorageExporter` and `MastraPlatformExporter`. |
| `sensitiveDataFilter` | `boolean \| SensitiveDataFilterOptions`. Default `true` (auto-applied to plain configs). |

Registry methods: `registerInstance`, `getInstance`, `getDefaultInstance`, `getSelectedInstance`, `listInstances`, `hasInstance`, `setConfigSelector`, `unregisterInstance`, `clear`, `shutdown`. Runtime: `mastra.observability.flush()`, `mastra.observability.addFeedback?()`.

Set `environment: 'production'` on `new Mastra({...})` to tag every signal. Without it, `mastra dev` runs report `development`, else `NODE_ENV`.

## Instance config

| Field | Default | Notes |
|---|---|---|
| `serviceName` | required | Service name on exported data. |
| `sampling` | `{ type: 'always' }` | See Sampling. |
| `exporters` | none | `ObservabilityExporter[]`. |
| `bridge` | none | `new OtelBridge()` or `new DatadogBridge({ mlApp })`. Shown in integration docs. |
| `spanOutputProcessors` | none | Run before export, apply to all exporters. |
| `includeInternalSpans` | `false` | Include Mastra-internal spans. |
| `excludeSpanTypes` | none | `SpanType[]` dropped first. |
| `spanFilter` | none | `(span: AnyExportedSpan) => boolean`. Runs last. Throwing keeps the span. |
| `requestContextKeys` | none | Keys (dot paths allowed) copied into span metadata. |
| `serializationOptions` | see below | `maxStringLength` 131072, `maxDepth` 8, `maxArrayLength` 50, `maxObjectKeys` 50. |
| `logging` | `{ enabled: true }` | `level`: `'debug' \| 'info' \| 'warn' \| 'error' \| 'fatal'`. Docs disagree on the default level (logging guide `'warn'`, config reference `'debug'`). Set it explicitly. |

Export order: drop internal spans, `excludeSpanTypes`, `spanOutputProcessors`, `spanFilter`.

## Sampling

```typescript
type SamplingStrategy =
  | { type: 'always' }
  | { type: 'never' }
  | { type: 'ratio'; probability: number } // 0..1
  | { type: 'custom'; sampler: (options?: { requestContext?; metadata? }) => boolean }
```

Live scorers skip runs whose trace was sampled out.

## Span types (`SpanType` from `@mastra/core/observability`)

`AGENT_RUN`, `GENERIC`, `MODEL_GENERATION`, `MODEL_STEP`, `MODEL_INFERENCE`, `MODEL_CHUNK`, `MCP_TOOL_CALL`, `MCP_SERVER_REQUEST`, `PROCESSOR_RUN`, `MEMORY_OPERATION`, `WORKSPACE_ACTION`, `SKILL_ACTION`, `AGENT_SIGNAL`, `TOOL_CALL`, `CLIENT_TOOL_CALL`, `PROVIDER_TOOL_CALL`, `WORKFLOW_RUN`, `WORKFLOW_STEP`, `WORKFLOW_CONDITIONAL`, `WORKFLOW_CONDITIONAL_EVAL`, `WORKFLOW_PARALLEL`, `WORKFLOW_LOOP`, `WORKFLOW_SLEEP`, `WORKFLOW_WAIT_EVENT`. Check the installed enum for the full list.

Common noise reduction: `excludeSpanTypes: [SpanType.MODEL_CHUNK, SpanType.MODEL_STEP]`.

Execution outcome fields on spans: `outcome` (`success`, `error`, `abort`, `interrupted`, `suspend`, `limit`, `blocked`, `unknown`), `stopReason` (for example `max_steps`, `guardrail`, `timeout`), `stopReasonContext`.

## Span methods

Get the current span in tools and steps from `context?.tracingContext.currentSpan`.

| Method | Notes |
|---|---|
| `createChildSpan({ type, name, input?, metadata?, requestContext? })` | Child inherits the trace. Pass `requestContext` to extract `requestContextKeys`. |
| `createEventSpan({ type, name, output? })` | Zero-duration event. No `input`. |
| `update({ input?, output?, metadata?, attributes? })` | While active. |
| `end({ output?, metadata?, attributes? })` | Ends and exports. |
| `error({ error, metadata?, endSpan? })` | Records `errorInfo`. |
| `isRootSpan`, `isValid`, `exportSpan()` | Properties and helpers. |

Base fields: `id`, `traceId`, `name`, `type`, `startTime`, `endTime`, `attributes`, `metadata`, `input`, `output`, `errorInfo`, `requestContext`, `isEvent`.

## `tracingOptions`

Accepted by `agent.generate()`, `agent.stream()`, and `run.start()`.

| Option | Notes |
|---|---|
| `tags` | String labels on the root span. |
| `metadata` | Key-value data. `metadata.environment` overrides `Mastra.environment`. |
| `requestContextKeys` | Added to config-level keys. |
| `rootSpanName` | Renames the root span (not used by OTel and Langfuse names). |
| `hideInput`, `hideOutput` | Remove input or output from all spans at export. |
| `traceId`, `parentSpanId` | Join an external trace (1 to 32 and 1 to 16 hex chars). |
| `nestUnderParent` | Nest under an earlier Mastra run. Helper: `nestUnderRun(result)` from `@mastra/core/observability`. |

Results expose `traceId` (`result.traceId`, `streamResult.traceId`, workflow `result.traceId`, `getWorkflowState()`).

## `SensitiveDataFilter` and custom processors

`new SensitiveDataFilter({ sensitiveFields?, redactionToken? = '[REDACTED]', redactionStyle? = 'full' })`. Styles: `'full' | 'partial' | 'indexed'`. Default fields: `password`, `token`, `secret`, `key`, `apikey`, `auth`, `authorization`, `bearer`, `bearertoken`, `jwt`, `credential`, `clientsecret`, `privatekey`, `refresh`, `ssn`. Matching ignores case and separators.

Custom processor: implement `SpanOutputProcessor` (`name`, `process(span): AnySpan | undefined`, `shutdown()`), types from `@mastra/core/observability`. Mutate and return the same instance.

Per-exporter formatting: `customSpanFormatter` option on an exporter, type `CustomSpanFormatter`, may be async. Combine with `chainFormatters([...])` from `@mastra/observability`.

---

## Logging

`new PinoLogger(options)` from `@mastra/loggers`:

| Option | Notes |
|---|---|
| `name` | Label. |
| `level` | `'debug' \| 'info' \| 'warn' \| 'error'`. |
| `transports` | `Record<string, LoggerTransport>`. `FileTransport` (`@mastra/loggers/file`), `UpstashTransport` (`@mastra/loggers/upstash`), or `createCustomTransport(stream)` (`@mastra/core/logger`). |
| `overrideDefaultTransports` | Disable the console transport. |
| `prettyPrint` | Default `true`. `false` writes JSON lines. |
| `redact`, `formatters`, `serializers`, `mixin`, `customLevels` | Forwarded to Pino. |

`new Mastra({ loggerOptions: { correlation?: true, export?: true } })` controls `trace_id`/`span_id` injection and forwarding to observability storage.

Get a logger: `mastra.getLogger()` in steps, `context?.mastra.getLogger()` in tools. Methods: `debug`, `info`, `warn`, `error`, each `(message, data?)`.

Query logs: `new MastraClient().listLogsVNext({ filters, pagination, orderBy })` or `npx mastra api log list`.

## Metrics

Automatic metric names: `mastra_agent_duration_ms`, `mastra_tool_duration_ms`, `mastra_workflow_duration_ms`, `mastra_model_duration_ms`, `mastra_processor_duration_ms`, `mastra_model_total_input_tokens`, `mastra_model_total_output_tokens`, plus detailed categories (`mastra_model_input_cache_read_tokens`, `mastra_model_output_reasoning_tokens`, ...). Durations carry a `status` label (`ok` or `error`). Cost comes from provider-reported cost or the models.dev price snapshot (`MASTRA_AUTO_REFRESH_PRICING`, `MASTRA_OFFLINE`).

Query from the observability store (`await mastra.getStorage()?.getStore('observability')`) or `MastraClient`:

| Method | Notes |
|---|---|
| `getMetricAggregate({ name: string[], aggregation, filters?, comparePeriod? })` | `{ value, previousValue?, changePercent?, estimatedCost?, costUnit? }`. |
| `getMetricBreakdown`, `getMetricTimeSeries`, `getMetricPercentiles` | Grouped, time-bucketed, percentile queries. |
| `listMetrics` | Store and HTTP only, not on the client. |

Always pass `filters.timestamp: { start, end? }`. HTTP: `POST /api/observability/metrics/aggregate` and siblings. CLI: `mastra api metric`.

## Feedback

| Call | Notes |
|---|---|
| `mastra.observability.addFeedback?.({ traceId, spanId?, feedback: { feedbackSource?, feedbackType, value, comment? } })` | Optional method, check it exists. Rehydrates the trace from storage. |
| `store.createFeedback({ feedback: { feedbackId, timestamp, feedbackType, value, traceId?, spanId?, feedbackSource?, comment?, tags?, experimentId? } })` | Direct storage write. |
| `store.listFeedback({ filters, pagination, orderBy })` | Filters include `traceId`, `feedbackType`, `feedbackSource`, `entityName`, `environment`, `tags`, `timestamp`. |
| `store.deleteFeedback({ feedbackIds })` | Up to 1,000 per call, idempotent. |
| `getFeedbackAggregate`, `getFeedbackBreakdown`, `getFeedbackTimeSeries` | Numeric `value` analytics. |

Assistant messages carry `content.metadata.traceId`. In AI SDK routes, return it from `messageMetadata: ({ part, traceId }) => part.type === 'start' ? { traceId } : undefined`. PostHog and Mastra platform exporters forward feedback.
