# Storage checklist

Run this before calling storage done.

## Choice

- [ ] Every feature in use has a domain implemented by the chosen adapter (see `providers.md`)
- [ ] Observational memory or resource working memory, if used, runs on a supporting adapter
- [ ] Observability routed to an adapter that implements it (ClickHouse, PostgreSQL, DuckDB locally)
- [ ] Record size limits checked for DynamoDB, Convex, and D1

## Configuration

- [ ] Each store has a unique `id`
- [ ] Credentials come from env vars, listed in `.env.example`, never committed
- [ ] No `:memory:` or local file database in multi-instance production
- [ ] Absolute `file:` path when Studio and the app share a libSQL file
- [ ] Agent-level `Memory({ storage })` only where an isolated boundary is intended
- [ ] Composite `domains` use exported domain classes; disabled domains set to `false` on purpose

## Schema and lifecycle

- [ ] `init()` runs: automatically via `new Mastra()`, or in a deploy step with `disableInit: true`
- [ ] `mastra.shutdown()` wired to SIGTERM
- [ ] Stores created only to supply a composite domain are closed separately
- [ ] `memory.settled()` awaited before closing storage when observational memory runs

## Growth

- [ ] `retention` set for messages, threads, and spans as policy requires
- [ ] A single scheduler or worker calls `prune()` with `maxRows` or `maxBatches`
- [ ] Disk reclamation plan documented (VACUUM, compact, CHECKPOINT)

## Verification

- [ ] Thread and workflow snapshot survive a process restart
- [ ] Studio shows threads and traces from the configured backends
