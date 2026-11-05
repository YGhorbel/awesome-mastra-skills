---
name: mastra-observability
description: "Set up and use Mastra observability: tracing with spans for every agent run, model call, tool call, and workflow step, exporters to Mastra Storage, Mastra platform, Langfuse, LangSmith, Braintrust, Datadog, Sentry, PostHog, Arize, Laminar, and any OpenTelemetry backend, sampling, custom spans and metadata, PinoLogger logging with trace correlation, automatic duration, token, and cost metrics, and human feedback. Use this skill whenever the user wants to trace or debug an agent, see token usage or cost, send traces to an APM or LLM observability tool, redact sensitive data from traces, configure logging, or record user ratings. Triggers on @mastra/observability, Observability, MastraStorageExporter, MastraPlatformExporter, SensitiveDataFilter, tracingOptions, createChildSpan, SpanType, OtelExporter, OtelBridge, DatadogBridge, LangfuseExporter, PinoLogger, @mastra/loggers, addFeedback, getMetricAggregate, traceId. Also triggers when the user cannot tell why an agent did something."
license: Apache-2.0
metadata:
  category: quality
  catalog_summary: "Tracing, exporters (Langfuse, Datadog, OTel, and more), sampling, custom spans, PinoLogger, metrics and cost, feedback"
  display_order: 3
  docs: https://mastra.ai/docs/observability/overview
---

# Mastra Observability

Configure tracing, logs, metrics, and feedback on a Mastra instance, and send them to Studio, Mastra platform, or any external provider.

---

## When to use

- Turning on tracing for agents, workflows, tools, and model calls
- Choosing and configuring exporters (Mastra Storage, Mastra platform, Langfuse, Datadog, OTel, and others)
- Sampling traces, filtering span types, redacting sensitive data
- Adding custom spans, metadata, tags, or trace names
- Joining Mastra traces to an existing OpenTelemetry or Datadog trace
- Configuring `PinoLogger`, transports, and trace-correlated logs
- Querying token usage, latency, and cost metrics
- Recording user ratings or QA comments against a trace

## When NOT to use

- Scoring output quality with scorers (use `mastra-evals`)
- Datasets and experiments (use `mastra-datasets-experiments`)
- The Studio Metrics, Traces, and Logs views as UI (use `mastra-studio-editor`)
- Hosted observability and platform setup (use `mastra-platform`)
- Querying traces from the CLI (use `mastra-cli-api`)
- Storage adapters in general (use `mastra-storage`)
- Debugging a specific error message (use `mastra-troubleshooting`)

---

## Required inputs

- Where data should go: Studio only, Mastra platform, an external provider, or several
- Storage backend for the `observability` domain (DuckDB local, ClickHouse production, or platform)
- Environment: long-running server or serverless (needs `flush()`)
- Traffic volume and budget (sampling rate, excluded span types)
- Sensitive fields that must never leave the process
- Provider credentials as env vars (see `references/exporters.md`)

---

## The framework: one config, four signals

`new Observability({ configs })` from `@mastra/observability` is passed to `new Mastra({ observability })`. Each named config has a `serviceName`, `exporters`, and optional sampling and processors.

| Signal | Source | Needs |
|---|---|---|
| Traces | Automatic spans for agent runs, model steps, tool calls, workflow steps, memory | An exporter |
| Logs | `logger.info()` and Mastra internals, tagged with `trace_id`/`span_id` | A logger plus observability storage |
| Metrics | Derived from spans: duration, tokens, cost | An analytics store (DuckDB, ClickHouse, `PostgresStoreVNext`) |
| Feedback | `mastra.observability.addFeedback()` | Observability storage |

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core/mastra'
import { LibSQLStore } from '@mastra/libsql'
import { DuckDBStore } from '@mastra/duckdb'
import { MastraCompositeStore } from '@mastra/core/storage'
import { PinoLogger } from '@mastra/loggers'
import { Observability, MastraStorageExporter, MastraPlatformExporter, SensitiveDataFilter } from '@mastra/observability'

export const mastra = new Mastra({
  storage: new MastraCompositeStore({
    id: 'composite-storage',
    default: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
    domains: { observability: await new DuckDBStore().getStore('observability') },
  }),
  logger: new PinoLogger({ name: 'Mastra', level: 'info' }),
  observability: new Observability({
    configs: {
      default: {
        serviceName: 'mastra',
        exporters: [new MastraStorageExporter(), new MastraPlatformExporter()],
        spanOutputProcessors: [new SensitiveDataFilter()],
      },
    },
  }),
})
```

`MastraPlatformExporter` only sends when `MASTRA_PLATFORM_ACCESS_TOKEN` is set. Keep `MastraStorageExporter` next to any external exporter so Studio still shows traces.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/observability/dist/docs/` and the installed types. Otherwise fetch `https://mastra.ai/docs/observability/overview.md`, `https://mastra.ai/docs/observability/tracing/overview.md`, and `https://mastra.ai/reference/observability/tracing/configuration.md`. Trust these over memory.
2. **Install** `@mastra/observability` plus storage (`@mastra/libsql @mastra/duckdb` for local) and any exporter package.
3. **Route the observability domain** to an analytics-capable store with `MastraCompositeStore` so metrics work. LibSQL, MSSQL, and MongoDB store traces but not metrics.
4. **Add exporters.** `MastraStorageExporter` for Studio, `MastraPlatformExporter` for hosted, plus the provider from `references/exporters.md`. Put credentials in env vars.
5. **Protect data.** `SensitiveDataFilter` is auto-applied (configure with the top-level `sensitiveDataFilter`). Use `tracingOptions.hideInput`/`hideOutput` per call.
6. **Control volume.** Set `sampling` (`always`, `never`, `ratio`, `custom`), `excludeSpanTypes`, `spanFilter`, and `serializationOptions`.
7. **Add context.** `requestContextKeys` for user and tenant IDs, `environment` on `Mastra`, `tracingOptions.tags`, `metadata`, `rootSpanName`.
8. **Instrument custom work** with `context?.tracingContext.currentSpan?.createChildSpan()` inside tools and steps.
9. **Configure logging.** `PinoLogger` from `@mastra/loggers`. Set `logging.level` on the observability config. Use `prettyPrint: false` for JSON.
10. **Flush in serverless** with `await mastra.observability.flush()` before the runtime exits.
11. **Verify** in Studio (`npx mastra dev`, Observability tab) or `npx mastra api trace list`.

