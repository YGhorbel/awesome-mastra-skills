# Observability checklist

Run this before calling observability done.

## Setup

- [ ] `@mastra/observability` installed and `new Observability({ configs })` on the `Mastra` instance
- [ ] `serviceName` set per config
- [ ] Observability domain routed to an analytics store (DuckDB local, ClickHouse or `PostgresStoreVNext` in production, or Mastra platform)
- [ ] `MastraStorageExporter` kept next to external exporters when the team uses Studio
- [ ] No deprecated `DefaultExporter` or `CloudExporter` in new code
- [ ] Exporter credentials in env vars and `.env.example`, never committed
- [ ] `environment` set on `Mastra`

## Data protection

- [ ] `SensitiveDataFilter` active, field list reviewed (custom list includes needed defaults)
- [ ] `hideInput`/`hideOutput` on calls that carry credentials or regulated data
- [ ] PinoLogger `redact` configured for sensitive log fields
- [ ] Retention configured for observability data

## Volume and cost

- [ ] Sampling strategy chosen for production traffic
- [ ] Noisy span types excluded (`MODEL_CHUNK`, `MODEL_STEP`) where per-span billing applies
- [ ] `serializationOptions` sized for payloads
- [ ] Metric queries always include a time range

## Runtime

- [ ] `await mastra.observability.flush()` in serverless handlers
- [ ] External trace context propagated (`traceId`/`parentSpanId` or a bridge)
- [ ] Custom spans in critical tools end on success and record `error()` on failure
- [ ] `logging.level` set explicitly for observability storage
- [ ] JSON logs (`prettyPrint: false`) for log aggregators

## Verification

- [ ] A trace visible in Studio or the provider, with model, tool, and step spans
- [ ] Token and cost columns visible (metrics store working)
- [ ] A log line correlates to its trace
- [ ] Feedback written and listed for a sample trace, if feedback is used
