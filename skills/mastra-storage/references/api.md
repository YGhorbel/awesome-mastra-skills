# Storage API reference

Distilled from `https://mastra.ai/reference/storage/overview.md`, `https://mastra.ai/reference/storage/composite.md`, and `https://mastra.ai/reference/storage/retention.md`. Verify against the installed version before relying on an option.

## Contents

- Storage domains
- Core memory tables
- Common store methods
- MastraCompositeStore options
- Retention config
- prune() options and result
- Retention-eligible tables
- Retention support by adapter

---

## Storage domains

| Domain | Holds |
|---|---|
| `memory` | Threads, messages, resources (working memory) |
| `workflows` | Workflow run snapshots for suspend and resume |
| `workflowDefinitions` | Persisted dynamic workflow definitions (beta) |
| `scores` | Eval score records |
| `observability` | Traces, spans, metrics, logs, feedback |
| `datasets` | Datasets, versioned items, versions |
| `experiments` | Experiment runs and per-item results |
| `agents` | Stored agent definitions (Editor) |
| `promptBlocks` | Stored prompt blocks (Editor) |
| `scorerDefinitions` | Stored scorer definitions (Editor) |
| `mcpClients`, `mcpServers` | Stored MCP configurations (Editor) |
| `workspaces` | Stored workspace configurations (Editor) |
| `skills` | Stored skills (Editor) |
| `favorites` | Per-user favorites |
| `blobs` | Content-addressed blobs for skill versioning |
| `backgroundTasks` | Background task state |
| `schedules` | Schedules and trigger history |
| `channels` | Channel installations |
| `harness` | Harness session records |
| `toolProviderConnections` | Tool provider connection names |
| `notifications` | Notification records |
| `threadState` | Per-thread task lists and goals |
| `knowledge` | Knowledge nodes and records (experimental) |

---

## Core memory tables

| Table | Key columns |
|---|---|
| Messages (`mastra_messages`) | `id`, `thread_id`, `resourceId`, `content` (JSON `{ format: 2, parts }`), `role`, `createdAt` |
| Threads (`mastra_threads`) | `id`, `resourceId`, `title`, `metadata` (JSON), `createdAt`, `updatedAt` |
| Resources (`mastra_resources`) | `id`, `workingMemory` (text), `metadata`, `createdAt`, `updatedAt` |
| Workflow snapshots | `workflow_name`, `run_id`, `snapshot` (JSON), `createdAt`, `updatedAt` |

---

## Common store methods

| Method | Notes |
|---|---|
| `await storage.init()` | Creates tables and indexes. Automatic when passed to `new Mastra()`. Required when used directly. |
| `await storage.getStore('memory')` | Domain store, for example `memoryStore?.getThreadById({ threadId })`. |
| `storage.stores?.observability` | Domain accessor on adapters that expose `stores`. |
| `await storage.prune(options?)` | Age-based deletion. See below. |
| `await storage.close()` | Release connections. |
| `await mastra.shutdown()` | Closes the instance storage, including composite `default` and `editor` stores. |

Shared constructor flags on most SQL and document adapters: `id`, `disableInit`, `skipDefaultIndexes`, `indexes`, `retention`.

---

## MastraCompositeStore options

Import: `import { MastraCompositeStore } from '@mastra/core/storage'`

| Option | Type | Notes |
|---|---|---|
| `id` | `string` | Unique identifier. |
| `default` | `MastraCompositeStore` | Fallback for domains not in `domains`. |
| `editor` | `MastraCompositeStore` | Store for Editor domains. Beats `default`, loses to `domains`. |
| `domains` | `{ [domain]: DomainStore \| false }` | Per-domain overrides. `false` disables with no fallback. |
| `disableInit` | `boolean` | Call `init()` yourself. |
| `retention` | `RetentionConfig` | Applies to `prune()`. |

Domain classes named in the docs: `MemoryLibSQL` (`@mastra/libsql`); `MemoryPG`, `WorkflowsPG`, `ScoresPG` (`@mastra/pg`); `MemoryStorageMongoDB`, `WorkflowsStorageMongoDB` (`@mastra/mongodb`); `ObservabilityStorageClickhouse`, `ObservabilityStorageClickhouseVNext` (`@mastra/clickhouse`); `new DuckDBStore().observability` (`@mastra/duckdb`).

A store built only to supply one domain (for example `clickhouseStore.stores?.observability`) is not closed by the composite. Close it yourself.

---

## Retention config

```typescript
retention: {
  memory: {
    messages: { maxAge: '30d' },
    threads: { maxAge: '90d', batchSize: 500 },
  },
  observability: { spans: { maxAge: '7d' } },
}
```

| Field | Notes |
|---|---|
| `maxAge` | Number (ms) or string with `ms`, `s`, `m`, `h`, `d`, `w`. Rows older than `now - maxAge` are eligible. |
| `batchSize` | Rows per delete transaction. Default `1000`. |

Type check a separate object with `satisfies RetentionConfig` (`import type { RetentionConfig } from '@mastra/core/storage'`). Unset domains keep data forever.

---

## prune() options and result

| Option | Notes |
|---|---|
| `maxBatches` | Cap batches per table per call. |
| `maxRows` | Cap rows per table per call. |
| `pauseMs` | Delay between batches. |
| `signal` | `AbortSignal`; stops between batches. |
| `retention` | Replace policies for this call only. |

Returns `PruneResult[]`: `{ domain, table, deleted, done }`. `done: false` means call again. `prune()` never runs on its own and never runs `VACUUM`. Indexes on anchor columns are created lazily on the first prune.

---

## Retention-eligible tables

| Domain | Table key | Anchor |
|---|---|---|
| `memory` | `threads`, `messages`, `resources` | `createdAt` |
| `memory` | `runFences` | `retiredAt` |
| `threadState` | `threadState` | `updatedAt` |
| `observability` | `spans` | `startedAt` |
| `observability` | `metrics`, `logs`, `scores`, `feedback` | `timestamp` (vNext only) |
| `scores` | `scorers` | `createdAt` |
| `workflows` | `workflowSnapshot`, `runOwnership` | `updatedAt` |
| `backgroundTasks` | `backgroundTasks` | `completedAt` |
| `experiments` | `experiments` | `completedAt` |
| `notifications` | `notifications` | `createdAt` |
| `harness` | `sessions` | `createdAt` |
| `schedules` | `triggers` | `actual_fire_at` |

The `observational_memory` table cannot be age-pruned. Keep `runOwnership` `maxAge` well above the 30-second lease.

---

## Retention support by adapter

| Adapter | Mechanism | Coverage |
|---|---|---|
| libSQL | `prune()` | All growth domains |
| PostgreSQL | `prune()` | All except `harness`. vNext observability drops day partitions |
| MongoDB | `prune()` or native TTL indexes | All except `threadState` and `harness` |
| DuckDB | `prune()` | Observability signals. Run `CHECKPOINT` after |
| MySQL, MSSQL, Aurora DSQL | `prune()` | Observability spans, run fencing |
| Oracle | `prune()` | Observability spans and logs, run fencing |
| Spanner | `prune()` | Observability spans (and metrics), run fencing |
| DynamoDB, Convex, Cloudflare D1/DO | `prune()` | Run fencing only |
| ClickHouse | Native TTL | Observability, days per signal, `applyRetention()` |

Pruning frees rows but does not shrink files. Reclaim disk with database maintenance (`VACUUM` on self-hosted libSQL, `VACUUM FULL` on PostgreSQL, `compact` on MongoDB) in a maintenance window.
