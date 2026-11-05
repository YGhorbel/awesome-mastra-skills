---
name: mastra-rag
description: "Build retrieval-augmented generation pipelines with @mastra/rag: load documents with MDocument, chunk them, embed with embed or embedMany, upsert into a vector store, then retrieve with metadata filters, reranking, GraphRAG, or an agent-facing vector query tool. Use this skill whenever the user wants an agent to answer from their own documents, build a knowledge base search, ingest PDFs or Markdown into a vector database, tune chunk size or overlap, add a reranker, or give an agent a search tool over embeddings. Triggers on RAG, retrieval, MDocument, doc.chunk, chunking strategy, embedMany, ModelRouterEmbeddingModel, vector upsert, query vector, topK, metadata filter, rerank, rerankWithScorer, CohereRelevanceScorer, GraphRAG, createVectorQueryTool, createGraphRAGTool, createDocumentChunkerTool, createBedrockKBTool, PGVECTOR_PROMPT. Also triggers when an agent hallucinates facts that live in the user's documents."
license: Apache-2.0
metadata:
  category: memory-and-knowledge
  catalog_summary: "MDocument chunking, embeddings, vector upsert and query, filters, reranking, GraphRAG, and vector query tools"
  display_order: 4
  docs: https://mastra.ai/reference/rag/overview
---

# Mastra RAG

Build a pipeline that chunks documents, embeds them, stores them in a vector database, and retrieves the right chunks at answer time, either in code or through an agent tool.

---

## When to use

- Ingesting documents (text, Markdown, HTML, JSON, LaTeX) into a vector store
- Choosing a chunking strategy, chunk size, overlap, or LLM metadata extraction
- Generating embeddings with `embed`/`embedMany` and the model router
- Querying a vector store with `topK` and MongoDB-style metadata filters
- Reranking results with an LLM or a dedicated reranker (Cohere, Voyage, ZeroEntropy)
- Giving an agent a search tool: `createVectorQueryTool`, `createGraphRAGTool`, `createBedrockKBTool`
- Graph-based retrieval across documents that reference each other (`GraphRAG`)

## When NOT to use

- Picking or configuring a vector database adapter and its constructor options (use `mastra-vector-stores`)
- Recalling past conversation messages by meaning (use `mastra-semantic-recall`)
- Conversation history, threads, and working memory (use `mastra-memory`)
- A shared, scoped page store that agents read and write, with access roles and pinned pages (use `mastra-knowledge`)
- Choosing an embedding or language model ID (use `mastra-models`)
- Storage adapters for threads, workflows, and traces (use `mastra-storage`)
- Writing a custom tool from scratch (use `mastra-tools`)

---

## Required inputs

- The source documents and their format (plain text, Markdown, HTML, JSON)
- The vector store (pgvector, libSQL, Pinecone, MongoDB, Qdrant, and so on) and its connection env vars
- The embedding model and its dimension (for example `openai/text-embedding-3-small`, 1536)
- Metadata to keep per chunk: at minimum the chunk `text`, plus a document ID and any filter fields
- Who drives retrieval: your code (direct `query`) or the agent (a vector query tool)

Ask for the vector store and embedding model before writing code. Index dimension cannot change after creation.

---

## The framework: chunk, embed, store, retrieve

```typescript
import { MDocument } from '@mastra/rag'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { PgVector } from '@mastra/pg'
import { embed, embedMany } from 'ai'

const embedder = new ModelRouterEmbeddingModel('openai/text-embedding-3-small')

// 1. Chunk
const doc = MDocument.fromMarkdown(markdownText)
const chunks = await doc.chunk({ strategy: 'recursive', maxSize: 512, overlap: 50 })

// 2. Embed
const { embeddings } = await embedMany({ model: embedder, values: chunks.map(c => c.text) })

// 3. Store (dimension must match the model)
const store = new PgVector({ id: 'pg-vector', connectionString: process.env.POSTGRES_CONNECTION_STRING })
await store.createIndex({ indexName: 'docs', dimension: 1536 })
await store.upsert({
  indexName: 'docs',
  vectors: embeddings,
  metadata: chunks.map(c => ({ text: c.text, docId: 'handbook' })),
})

// 4. Retrieve
const { embedding } = await embed({ model: embedder, value: 'What is the refund window?' })
const results = await store.query({ indexName: 'docs', queryVector: embedding, topK: 5 })
// results: [{ id, score, metadata: { text, docId } }]
```

