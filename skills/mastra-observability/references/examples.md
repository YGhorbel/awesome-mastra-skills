# Observability examples

All examples follow the current docs. Verify against the installed version before copying.

## Contents

1. Production config with an external exporter, sampling, and filtering
2. Per-environment configs with configSelector
3. OpenTelemetry bridge
4. Collect user feedback against a trace
5. Query token usage and latency

---

## 1. Production config with an external exporter, sampling, and filtering

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { SpanType } from '@mastra/core/observability'
import { PinoLogger } from '@mastra/loggers'
import { Observability, MastraStorageExporter, MastraPlatformExporter } from '@mastra/observability'
import { LangfuseExporter } from '@mastra/langfuse'

export const mastra = new Mastra({
  environment: 'production',
  logger: new PinoLogger({ name: 'Mastra', level: 'info', prettyPrint: false }),
  observability: new Observability({
    configs: {
      default: {
        serviceName: 'support-api',
        sampling: { type: 'ratio', probability: 0.1 },
        requestContextKeys: ['userId', 'tenantId'],
        exporters: [new MastraStorageExporter(), new MastraPlatformExporter(), new LangfuseExporter()],
        excludeSpanTypes: [SpanType.MODEL_CHUNK, SpanType.MODEL_STEP],
        spanFilter: span => !(span.type === SpanType.TOOL_CALL && span.attributes?.success),
        serializationOptions: { maxStringLength: 2048, maxDepth: 6 },
        logging: { enabled: true, level: 'info' },
      },
    },
    sensitiveDataFilter: {
      sensitiveFields: ['password', 'token', 'secret', 'apikey', 'authorization', 'customerSecret'],
      redactionStyle: 'partial',
    },
  }),
})
```

`.env.example`: `LANGFUSE_PUBLIC_KEY=`, `LANGFUSE_SECRET_KEY=`, `LANGFUSE_BASE_URL=`, `MASTRA_PLATFORM_ACCESS_TOKEN=`, `MASTRA_PROJECT_ID=`. Configure storage separately (ClickHouse for the observability domain in production).

---

## 2. Per-environment configs with configSelector

```typescript
import { Mastra } from '@mastra/core'
import { Observability, MastraStorageExporter } from '@mastra/observability'
import { LangfuseExporter } from '@mastra/langfuse'

const storageExporter = new MastraStorageExporter()
const langfuseExporter = new LangfuseExporter()

export const mastra = new Mastra({
  observability: new Observability({
    configs: {
      development: { serviceName: 'my-service-dev', exporters: [storageExporter] },
      production: { serviceName: 'my-service-prod', exporters: [storageExporter, langfuseExporter] },
    },
    configSelector: () => process.env.NODE_ENV || 'development',
  }),
})
```

In serverless handlers, call `await mastra.observability.flush()` before returning.

---

## 3. OpenTelemetry bridge

```typescript
// instrumentation.ts (load before app code)
import { NodeSDK } from '@opentelemetry/sdk-node'
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-proto'
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base'
import { W3CTraceContextPropagator } from '@opentelemetry/core'

const sdk = new NodeSDK({
  serviceName: 'my-service',
  spanProcessors: [
    new BatchSpanProcessor(
      new OTLPTraceExporter({
        url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces',
      }),
    ),
  ],
  instrumentations: [getNodeAutoInstrumentations()],
  textMapPropagator: new W3CTraceContextPropagator(),
})

sdk.start()
export { sdk }
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { Observability } from '@mastra/observability'
import { OtelBridge } from '@mastra/otel-bridge'

export const mastra = new Mastra({
  observability: new Observability({
    configs: {
      default: { serviceName: 'my-service', bridge: new OtelBridge() },
    },
  }),
})
```

Without a bridge, join an existing trace per call instead:

```typescript
import { trace } from '@opentelemetry/api'

const spanContext = trace.getActiveSpan()?.spanContext()
const result = await agent.generate(userMessage, {
  tracingOptions: spanContext
    ? { traceId: spanContext.traceId, parentSpanId: spanContext.spanId }
    : undefined,
})
```

---

## 4. Collect user feedback against a trace

Server side, after the client sends `{ traceId, rating }` for a message it owns:

```typescript
export async function recordRating(traceId: string, rating: 1 | -1, comment?: string) {
  if (!mastra.observability.addFeedback) {
    throw new Error('Feedback is not supported by the active observability implementation')
  }

  await mastra.observability.addFeedback({
    traceId,
    feedback: {
      feedbackSource: 'user',
      feedbackType: 'thumbs',
      value: rating,
      comment,
    },
  })
}
```

Get the `traceId` for a stored message from memory:

```typescript
const memory = await mastra.getAgent('weatherAgent').getMemory()
const { messages } = await memory!.recall({ threadId, perPage: false })
const traceId = messages.find(m => m.id === messageId)?.content.metadata?.traceId
```

Check that the caller owns a message with that `traceId` before writing, because the value comes from the client. `MastraStorageExporter` must be configured so the trace can be rehydrated.

---

## 5. Query token usage and latency

```typescript
const observability = await mastra.getStorage()?.getStore('observability')
if (!observability) throw new Error('Observability storage is not configured')

const tokens = await observability.getMetricAggregate({
  name: ['mastra_model_total_input_tokens', 'mastra_model_total_output_tokens'],
  aggregation: 'sum',
  filters: { timestamp: { start: new Date(Date.now() - 24 * 60 * 60 * 1000) } },
  comparePeriod: 'previous_period',
})

const latency = await observability.getMetricAggregate({
  name: ['mastra_agent_duration_ms'],
  aggregation: 'avg',
  filters: { timestamp: { start: new Date(Date.now() - 60 * 60 * 1000) } },
})

console.log(tokens.value, tokens.estimatedCost, tokens.costUnit, latency.value)
```

Metrics require DuckDB, ClickHouse, or `PostgresStoreVNext` for the observability domain.
