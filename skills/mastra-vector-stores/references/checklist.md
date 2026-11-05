# Vector store checklist

Run this before calling a vector store done.

## Choice

- [ ] Store chosen for an existing database where possible, or for a stated need (hybrid, scale, platform)
- [ ] Every filter operator in use is supported by the store (see `api.md`)
- [ ] Metric supported by the store (libSQL and Convex cosine only; S3 Vectors and Turbopuffer no dotproduct)
- [ ] Preview services (S3 Vectors, MongoDB Automated Embedding) acceptable for this deployment

## Index

- [ ] `dimension` equals the embedder output; one embedder per index
- [ ] Index name follows the store's naming rules
- [ ] Filterable fields declared where required (Qdrant payload index, Vectorize metadata index, MongoDB `filterFields`, Azure `metadataIndexes`)
- [ ] PgVector uses an explicit `indexConfig` (HNSW for recall and speed) and `metadataIndexes` for hot filters
- [ ] Index creation runs once (startup guard or migration script), not per request

## Data

- [ ] Metadata stores the source `text` and a document ID on every vector
- [ ] Metadata field names are consistent in casing
- [ ] Re-indexing deletes old vectors by document ID first (where filtered delete is supported)
- [ ] Tenant isolation enforced by index, namespace, or a server-set filter

## Operations

- [ ] Credentials in env vars and `.env.example`
- [ ] Store registered on `new Mastra({ vectors })` if shared, fetched with `mastra.getVector()`
- [ ] Connections closed on shutdown where the store exposes `disconnect()`
- [ ] Recall and p95 latency measured on a sample query set