### Two ways to retrieve

| Retrieval in code | Retrieval by the agent |
|---|---|
| You embed the query and call `store.query()` | Agent calls `createVectorQueryTool(...)` |
| You build the prompt context yourself | Tool returns `relevantContext` and `sources` |
| Fixed filters and `topK` | Agent can build filters with `enableFilter: true` |
| Best inside workflow steps | Best for open-ended chat |

### The `metadata.text` rule

Store the chunk text in metadata as `text`. Results only carry `id`, `score`, and `metadata` for most stores. Reranking, the vector query tool's `relevantContext`, and the GraphRAG tool all read `metadata.text`.

### Strategy cheat sheet

| Content | Strategy | Notes |
|---|---|---|
| Plain prose | `recursive` | Default for text. Tune `maxSize`, `overlap`, `separators`. |
| Markdown with headings | `markdown` with `headers` | `headers` ignores size options. Omit it for size-based splits. |
| Related Markdown sections | `semantic-markdown` | Merges sections under `joinThreshold` tokens. |
| Sentence-preserving | `sentence` | `maxSize` required. `overlap` defaults to 0. |
| Token budgets | `token` | Set `encodingName` or `modelName`. |
| HTML | `html` with `headers` or `sections` | General size options are ignored. |
| JSON | `json` | Structure-aware. |

Defaults: `maxSize` 4000, `overlap` 200. Without `strategy`, Mastra picks by document type.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/rag/dist/docs/` and the installed types for `MDocument`, `createVectorQueryTool`, and the vector store package. Otherwise fetch `https://mastra.ai/reference/rag/chunk.md`, `https://mastra.ai/reference/rag/retrieval.md`, and `https://mastra.ai/reference/tools/vector-query-tool.md`. Trust these over memory.
2. **Pick the store and model.** Install `@mastra/rag` plus the store package (see `mastra-vector-stores`). Confirm the embedding model's dimension. Use `ModelRouterEmbeddingModel` with a `provider/model` string.
3. **Choose a chunking strategy** from the cheat sheet. Start with `recursive`, `maxSize: 512`, `overlap: 50` and adjust after you inspect results.
4. **Design metadata.** Always include `text`. Add a stable `docId` so you can delete and re-index one document. Add only fields you will filter on.
5. **Write the ingestion script** (`src/mastra/rag/ingest.ts` or a workflow): chunk, `embedMany`, `createIndex` once, `upsert`.
6. **Register the store** on `new Mastra({ vectors: { pgVector } })` when an agent tool references it by `vectorStoreName`. Or pass the instance directly with `vectorStore`.
7. **Retrieve.** Either query in code, or attach `createVectorQueryTool` to an agent. Give the tool a specific `description`. Add the store's filter prompt (for example `PGVECTOR_PROMPT`) to instructions when `enableFilter` is on.
8. **Improve relevance** only after measuring: add metadata filters, then reranking, then GraphRAG for linked documents.
9. **Re-index safely.** On document change, `deleteVectors({ indexName, filter: { docId } })`, then upsert the new chunks.
10. **Test** retrieval with known questions. Add a retrieval or faithfulness scorer with `mastra-evals`.

---

## Deep dive: agent retrieval tools

```typescript
import { Agent } from '@mastra/core/agent'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { createVectorQueryTool } from '@mastra/rag'
import { PGVECTOR_PROMPT } from '@mastra/pg'

const vectorQueryTool = createVectorQueryTool({
  vectorStoreName: 'pgVector', // key in new Mastra({ vectors })
  indexName: 'docs',
  model: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
  description: 'Search the employee handbook for policies and procedures',
  enableFilter: true,
})

export const ragAgent = new Agent({
  id: 'rag-agent',
  name: 'RAG Agent',
  model: 'openai/gpt-6.1-sol',
  instructions: `Answer from the handbook. Use vectorQueryTool before answering.
