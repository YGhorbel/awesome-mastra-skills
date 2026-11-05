---
name: mastra-storage
description: "Configure the Mastra persistence layer: pick and wire a storage adapter (LibSQLStore, PostgresStore, MongoDBStore, and 20 more), set it on the Mastra instance or a single agent's Memory, split storage domains across databases with MastraCompositeStore, and keep tables bounded with retention and storage.prune(). Use this skill whenever the user needs memory, workflow snapshots, traces, scores, or schedules to survive restarts, moves from local SQLite to a production database, sees data vanish between runs, hits a record size limit, or wants observability in a separate database. Triggers on Mastra storage, storage adapter, @mastra/libsql, @mastra/pg, @mastra/mongodb, @mastra/clickhouse, @mastra/duckdb, MastraCompositeStore, storage domains, MemoryLibSQL, WorkflowsPG, retention, prune, disableInit, storage.init, getStore, mastra.shutdown. Also triggers when choosing a database for a Mastra deployment."
license: Apache-2.0
metadata:
  category: memory-and-knowledge
  catalog_summary: "Storage adapters, instance vs agent storage, composite domain routing, retention and pruning, provider table"
  display_order: 6
  docs: https://mastra.ai/docs/storage
---

# Mastra Storage

Choose, configure, and operate the database that keeps Mastra state (memory, workflow snapshots, traces, scores, schedules) across restarts and processes.

---

## When to use

- Adding persistence to a new Mastra project
- Moving from `:memory:` or a local file to a managed production database
- Picking an adapter for a platform (Cloudflare, AWS, Convex, Spanner, Oracle)
- Routing domains to different databases, such as observability to ClickHouse
- Giving one agent's memory its own database
- Bounding table growth with retention policies and `prune()`
- Running migrations separately from app start (`disableInit`)
- Debugging lost data, "Memory requires a storage provider", or size limit errors

## When NOT to use

- Memory behavior: history, working memory, threads (use `mastra-memory`)
- Vector databases for embeddings (use `mastra-vector-stores`)
- Semantic recall configuration (use `mastra-semantic-recall`)
- Trace exporters and sampling (use `mastra-observability`)
- Mastra Platform managed database (use `mastra-platform`)
- Workflow suspend and resume logic (use `mastra-workflow-suspend-resume`)
- Deploying the server that uses the database (use `mastra-deployment`)

---

## Required inputs

- Which features need persistence: memory, workflows, observability, evals, schedules, background tasks
- Environment: local dev, single server, multi-process, serverless, edge
- Existing databases the team already runs
- Expected trace volume (decides whether observability needs its own backend)
- Retention requirements for messages, threads, and spans
- Whether schema migrations may run at app start

---

## The framework: domains, adapters, scope

Storage is split into **domains**. An adapter implements some of them.

| Domain | Holds | Fits |
|---|---|---|
| `memory` | Threads, messages, resources, working memory | Transactional DB: libSQL, PostgreSQL, MongoDB |
| `workflows` | Suspend and resume snapshots | Reliable persistent DB |
| `observability` | Traces, spans, metrics, logs, feedback | OLAP: ClickHouse (prod), DuckDB (local) |
| `scores`, `datasets`, `experiments` | Eval data | Any persistent DB |
| `schedules`, `backgroundTasks`, `threadState` | Harness state | Adapter must implement the domain |

The full list (24 domains, including Editor domains such as `agents` and `skills`) is in `references/api.md`.

Two scopes:

```typescript
// Instance level: shared by every agent, workflow, and feature
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'

export const mastra = new Mastra({
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
})
```

```typescript
// Agent level: overrides instance storage for this agent's memory only
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { PostgresStore } from '@mastra/pg'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support agent',
  instructions: 'Answer customer support questions.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    storage: new PostgresStore({
      id: 'support-agent-storage',
      connectionString: process.env.SUPPORT_AGENT_DATABASE_URL,
    }),
  }),
})
```

