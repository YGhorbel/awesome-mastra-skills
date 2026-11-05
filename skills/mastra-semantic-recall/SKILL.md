---
name: mastra-semantic-recall
description: "Configure semantic recall in Mastra memory: embed every stored message, then pull the most similar older messages into context with topK, messageRange, thread or resource scope, and metadata filters. Use this skill whenever the user wants an agent to remember details that scrolled out of recent history, search past conversations by meaning, pick an embedder and vector store for memory, tune recall quality, latency, or embedding cost, or fix recall that returns nothing. Triggers on semanticRecall, topK, messageRange, scope resource, vectorSearchString, embedder, ModelRouterEmbeddingModel, openai/text-embedding-3-small, fastembed, embeddingDimension, MASTRA_MEMORY_EMBEDDING_DIMENSION_MISMATCH, LibSQLVector, PgVector indexConfig hnsw, MongoDB autoEmbed. Also triggers for questions like what did we decide about X last week in a Mastra chat app."
license: Apache-2.0
metadata:
  category: memory-and-knowledge
  catalog_summary: "Semantic recall config: topK, messageRange, scope, filters, embedder and vector setup, tuning and cost"
  display_order: 2
  docs: https://mastra.ai/docs/memory/semantic-recall
---

# Mastra Semantic Recall

Find earlier messages by meaning and add them to the agent's context, so the agent can use details that are no longer in recent history.

---

## When to use

- The user refers back to something said many turns or many threads ago
- `lastMessages` is not enough, but you still want raw message wording
- Searching a user's past conversations by meaning from code with `recall()`
- Choosing an embedder and vector store for agent memory
- Tuning `topK`, `messageRange`, `scope`, or a metadata `filter`
- Fixing recall errors, dimension mismatches, or slow vector queries

## When NOT to use

- Basic threads, history, and working memory (use `mastra-memory`)
- Long agentic sessions where context must stay small and cacheable (use `mastra-observational-memory`, which the docs rate as more accurate and cheaper)
- Retrieval over documents, PDFs, or a knowledge base (use `mastra-rag`)
- Choosing between vector databases in depth (use `mastra-vector-stores`)
- Embedding model IDs and provider keys in general (use `mastra-models`)
- Realtime voice where every millisecond counts (leave recall off, see `mastra-voice`)

---

## Required inputs

- The storage adapter, and whether it supports `scope: 'resource'` (libSQL, OracleDB, PostgreSQL, MongoDB, Upstash)
- A vector store (often the same database as storage) or a self-embedding store
- An embedder ID and its output dimension (for example `openai/text-embedding-3-small`, 1536)
- Recall scope: this thread only, or all threads of the resource
- Any metadata the recall must be limited by (project, tenant, category)
- Latency budget per turn

---

## The framework: embed on save, search on input

Semantic recall is a pair of processors. On output, new messages (user, assistant, tool calls and results) are embedded and stored in the vector store. On input, the new message is embedded, the store returns the `topK` closest messages, and each match is added with `messageRange` neighbours.

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { LibSQLStore, LibSQLVector } from '@mastra/libsql'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'SupportAgent',
  instructions: 'You are a helpful support agent.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    storage: new LibSQLStore({ id: 'agent-storage', url: 'file:./local.db' }),
    vector: new LibSQLVector({ id: 'agent-vector', url: 'file:./local.db' }),
    embedder: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
    options: {
      lastMessages: 10,
      semanticRecall: { topK: 3, messageRange: 2, scope: 'resource' },
    },
  }),
})
```

| Option | Default | Effect |
|---|---|---|
| `topK` | `4` | Number of matched messages |
| `messageRange` | `{ before: 1, after: 1 }` | Neighbours added around each match. A number sets both sides |
| `scope` | `'resource'` | `'thread'` searches the current thread only |
| `filter` | none | Metadata filter on stored embeddings (`$eq`, `$in`, `$and`, ...) |
| `indexConfig` | store default | Vector index type and metric (PgVector: `ivfflat` default, `hnsw` recommended) |

Where recalled messages land: matches from the current thread interleave with history by timestamp. Matches from other threads go into a system message.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/memory/dist/docs/` and the installed `Memory` types. Otherwise fetch `https://mastra.ai/docs/memory/semantic-recall.md` and `https://mastra.ai/reference/memory/memory-class.md`. Trust these over memory.
2. **Decide if recall is needed.** If history plus working memory answers the follow-ups, stop. If threads run long, compare with `mastra-observational-memory` first.
3. **Pick the vector store.** Reuse the storage database when possible: `LibSQLVector` with `LibSQLStore`, `PgVector` with `PostgresStore`, `MongoDBVector` with `MongoDBStore`. Other options in `mastra-vector-stores`.
4. **Pick the embedder.** A router string such as `'openai/text-embedding-3-small'` or `new ModelRouterEmbeddingModel(...)`, local `fastembed` from `@mastra/fastembed`, or none when the store embeds server-side (MongoDB `autoEmbed`).
5. **Set `embeddingDimension`.** It skips the startup probe call and fails fast on a mismatch.
6. **Enable and size recall.** Start with `topK: 3`, `messageRange: 2`. Choose `scope`. Add `filter` if threads carry metadata such as `projectId`.
7. **Tune the index.** On PostgreSQL use `indexConfig: { type: 'hnsw', metric: 'dotproduct' }` for OpenAI embeddings.
8. **Verify.** Ask about something from an older thread, then open the trace in Studio. Recalled messages appear in the LLM span. Or call `memory.recall({ vectorSearchString, threadConfig: { semanticRecall: true } })`.

