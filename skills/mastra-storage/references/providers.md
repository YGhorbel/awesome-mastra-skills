# Storage providers

One row per adapter documented under `https://mastra.ai/integrations/databases/`, plus `@mastra/turso`. Constructor shapes are the minimal form from each page. Verify on the adapter page before use: options change between releases.

## Contents

- Adapter table
- Feature support matrix
- Size limits and caveats
- Picking an adapter

---

## Adapter table

| Adapter | Package | Class | Minimal constructor | Notes |
|---|---|---|---|---|
| libSQL / Turso Cloud | `@mastra/libsql` | `LibSQLStore` | `new LibSQLStore({ id, url: 'file:./mastra.db' })` | `url` also `:memory:` or `libsql://...` with `authToken`. Embedded replica via `syncUrl`, `syncInterval`. Default for local dev. Pairs with `LibSQLVector`. |
| PostgreSQL | `@mastra/pg` | `PostgresStore` | `new PostgresStore({ id, connectionString })` | Or `host`/`port`/`database`/`user`/`password`, or `pool`. `schemaName`, `ssl`, `max` (20), `indexes`. `PostgresStoreVNext` adds event-sourced, day-partitioned observability. Pairs with `PgVector`. |
| Neon | `@mastra/pg` | `PostgresStore` | `new PostgresStore({ id, connectionString: process.env.DATABASE_URL })` | Use Neon's pooled connection string. No separate package. |
| ClickHouse Managed Postgres | `@mastra/pg` | `PostgresStore` | `new PostgresStore({ id, connectionString, ssl: { ca, rejectUnauthorized: true } })` | Direct URL with PgBouncer off; CA bundle from instance settings. |
| Aurora DSQL | `@mastra/dsql` | `DSQLStore` | `new DSQLStore({ id, host: 'abc123.dsql.us-east-1.on.aws' })` | IAM auth. `region` from host. `maxLifetimeSeconds` under 3600. No pgvector: use another vector store such as `@mastra/s3vectors`. |
| MongoDB | `@mastra/mongodb` | `MongoDBStore` | `new MongoDBStore({ id, uri, dbName })` | `url` is deprecated. `indexes` supports TTL indexes. Pairs with `MongoDBVector`. Domain classes `MemoryStorageMongoDB`, `WorkflowsStorageMongoDB`. |
| MySQL | `@mastra/mysql` | `MySQLStore` | `new MySQLStore({ id, connectionString })` | Or `host`/`port` (3306)/`user`/`password`/`database`. Pool `max` 10. Covers messages, workflows, traces, scores. |
| MSSQL | `@mastra/mssql` | `MSSQLStore` | `new MSSQLStore({ id, connectionString })` | `schemaName` optional. |
| OracleDB | `@mastra/oracledb` | `OracleStore` | `new OracleStore({ id, user, password, connectString })` | Or `pool`/`poolManager` shared with `OracleVector`. Wallet options for Autonomous DB. Covers memory, workflows, observability, scores, and Editor data. |
| Google Cloud Spanner | `@mastra/spanner` | `SpannerStore` | `new SpannerStore({ id, projectId, instanceId, databaseId })` | Or `database` handle. GoogleSQL dialect. `initMode: 'sync' \| 'validate'`. Init runs domains sequentially. |
| DynamoDB | `@mastra/dynamodb` | `DynamoDBStore` | `new DynamoDBStore({ id, config: { tableName, region } })` | Single-table design (ElectroDB). `config.endpoint` for local. Per-entity `config.ttl`. No observability. 400 KB items. |
| Cloudflare D1 | `@mastra/cloudflare-d1` | `D1Store` | `new D1Store({ binding: env.DB })` | Workers binding, or REST with `accountId`, `databaseId`, `apiToken`. Initialize inline inside `new Mastra({...})` when importing `env` from `cloudflare:workers`. No observability. 1 MiB rows. |
| Cloudflare KV | `@mastra/cloudflare` (`/kv`) | `CloudflareKVStorage` (alias `CloudflareStore`) | `new CloudflareKVStorage({ id, bindings: { threads, messages } })` | Or REST with `accountId`, `apiToken`. Eventually consistent. No observability. |
| Cloudflare Durable Objects | `@mastra/cloudflare` (`/do`) | `CloudflareDOStorage` (alias `DOStore`) | `new CloudflareDOStorage({ sql: ctx.storage.sql })` | Strongly consistent SQLite in a Durable Object. `tablePrefix`. No observability. |
| Convex | `@mastra/convex` | `ConvexStore` | `new ConvexStore({ id, deploymentUrl, adminAuthToken })` | Needs `mastraStorage` server function (`@mastra/convex/server`). Redeploy functions after upgrading. No observability. 1 MiB records. |
| Upstash | `@mastra/upstash` | `UpstashStore` | `new UpstashStore({ id, url, token })` | Redis-compatible, `prefix` default `mastra:`. Use a fixed pricing plan. No observability. |
| Redis | `@mastra/redis` | `RedisStore` | `new RedisStore({ id, connectionString: 'redis://localhost:6379' })` | Or `host`/`port`/`password`/`db`/`client`. Standalone or Sentinel via custom client. No Redis Cluster. |
| Valkey | `@mastra/valkey` | `ValkeyStore` | `new ValkeyStore({ id, host, port, password })` | Valkey GLIDE client. Also `config` or `client`, `useTLS`. |
| Elasticsearch | `@mastra/elasticsearch` | `ElasticSearchStore` | `new ElasticSearchStore({ id, url: 'http://localhost:9200' })` | `auth`: `{ apiKey }`, `{ username, password }`, or `{ bearer }`; or `client`. Domains: memory, workflows, scores. Can share a client with `ElasticSearchVector`. |
| LanceDB | `@mastra/lance` | `LanceStorage` | `await LanceStorage.create('my-storage', '/path/to/db')` | Async factory. URI may be local, `db://`, or `s3://`. No observability. |
| ClickHouse | `@mastra/clickhouse` | `ClickhouseStore`, `ClickhouseStoreVNext`, `ObservabilityStorageClickhouseVNext` | `new ClickhouseStore({ id, url, username, password })` | Recommended production observability backend, usually inside a composite. `replication` for self-managed clusters only (not ClickHouse Cloud). Native TTL retention. |
| DuckDB | `@mastra/duckdb` | `DuckDBStore` | `new DuckDBStore({ path: './traces.duckdb' })` | Observability domain only. `id` default `'duckdb'`, `path` default `'mastra.duckdb'`, `memoryLimit` `'2GB'`. Local dev pairing with libSQL. |
| Turso Database (local file) | `@mastra/turso` | `TursoStore` | `new TursoStore({ id, path: './mastra.db' })` | Native local driver; no remote libSQL and no vector store. Check `getTursoDatabaseSupport()` on unusual platforms. |
| Mastra Platform | managed | | see `mastra-platform` | Listed under supported providers; documented with the platform. |

