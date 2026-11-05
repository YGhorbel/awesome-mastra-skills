# Vector store providers

One row per adapter under `https://mastra.ai/integrations/vectors/`. Constructor shapes are the minimal form from each page or from `reference/rag/vector-databases`. Verify on the adapter page before use.

## Contents

- Adapter table
- Index creation and metrics
- Filter support summary
- Limits worth knowing

---

## Adapter table

| Store | Package | Class | Minimal constructor | Notes |
|---|---|---|---|---|
| PostgreSQL (pgvector) | `@mastra/pg` | `PgVector` | `new PgVector({ id, connectionString })` | Or host/port/database/user/password. `schemaName`, `max` (20), `pgPoolOptions`, `disableInit`. Fullest filter support. |
| libSQL / Turso | `@mastra/libsql` | `LibSQLVector` | `new LibSQLVector({ id, url, authToken? })` | `url`: `:memory:`, `file:...`, `libsql://...`. Cosine only. Good for local dev. |
| MongoDB Atlas | `@mastra/mongodb` | `MongoDBVector` | `new MongoDBVector({ id, uri, dbName })` | `embeddingFieldPath`, `autoEmbed`. Hybrid text plus vector, server-side Voyage embeddings (Preview). |
| Pinecone | `@mastra/pinecone` | `PineconeVector` | `new PineconeVector({ id, apiKey })` | `cloud` (`aws`), `region` (`us-east-1`) for new indexes. Namespaces, sparse vectors. |
| Qdrant | `@mastra/qdrant` | `QdrantVector` | `new QdrantVector({ id, url, apiKey })` | `https` option. Named vectors. Payload indexes required for filtering. |
| Chroma | `@mastra/chroma` | `ChromaVector` | `new ChromaVector({ id, apiKey, tenant, database })` | Local: `host` (`localhost`), `port` (8000), `ssl`. Documents and document filters, `hybridSearch`, `forkIndex`. |
| Astra DB | `@mastra/astra` | `AstraVector` | `new AstraVector({ id, token, endpoint, keyspace })` | `keyspace` optional. Nested fields with dot notation. |
| Upstash Vector | `@mastra/upstash` | `UpstashVector` | `new UpstashVector({ id, url, token })` | Indexes are namespaces created on upsert. Metric set on the Upstash index. Sparse hybrid. |
| Cloudflare Vectorize | `@mastra/vectorize` | `CloudflareVector` | `new CloudflareVector({ id, accountId, apiToken })` | Metadata indexes required (max 10). No `$and`/`$or`. No filtered delete. |
| Weaviate | `@mastra/weaviate` | `WeaviateVector` | `new WeaviateVector({ id, httpHost, httpPort, httpSecure, grpcHost, grpcPort, grpcSecure, apiKey })` | Defaults `localhost:8080`, gRPC 50051. Collections created with `vectorizer: none`. |
| OpenSearch | `@mastra/opensearch` | `OpenSearchVector` | `new OpenSearchVector({ id, node })` | `auth` (basic, bearer, AWS SigV4), `ssl`, `compression`. k-NN. |
| Elasticsearch | `@mastra/elasticsearch` | `ElasticSearchVector` | `new ElasticSearchVector({ id, url, auth? })` | Or `client`. `auth`: `{ apiKey }`, `{ username, password }`, `{ bearer }`. Shares a client with `ElasticSearchStore`. |
| Azure AI Search | `@mastra/azure-ai-search` | `AzureAISearchVector` | `new AzureAISearchVector({ id, endpoint, credential })` | `credential`: admin key, `AzureKeyCredential`, or `TokenCredential`. `autoIndexMetadata`. Hybrid and semantic ranking. |
| Amazon S3 Vectors | `@mastra/s3vectors` | `S3Vectors` | `new S3Vectors({ id, vectorBucketName, clientConfig: { region } })` | Preview service. `nonFilterableMetadataKeys` for large text. Cosine or euclidean. |
| Turbopuffer | not stated on the docs page | `TurbopufferVector` | `new TurbopufferVector({ id, apiKey })` | `baseUrl`, `consistency`, `schemaConfigForIndex`. Cosine or euclidean. Verify the package name on npm. |
| LanceDB | `@mastra/lance` | `LanceVectorStore` | `await LanceVectorStore.create('/path/to/db')` | Embedded. Uses `tableName`. Index types hnsw (default), ivfflat, ivfpq. |
| DuckDB | `@mastra/duckdb` | `DuckDBVector` | `new DuckDBVector({ id, path: ':memory:' })` | Embedded, VSS extension with HNSW. File path for persistence. |
| OracleDB | `@mastra/oracledb` | `OracleVector` | `new OracleVector({ id, user, password, connectString })` | Native `VECTOR` columns, JSON metadata. Share a pool with `OracleStore` via `poolManager`. Exact search default. |
| Couchbase | `@mastra/couchbase` | `CouchbaseVector` | `new CouchbaseVector({ id, connectionString, username, password, bucketName, scopeName, collectionName })` | No metadata filters, no `includeVector`, delete by ID only. Default metric dotproduct. |
| Convex | `@mastra/convex` | `ConvexVector` | `new ConvexVector({ id, deploymentUrl, adminAuthToken })` | In-JS cosine scoring for dev scale. `ConvexNativeVector` for native vector search. |