---

## Deep dive: custom spans and trace context

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const queryTool = createTool({
  id: 'query-db',
  description: 'Run a read-only query',
  inputSchema: z.object({ query: z.string() }),
  execute: async (inputData, context) => {
    const span = context?.tracingContext.currentSpan?.createChildSpan({
      type: 'generic',
      name: 'database-query',
      input: { query: inputData.query },
      requestContext: context?.requestContext, // enables requestContextKeys extraction
    })
    try {
      const rows = await db.query(inputData.query)
      span?.end({ output: rows, metadata: { rowsReturned: rows.length } })
      return { rows }
    } catch (error) {
      span?.error({ error })
      throw error
    }
  },
})
```

Per-call options on `generate()`, `stream()`, and `run.start()`:

```typescript
const result = await agent.generate('Hello', {
  requestContext,
  tracingOptions: {
    tags: ['production', 'experiment-v2'],
    metadata: { userId: 'user-123' },
    traceId: parentTraceId,       // join an external trace
    parentSpanId: parentSpanId,
    hideInput: true,
  },
})
console.log(result.traceId) // undefined when sampled out or tracing is off
```

---

## Failure patterns

- **Traces show in Langfuse but not Studio.** Only the external exporter is configured. Add `new MastraStorageExporter()`.
- **No metrics, cost, or token columns in Studio.** The observability domain is on LibSQL, MSSQL, or MongoDB. Route it to DuckDB, ClickHouse, or `PostgresStoreVNext`.
- **Serverless traces missing.** The function froze before export. Call `await mastra.observability.flush()`.
- **Using `DefaultExporter` or `CloudExporter` in new code.** Both are deprecated aliases. Use `MastraStorageExporter` and `MastraPlatformExporter`.
- **Custom span processor returns `{ ...span }`.** The copy cannot export and is dropped. Mutate and return the same span, or return `undefined` to drop.
- **Replacing the redaction list by accident.** Passing `sensitiveFields` replaces the defaults. Include every default you still need.
- **Expecting tags on child spans.** Tags apply to the root span only.
- **Logs missing from observability storage.** `logging.level` filters them (the logging guide says default `'warn'`). Set `logging: { level: 'info' }`.
- **Invalid external trace IDs.** Trace IDs are 1 to 32 hex chars, span IDs 1 to 16. Invalid values are ignored with a logged error.
- **Unbounded metric queries in production.** Always pass `filters.timestamp`.
- **Feedback dropped.** `addFeedback()` with only `traceId` needs the trace in storage. Configure `MastraStorageExporter`, and check `mastra.observability.addFeedback` exists first.
- **Datadog bridge crashes the bundle.** Add `dd-trace` and its native modules to `bundler.externals`, and import `dd-trace` before anything else.

---

## Output format

A finished observability delivery contains:

- `observability` (and `logger`) configured in `src/mastra/index.ts`
- Storage routing for the `observability` domain suited to the environment
- Exporter credentials listed in `.env.example`, never committed
- Sampling, span filtering, and redaction choices stated with reasons
- `flush()` in serverless handlers
- Evidence: a trace visible in Studio or the provider, with its `traceId`

---

## Reference files

- [`references/api.md`](references/api.md) - `ObservabilityInstanceConfig`, sampling, `SpanType`, span methods, `tracingOptions`, `PinoLogger`, metrics and feedback APIs.
- [`references/exporters.md`](references/exporters.md) - Every exporter and bridge: package, class, constructor, env vars.
- [`references/examples.md`](references/examples.md) - Local dev setup, production multi-exporter, OTel bridge, feedback route, metrics query.
- [`references/checklist.md`](references/checklist.md) - Production observability checklist.

**Live docs**

- https://mastra.ai/docs/observability/overview
- https://mastra.ai/docs/observability/tracing/overview
- https://mastra.ai/docs/observability/logging
- https://mastra.ai/docs/observability/metrics/overview
- https://mastra.ai/docs/observability/feedback
- https://mastra.ai/reference/observability/tracing/configuration
- https://mastra.ai/reference/observability/tracing/spans
- https://mastra.ai/reference/logging/pino-logger