If the context does not contain the answer, say so.
${PGVECTOR_PROMPT}`,
  tools: { vectorQueryTool },
})
```

Runtime overrides go through `requestContext`: `vectorStoreName`, `indexName`, `topK`, `filter`, and `databaseConfig`. For multi-tenant data, pass `vectorStore` as a resolver `async ({ requestContext }) => store`.

Other tools in `@mastra/rag`:

- `createGraphRAGTool({ vectorStoreName, indexName, model, graphOptions: { dimension, threshold } })` for relationship-aware retrieval. Start at `threshold: 0.7`.
- `createBedrockKBTool({ knowledgeBaseId, region })` for an Amazon Bedrock Knowledge Base. No vector store needed.
- `createDocumentChunkerTool({ doc, params })` to chunk a document as a tool call.

---

## Failure patterns

- **Results have no text.** You upserted vectors without `metadata: chunks.map(c => ({ text: c.text }))`. Re-ingest with text in metadata.
- **Dimension mismatch errors or garbage scores.** The index dimension differs from the model output. Delete and recreate the index. Dimensions cannot be changed.
- **`size` instead of `maxSize`.** Some docs examples show `size`. The `chunk()` reference uses `maxSize`. Use `maxSize`.
- **Markdown `headers` ignoring `maxSize`.** Expected. Header-based splitting ignores size options. Omit `headers` for size-based chunks.
- **Different embedding models for ingest and query.** Similarity becomes meaningless. Use one model for both.
- **Reranker returns poor order.** Semantic scoring needs `metadata.text`. Weights must add up to 1.
- **Agent never filters.** Set `enableFilter: true` and include the store prompt constant (`PGVECTOR_PROMPT`, `PINECONE_PROMPT`, and so on) in instructions.
- **Filter operator silently unsupported.** Operators vary by store (for example `$regex` and `$elemMatch`). Check the support list in `references/api.md`.
- **Tool cannot find the store.** `vectorStoreName` must match the key in `new Mastra({ vectors })`, or pass `vectorStore` directly.
- **Stale chunks after an edit.** Upsert does not remove old chunks. Delete by `docId` first.
- **GraphRAG rebuilt on every boot.** Building is O(n squared). Use `serialize()` and `GraphRAG.deserialize()`.

---

## Output format

A finished RAG delivery contains:

- An ingestion script or workflow that chunks, embeds, creates the index, and upserts with `text` and `docId` metadata
- The vector store instance, registered on `new Mastra({ vectors })` when tools reference it by name
- Either a retrieval function or an agent with `createVectorQueryTool` and a specific tool description
- Env vars in `.env.example` (store connection string, embedding provider key)
- A test or Studio run showing a known question retrieves the expected chunk

---

## Reference files

- [`references/api.md`](references/api.md) - `MDocument`, `chunk()` options per strategy, `ExtractParams`, embed, vector store methods, filter operators, rerank, GraphRAG, and tool parameters.
- [`references/examples.md`](references/examples.md) - Complete pipelines: ingest and query, agent with vector query tool, reranking, multi-tenant resolver, GraphRAG persistence.
- [`references/checklist.md`](references/checklist.md) - Ingestion and retrieval checklist before production.

**Live docs**

- https://mastra.ai/reference/rag/overview
- https://mastra.ai/reference/rag/chunking-and-embedding
- https://mastra.ai/reference/rag/chunk
- https://mastra.ai/reference/rag/retrieval
- https://mastra.ai/reference/rag/metadata-filters
- https://mastra.ai/reference/rag/rerankWithScorer
- https://mastra.ai/reference/rag/graph-rag-guide
- https://mastra.ai/reference/tools/vector-query-tool
- https://mastra.ai/reference/tools/graph-rag-tool
- https://mastra.ai/reference/tools/bedrock-kb-tool
