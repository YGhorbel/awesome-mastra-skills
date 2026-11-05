# RAG checklist

Run this before calling a RAG pipeline done.

## Ingestion

- [ ] Chunking strategy matches the content type (Markdown, HTML, prose, JSON)
- [ ] `maxSize` and `overlap` chosen deliberately and checked on real documents
- [ ] Every upsert stores `text` in metadata
- [ ] Every chunk carries a stable `docId` for deletes and re-indexing
- [ ] Only filterable fields added to metadata, with consistent casing
- [ ] Index `dimension` matches the embedding model output
- [ ] Same embedding model used for ingest and query
- [ ] Re-ingest deletes old chunks (`deleteVectors` by `docId`) before upserting
- [ ] LLM metadata extraction (`extract`) only enabled when worth the cost
- [ ] Store-specific filter indexes created (Qdrant payload index, Vectorize metadata index, MongoDB `filterFields`)

## Retrieval

- [ ] `topK` sized for the model's context budget
- [ ] Filters use operators the store supports
- [ ] Reranker added only after measuring baseline relevance
- [ ] Reranker weights sum to 1
- [ ] GraphRAG only for cross-referencing documents, with snapshots persisted

## Agent wiring

- [ ] Vector query tool has a specific `description`
- [ ] Instructions tell the agent when to search and to admit when nothing is found
- [ ] Store filter prompt constant included when `enableFilter: true`
- [ ] `vectorStoreName` matches the `new Mastra({ vectors })` key, or `vectorStore` passed directly
- [ ] Tenant selection comes from server-set `requestContext`, not user input

## Operations

- [ ] Connection strings and provider keys in `.env.example`
- [ ] A set of known questions with expected chunks for regression checks
- [ ] Retrieval and faithfulness scorers configured (see `mastra-evals`)
- [ ] Tracing enabled to inspect retrieval spans (see `mastra-observability`)