---

## Index creation and metrics

| Store | `createIndex` shape | Metrics |
|---|---|---|
| Most stores | `{ indexName, dimension, metric? }` | cosine (default), euclidean, dotproduct |
| PgVector | plus `indexConfig`, `vectorType`, `buildIndex`, `metadataIndexes` | plus hamming, jaccard (bit vectors) |
| MongoDB | plus `filterFields`; `autoEmbed` instead of `dimension` | cosine, euclidean, dotproduct |
| OracleDB | plus `vectorFormat`, `indexConfig`, `metadataIndexes` | plus hamming, jaccard |
| Lance | `{ tableName, indexName, dimension, metric?, indexConfig? }` | cosine, euclidean, dotproduct |
| Qdrant | plus `namedVectors` | cosine, euclidean, dotproduct |
| Azure AI Search | plus `metadataIndexes` | cosine, euclidean, dotproduct |
| libSQL, Convex | standard | cosine only |
| S3 Vectors, Turbopuffer | standard | cosine, euclidean |
| Couchbase | standard | default dotproduct |
| Upstash | `createIndex` optional (namespace created on upsert) | metric ignored |

---

## Filter support summary

| Level | Stores |
|---|---|
| Full MongoDB-style including `$elemMatch`, `$contains`, `$regex`, `$size` | PgVector, libSQL (no `$regex`), MongoDB, OracleDB |
| Rich plus geo and datetime | Qdrant (index payload fields first) |
| Comparison, array, logical | Pinecone, Astra, Upstash, Chroma (no `$exists`), Weaviate, Elasticsearch, OpenSearch, DuckDB, Turbopuffer, Lance |
| Restricted set, unknown operators throw | Azure AI Search, S3 Vectors |
| No logical operators | Cloudflare Vectorize (metadata indexes required) |
| Equality or `$or` of equalities | Convex native |
| None | Couchbase |

The metadata filter reference does not list operator support for Elasticsearch, OpenSearch, DuckDB, Turbopuffer, or Lance individually; their pages describe "metadata filters" or "MongoDB-style query syntax". Test the operators you rely on.

---

## Limits worth knowing

| Store | Limit |
|---|---|
| Pinecone | Metadata field names 512 chars; arrays 64 KB; numbers within plus or minus 1e38; metadata updates replace the whole object |
| Upstash | Keys 512 chars; no null filters; avoid large `$in` lists |
| Vectorize | 10 metadata indexes; strings indexed to 64 bytes; filter JSON under 2048 bytes; re-upsert after adding metadata indexes |
| S3 Vectors | 10 metadata keys per vector; 2 KB filterable; 40 KB total; key names 63 chars |
| MongoDB | Undeclared filter fields fall back to a pre-filter bounded by 16 MB BSON |
| PgVector | HNSW build memory roughly 60 MB to 250 MB+ per 100K vectors by dimension |
| Aurora DSQL | No pgvector; pair with a separate vector store |