Mastra creates tables on first use. Passing a store to `new Mastra()` calls `init()` for you; using a store directly needs `await storage.init()`.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the adapter's types. Otherwise fetch `https://mastra.ai/docs/storage.md` and the adapter page, for example `https://mastra.ai/integrations/databases/postgresql.md`. Trust these over memory.
2. **List the domains you need.** Memory only? Add workflows, observability, schedules as features demand.
3. **Pick the adapter.** Local: `LibSQLStore` with `file:`. Production default: `PostgresStore`. Check `references/providers.md` for domain gaps (many adapters lack observability) and features (observational memory and resource working memory need specific adapters).
4. **Install and configure.** `npm install @mastra/<adapter>@latest`. Always pass `id`. Read secrets from env vars.
5. **Choose scope.** Instance storage by default. Agent-level `Memory({ storage })` only for an isolated memory boundary.
6. **Split domains if needed.** `MastraCompositeStore` with `default` plus `domains` overrides, for example observability to ClickHouse.
7. **Set retention.** Add `retention` on the store, and call `storage.prune()` from your own scheduler.
8. **Plan migrations.** For CI-managed schemas set `disableInit: true` and run `storage.init()` in a deploy step.
9. **Shut down cleanly.** `await mastra.shutdown()` closes the composite's stores. Close stores you built only to supply a domain yourself.
10. **Test persistence.** Restart the process and confirm a thread and a suspended workflow are still there. Check Studio shows them.

---

## Deep dive: composite storage

```typescript
import { Mastra } from '@mastra/core'
import { MastraCompositeStore } from '@mastra/core/storage'
import { MemoryPG, WorkflowsPG, ScoresPG } from '@mastra/pg'
import { ObservabilityStorageClickhouseVNext } from '@mastra/clickhouse'

export const mastra = new Mastra({
  storage: new MastraCompositeStore({
    id: 'composite',
    domains: {
      memory: new MemoryPG({ connectionString: process.env.DATABASE_URL }),
      workflows: new WorkflowsPG({ connectionString: process.env.DATABASE_URL }),
      scores: new ScoresPG({ connectionString: process.env.DATABASE_URL }),
      observability: new ObservabilityStorageClickhouseVNext({
        url: process.env.CLICKHOUSE_URL,
        username: process.env.CLICKHOUSE_USERNAME,
        password: process.env.CLICKHOUSE_PASSWORD,
      }),
    },
  }),
})
```

Resolution order per domain: explicit `domains` entry, then `editor` store (Editor domains), then `default`. A domain set to `false` is disabled and does not fall back. Mix only domain classes the packages export (`MemoryLibSQL`, `WorkflowsPG`, `MemoryStorageMongoDB`, and similar).

---

## Failure patterns

- **Data gone after restart.** `url: ':memory:'` or no storage at all. Use `file:./mastra.db` locally and a server database in production.
- **Studio and app show different data.** Relative `file:` paths resolve per process. Use an absolute path.
- **Missing `id`.** The memory quickstart says to add `id` to `LibSQLStore`, and most adapters list it. Always set a unique `id`.
- **Tables never created.** Store used directly without `init()`, or `disableInit: true` with no migration step. Call `await storage.init()`.
- **Traces missing in Studio.** The adapter lacks the observability domain (Convex, DynamoDB, D1, Cloudflare KV/DO, LanceDB, Upstash). Route `observability` to ClickHouse or DuckDB with composite storage.
- **Save fails on attachments.** DynamoDB 400 KB items, Convex and D1 1 MiB records. Upload attachments in an input processor (see `mastra-memory`).
- **Observational memory or resource working memory errors.** Adapter does not support them. See the feature columns in `references/providers.md`.
- **Unbounded growth.** No retention. Configure `retention` and schedule `prune()`; it never runs on its own.
- **Process hangs on exit.** Open pools. Call `await mastra.shutdown()` and close extra stores.
- **Local file DB in multi-instance production.** Each instance writes its own file. Use a shared server database.
- **Upstash bill spikes.** Pay-as-you-go pricing with high command volume. Use a fixed plan.

---

## Output format

A finished storage delivery contains:

- Adapter installed and configured in `src/mastra/index.ts` with an `id` and env-based credentials
- Domain coverage confirmed for every feature in use, or a composite store filling the gaps
- `.env.example` listing connection variables
- Retention config plus the scheduled job that calls `prune()`, if data grows
- Shutdown handling (`mastra.shutdown()`)
- Evidence: data survives a restart and appears in Studio

---

## Reference files

- [`references/api.md`](references/api.md) - Domains, composite options, store methods, retention config and `prune()`.
- [`references/providers.md`](references/providers.md) - Every database adapter: package, class, constructor shape, domain and feature notes.
- [`references/examples.md`](references/examples.md) - Local libSQL, production PostgreSQL, composite with DuckDB and ClickHouse, retention job.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for storage.

**Live docs**

- https://mastra.ai/docs/storage
- https://mastra.ai/reference/storage/overview
- https://mastra.ai/reference/storage/composite
- https://mastra.ai/reference/storage/retention
- https://mastra.ai/integrations/databases/libsql
- https://mastra.ai/integrations/databases/postgresql
