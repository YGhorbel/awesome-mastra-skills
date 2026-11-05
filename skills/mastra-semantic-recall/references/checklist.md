# Semantic recall checklist

Run this before calling semantic recall done.

## Need

- [ ] Message history and working memory alone were not enough (a concrete failing follow-up exists)
- [ ] Observational memory was considered for long-running threads (see `mastra-observational-memory`)
- [ ] Recall is off for latency-critical paths such as realtime voice

## Setup

- [ ] `vector` store configured and reachable from every process
- [ ] `embedder` set, or the vector store embeds server-side
- [ ] `embeddingDimension` set and matches the model (1536 for `openai/text-embedding-3-small`)
- [ ] Embedder API key in `.env.example`
- [ ] One embedder per index; changing models means a new index or re-indexing

## Configuration

- [ ] `topK`, `messageRange`, and `scope` set explicitly, not left implicit
- [ ] `scope: 'resource'` only on libSQL, OracleDB, PostgreSQL, MongoDB, or Upstash storage
- [ ] `filter` fields exist in thread metadata at save time
- [ ] PostgreSQL uses an HNSW `indexConfig` with explicit `m` and `efConstruction`
- [ ] FastEmbed inputs fit the 512-token window, or long content is chunked

## Verification

- [ ] A trace shows recalled messages in the LLM span for a cross-thread question
- [ ] `recall({ vectorSearchString, threadConfig: { semanticRecall: true } })` returns the expected message
- [ ] Per-turn latency and embedding token cost measured against budget
- [ ] Ownership checked before any programmatic `recall()` exposed to users