---

## Feature support matrix

| Feature | Adapters named in the docs |
|---|---|
| Observational memory | libSQL, PostgreSQL, MongoDB, MySQL, Convex, OracleDB |
| Resource-scoped working memory | libSQL, PostgreSQL, OracleDB, Upstash, MongoDB |
| Semantic recall `scope: 'resource'` | libSQL, OracleDB, PostgreSQL, MongoDB, Upstash |
| Atomic `mergeWorkingMemory` | PostgreSQL |
| In-database `copyThread` | libSQL, PostgreSQL |
| Observability domain missing | Convex, DynamoDB, Cloudflare D1, Cloudflare KV/DO, LanceDB, Upstash, Elasticsearch store |
| Observability only | DuckDB |
| Full `prune()` retention | libSQL, PostgreSQL, MongoDB |

---

## Size limits and caveats

| Adapter | Limit |
|---|---|
| DynamoDB | 400 KB per item |
| Convex | 1 MiB per record |
| Cloudflare D1 | 1 MiB per row |
| Aurora DSQL | No extensions (no pgvector); 60-minute connection limit |
| Redis | No Cluster mode |
| Upstash | High command volume per conversation; pay-as-you-go can be costly |

Docs contradiction: the libSQL page says libSQL supports observability (good for local dev), while the ClickHouse page says LibSQL does not implement the observability domain and recommends libSQL plus DuckDB locally. Verify against the installed `@mastra/libsql` before relying on libSQL for traces.

---

## Picking an adapter

| Situation | Pick |
|---|---|
| Local development | `LibSQLStore` with `file:` (absolute path when sharing with Studio) |
| Production default | `PostgresStore` (managed: Neon, ClickHouse Managed Postgres, RDS) |
| Already on MongoDB Atlas | `MongoDBStore` with `MongoDBVector` |
| Cloudflare Workers | `D1Store` or `CloudflareDOStorage`, plus observability elsewhere |
| AWS serverless | `DynamoDBStore` or `DSQLStore`, plus a vector store and observability backend |
| High trace volume | Composite: main DB plus `ObservabilityStorageClickhouseVNext` |
| Local observability | Composite: `LibSQLStore` default plus `new DuckDBStore().observability` |