---

## Deep dive: tuning and cost

Every turn costs one embedding call for the input, one vector query, and one embedding call per saved message. That is the latency and spend to budget.

| Lever | Raise when | Lower when |
|---|---|---|
| `topK` | Answers miss facts the user stated | Context fills with loosely related turns |
| `messageRange` | Matches lack the surrounding question or answer | Token usage per turn is too high |
| `scope: 'resource'` | Facts live in other conversations | Threads are unrelated tasks; leakage confuses the model |
| `filter` | One resource mixes projects or tenants | Never needed |

- **Index type matters at scale.** Recall always filters by thread or resource. PgVector uses the index for those searches only with HNSW on pgvector 0.8.0 or newer. With IVFFlat, each search compares against every message of the thread or resource.
- **Filters read embedding metadata from save time.** Changing thread metadata later does not update existing embeddings until they are saved or indexed again.
- **FastEmbed truncates at 512 tokens.** Text past the window cannot be recalled. Multilingual E5 is 1024 dimensions; use one model (`multilingualE5LargePassage`) for both storing and searching in memory.
- **Server-side embeddings are eventually consistent.** MongoDB embeds new messages in the background, so a message saved moments ago may not be recallable yet.
- **Thread cloning re-embeds.** `cloneThread()` and `copyThread()` embed copied messages in batches when recall is on.

---

## Failure patterns

- **"Embedder required" error on startup.** Recall is on with neither `embedder` nor a self-embedding store. Add an embedder or use MongoDB `autoEmbed`.
- **`MASTRA_MEMORY_EMBEDDING_DIMENSION_MISMATCH`.** `embeddingDimension` differs from the model output. Update it whenever you change the embedder.
- **Switched embedder and recall returns junk.** Old vectors came from another model. Vectors from different embedders cannot share an index; re-index or start a new index.
- **`scope: 'resource'` finds nothing across threads.** The storage adapter does not support resource scope, or calls pass different `resource` values. Use a listed adapter and a stable resource ID.
- **Recall is slow on PostgreSQL.** Default IVFFlat index. Switch to `indexConfig: { type: 'hnsw' }` on pgvector 0.8.0+.
- **Missing API key at construction.** `ModelRouterEmbeddingModel` throws if `OPENAI_API_KEY` (or `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`) is unset.
- **`recall()` with `vectorSearchString` returns recent messages only.** `threadConfig: { semanticRecall: true }` was not passed.
- **Using recall to hold user profile facts.** Similarity search is not guaranteed to return them. Put stable facts in working memory (`mastra-memory`).
- **Recall enabled on a realtime voice agent.** Adds embedding and query latency each turn. Disable it there.

---

## Output format

A finished semantic recall delivery contains:

- `Memory` with `vector`, `embedder` (or a self-embedding store), and `embeddingDimension`
- `semanticRecall` with explicit `topK`, `messageRange`, and `scope`, plus `filter` if used
- Index configuration for PostgreSQL deployments
- Embedder API key listed in `.env.example`
- Evidence: a trace or `recall()` call showing an older message retrieved by meaning

---

## Reference files

- [`references/api.md`](references/api.md) - `semanticRecall` options, embedder forms, embedding dimensions, `recall()` search parameters, filter operators.
- [`references/examples.md`](references/examples.md) - libSQL recall, PostgreSQL with HNSW and fastembed, MongoDB server-side embeddings, programmatic search.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for semantic recall.

**Live docs**

- https://mastra.ai/docs/memory/semantic-recall
- https://mastra.ai/reference/memory/memory-class
- https://mastra.ai/reference/memory/recall
- https://mastra.ai/models/embeddings
- https://mastra.ai/integrations/vectors/pg
