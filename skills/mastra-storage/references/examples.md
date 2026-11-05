# Storage examples

All examples follow the current docs. Verify before copying into a project on an older version.

## Contents

1. Local development with libSQL
2. Production PostgreSQL with migrations in CI
3. Composite: libSQL plus DuckDB locally, PostgreSQL plus ClickHouse in production
4. Retention with a scheduled prune job

---

## 1. Local development with libSQL

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'

export const mastra = new Mastra({
  storage: new LibSQLStore({
    id: 'mastra-storage',
    // Absolute path so `mastra dev` and the app share one file
    url: 'file:/absolute/path/to/your/project/mastra.db',
  }),
})
```

Install: `npm install @mastra/libsql@latest`. Tables are created on first use.

---

## 2. Production PostgreSQL with migrations in CI

```typescript
// src/mastra/storage.ts
import { PostgresStore } from '@mastra/pg'

export const storage = new PostgresStore({
  id: 'pg-storage',
  connectionString: process.env.DATABASE_URL,
  max: 20,
  disableInit: true, // schema is applied by the deploy step
})
```

```typescript
// scripts/migrate.ts (run once per deploy)
import { storage } from '../src/mastra/storage.ts'

await storage.init()
await storage.close()
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { storage } from './storage'

export const mastra = new Mastra({ storage })

process.on('SIGTERM', async () => {
  await mastra.shutdown() // releases the Postgres pool
})
```

Read data directly when needed:

```typescript
const memoryStore = await storage.getStore('memory')
const thread = await memoryStore?.getThreadById({ threadId: 'thread-123' })
```

---

## 3. Composite: libSQL plus DuckDB locally, PostgreSQL plus ClickHouse in production

```typescript
// src/mastra/storage.ts
import { MastraCompositeStore } from '@mastra/core/storage'
import { LibSQLStore } from '@mastra/libsql'
import { DuckDBStore } from '@mastra/duckdb'
import { PostgresStore } from '@mastra/pg'
import { ObservabilityStorageClickhouseVNext } from '@mastra/clickhouse'

const isDev = process.env.NODE_ENV === 'development'

export const storage = isDev
  ? new MastraCompositeStore({
      id: 'composite-storage',
      default: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
      domains: {
        observability: new DuckDBStore().observability,
      },
    })
  : new MastraCompositeStore({
      id: 'composite-storage',
      default: new PostgresStore({ id: 'pg', connectionString: process.env.DATABASE_URL! }),
      domains: {
        observability: new ObservabilityStorageClickhouseVNext({
          url: process.env.CLICKHOUSE_URL,
          username: process.env.CLICKHOUSE_USERNAME,
          password: process.env.CLICKHOUSE_PASSWORD,
        }),
      },
    })
```

Disable a domain you do not want persisted:

```typescript
new MastraCompositeStore({
  id: 'composite',
  default: new PostgresStore({ id: 'pg', connectionString: process.env.DATABASE_URL }),
  domains: { observability: false }, // no fallback to default
})
```

---

## 4. Retention with a scheduled prune job

```typescript
// src/mastra/storage.ts
import { LibSQLStore } from '@mastra/libsql'

export const storage = new LibSQLStore({
  id: 'mastra-storage',
  url: 'file:./mastra.db',
  retention: {
    memory: {
      messages: { maxAge: '30d' },
      threads: { maxAge: '90d', batchSize: 500 },
    },
    observability: {
      spans: { maxAge: '7d' },
    },
  },
})
```

```typescript
// Wire to your own cron or a single maintenance worker. Mastra never runs it for you.
import { storage } from './storage'

export async function retentionTick() {
  const results = await storage.prune({ maxRows: 100_000, pauseMs: 25 })
  const incomplete = results.filter(r => !r.done)
  if (incomplete.length) {
    console.log(
      'retention still draining:',
      incomplete.map(r => `${r.domain}.${r.table}`),
    )
  }
}
```

One-off aggressive pass without changing the configured policy:

```typescript
await storage.prune({
  retention: { observability: { spans: { maxAge: '1d' } } },
})
```
