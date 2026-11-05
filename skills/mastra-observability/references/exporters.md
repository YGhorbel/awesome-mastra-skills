# Observability exporters and bridges

Every exporter and bridge in `https://mastra.ai/integrations/observability/*` and `https://mastra.ai/reference/observability/tracing/exporters/*`. All exporters go in `exporters: [...]` of an `Observability` config. Bridges go in `bridge:`. Explicit constructor options take precedence over env vars. Verify package names and options against the installed version.

## Contents

- Built-in exporters (`@mastra/observability`)
- Provider exporters
- OpenTelemetry exporter providers
- Bridges
- Choosing

---

## Built-in exporters (`@mastra/observability`)

| Class | Sends to | Env vars | Notes |
|---|---|---|---|
| `MastraStorageExporter` | Configured Mastra storage (Studio) | none | Options: `maxBatchSize` (1000), `maxBufferSize` (10000), `maxBatchWaitMs` (5000), `maxRetries` (4), `retryDelayMs` (500), `strategy` (`'auto' \| 'realtime' \| 'batch-with-updates' \| 'insert-only'`). Traces on ClickHouse, PostgreSQL, MSSQL, MongoDB, LibSQL. |
| `MastraPlatformExporter` | Mastra platform | `MASTRA_PLATFORM_ACCESS_TOKEN`, `MASTRA_PROJECT_ID`, `MASTRA_PLATFORM_OBSERVABILITY_ENDPOINT` (1.17.4+, for example EU), `MASTRA_CLOUD_TRACES_ENDPOINT` (legacy, wins) | Added in 1.12.0. Exports only `SPAN_ENDED`. Also sends logs, metrics, scores, feedback. |
| `ConsoleExporter` | stdout | none | Debugging. `new ConsoleExporter(config?)`. |
| `DefaultExporter` | Same as `MastraStorageExporter` | none | Deprecated in 1.12.0. |
| `CloudExporter` | Same as `MastraPlatformExporter` | `MASTRA_CLOUD_ACCESS_TOKEN` | Deprecated in 1.12.0. |

---

## Provider exporters

All support zero-config (`new XExporter()`) when the env vars are set.

| Provider | Package | Import | Required env | Optional env | Explicit options (selection) |
|---|---|---|---|---|---|
| Langfuse | `@mastra/langfuse` | `import { LangfuseExporter } from '@mastra/langfuse'` | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | `LANGFUSE_BASE_URL` | `publicKey`, `secretKey`, `baseUrl`, `environment`, `release`, `realtime` |
| LangSmith | `@mastra/langsmith` | `import { LangSmithExporter } from '@mastra/langsmith'` | `LANGSMITH_API_KEY` | `LANGCHAIN_PROJECT`, `LANGSMITH_BASE_URL` | `apiKey`, `apiUrl`, `projectName`, `callerOptions`, `hideInputs`, `hideOutputs`, `logLevel` |
| Braintrust | `@mastra/braintrust` | `import { BraintrustExporter } from '@mastra/braintrust'` | `BRAINTRUST_API_KEY` | `BRAINTRUST_ENDPOINT` | `apiKey`, `projectName` (default `'mastra-tracing'`), `endpoint`, `logLevel` |
| Datadog LLM Obs | `@mastra/datadog` | `import { DatadogExporter } from '@mastra/datadog'` | `DD_API_KEY`, `DD_LLMOBS_ML_APP` | `DD_SITE`, `DD_ENV` | `mlApp`, `apiKey` |
| Sentry | `@mastra/sentry` | `import { SentryExporter } from '@mastra/sentry'` | `SENTRY_DSN` | `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE` | `dsn`, `environment`, sampling options |
| PostHog | `@mastra/posthog` | `import { PosthogExporter } from '@mastra/posthog'` | `POSTHOG_API_KEY` | `POSTHOG_HOST` | `apiKey`, `host`, `flushAt` (20), `flushInterval` (10000), `serverless`, `defaultDistinctId`, `enablePrivacyMode`. Forwards feedback as `$ai_feedback`. |
| Arize / Phoenix | `@mastra/arize` | `import { ArizeExporter } from '@mastra/arize'` | Phoenix: `PHOENIX_COLLECTOR_ENDPOINT`. Arize AX: `ARIZE_SPACE_ID`, `ARIZE_API_KEY` | `PHOENIX_API_KEY`, `PHOENIX_PROJECT_NAME`, `ARIZE_PROJECT_NAME` | `endpoint`, `apiKey`, `projectName` |
| Arthur | `@mastra/arthur` | `import { ArthurExporter } from '@mastra/arthur'` | `ARTHUR_API_KEY`, `ARTHUR_BASE_URL` | `ARTHUR_TASK_ID` | Task by ID or name (`taskId` wins) |
| Laminar | `@lmnr-ai/lmnr` | `import { Laminar, MastraExporter } from '@lmnr-ai/lmnr'` | `LMNR_PROJECT_API_KEY` | `LMNR_BASE_URL` | Call `Laminar.initialize({ projectApiKey?, baseUrl? })` first, then `new MastraExporter({ realtime? })` |
| Confident AI | `confident-trace` | `import { ConfidentMastraExporter } from 'confident-trace/mastra'` | `CONFIDENT_API_KEY` | `CONFIDENT_OTEL_ENDPOINT` (EU) | `apiKey`, `endpoint` |
| OpenTelemetry | `@mastra/otel-exporter` plus a protocol package | `import { OtelExporter } from '@mastra/otel-exporter'` | per provider (below) | | `provider: { <name>: {...} }` |

