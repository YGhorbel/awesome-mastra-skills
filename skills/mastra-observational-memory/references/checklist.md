# Observational Memory checklist

Run this before calling OM done.

## Fit

- [ ] Threads are long or tool-heavy enough to need compression
- [ ] Not combined with working memory or semantic recall without a reason (overlap adds latency and cost)
- [ ] `@mastra/memory` is 1.1.0 or newer (1.10.0+ for `ModelByInputTokens`)

## Setup

- [ ] Storage is libSQL, PostgreSQL, MongoDB, MySQL, Convex, or OracleDB
- [ ] Every call passes a stable `thread` and `resource`
- [ ] Clients send only the new message
- [ ] `lastMessages` is not used as the history control (ignored under OM)
- [ ] Observer and Reflector models chosen (`'auto'` or pinned, 128K+ context, fast)
- [ ] Provider keys for the OM models exist in `.env.example`
- [ ] `scope: 'resource'` not used (deprecated)

## Tuning

- [ ] `activateAfterIdle` set when relying on prompt caching (`'auto'` or the real TTL)
- [ ] `activateOnProviderChange: true` if the agent switches models mid-thread
- [ ] `shareTokenBudget` only with `observation.bufferTokens: false`
- [ ] `observeOnContextOverflow` left at `true`
- [ ] `failurePolicy` chosen for both observation and reflection
- [ ] `observeAttachments` set for text-only Observer models
- [ ] Sensitive or bulky tool results filtered in `beforeObservation` (for example `skillResultRedactor()`)

## Operations

- [ ] `await memory.settled()` before closing storage in shutdown hooks and tests
- [ ] Multi-process deployments share one storage and one PubSub backend with leases
- [ ] OM model spend tracked through `onObservationEnd` / `onReflectionEnd` usage or traces
- [ ] A full observe and reflect cycle seen in Studio's Memory tab or `data-om-*` parts
- [ ] `OM_DEBUG=1` documented for incident debugging