Every exporter accepts `customSpanFormatter`. Langfuse also exports `withLangfusePrompt` for prompt linking. Braintrust and Langfuse honor `tracingOptions.nestUnderParent`.

---

## OpenTelemetry exporter providers

Install the base package plus one protocol package:

| Protocol | Install |
|---|---|
| HTTP/Protobuf (SigNoz, New Relic, Sentry, Laminar, MLflow, Latitude, telemetry.dev) | `npm install @mastra/otel-exporter@latest @opentelemetry/exporter-trace-otlp-proto` |
| HTTP/JSON | `npm install @mastra/otel-exporter@latest @opentelemetry/exporter-trace-otlp-http` |
| gRPC (Dash0) | `npm install @mastra/otel-exporter@latest @opentelemetry/exporter-trace-otlp-grpc @grpc/grpc-js` |

| `provider` key | Env vars |
|---|---|
| `dash0` | `DASH0_API_KEY`, `DASH0_ENDPOINT` (required), `DASH0_DATASET` |
| `signoz` | `SIGNOZ_API_KEY` (required), `SIGNOZ_REGION`, `SIGNOZ_ENDPOINT` |
| `newrelic` | `NEW_RELIC_LICENSE_KEY` (required), `NEW_RELIC_ENDPOINT` |
| `traceloop` | `TRACELOOP_API_KEY` (required), `TRACELOOP_DESTINATION_ID`, `TRACELOOP_ENDPOINT` |
| `laminar` | `LMNR_PROJECT_API_KEY` (required), `LAMINAR_ENDPOINT` |
| `custom` | `endpoint`, headers, and protocol in code. Used for Sentry OTLP, Sazabi, MLflow, and others. |

```typescript
import { OtelExporter } from '@mastra/otel-exporter'

new OtelExporter({ provider: { dash0: {} } }) // zero-config from env
```

The exporter also has a `signals` option to send logs (install a matching `@opentelemetry/exporter-logs-otlp-*` package). Span tags appear as `mastra.tags`.

---

## Bridges

Bridges make Mastra spans part of an existing tracer instead of exporting separately. No Mastra exporter is required, but you may add one.

| Bridge | Package | Setup |
|---|---|---|
| `OtelBridge` | `@mastra/otel-bridge` | Start an OTel `NodeSDK` in an instrumentation file loaded before app code, then `bridge: new OtelBridge()`. Forwards logs to the global `LoggerProvider` if one is registered. |
| `DatadogBridge` | `@mastra/datadog` plus `dd-trace` | `import tracer from 'dd-trace'` and `tracer.init({ service, env, version })` at the very top of the entry file, then `bridge: new DatadogBridge({ mlApp: process.env.DD_LLMOBS_ML_APP! })`. Add `dd-trace`, `@datadog/native-metrics`, `@datadog/native-appsec`, `@datadog/native-iast-taint-tracking`, `@datadog/pprof` to `bundler.externals`. Env: `DD_SERVICE`, `DD_ENV`, `DD_VERSION`, `DD_LLMOBS_ML_APP`. |

---

## Choosing

| Need | Use |
|---|---|
| Local debugging in Studio | `MastraStorageExporter` with DuckDB for the observability domain |
| Hosted, no backend to run | `MastraPlatformExporter` |
| LLM-focused tracing and prompt management | Langfuse, LangSmith, Braintrust, Arize, Laminar, Confident AI |
| Existing APM | `DatadogExporter` or `DatadogBridge`, `SentryExporter`, or `OtelExporter` |
| Product analytics with LLM events | `PosthogExporter` |
| App already instrumented with OTel | `OtelBridge` |

Keep `MastraStorageExporter` alongside external exporters when the team uses Studio.
