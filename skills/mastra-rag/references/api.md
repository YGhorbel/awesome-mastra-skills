# RAG API reference

Distilled from `https://mastra.ai/reference/rag/*.md` and `https://mastra.ai/reference/tools/*.md`. Verify against the installed version before relying on an option.

## Contents

- MDocument
- chunk() options
- ExtractParams
- Embeddings
- Vector store methods
- Metadata filter operators
- rerank() and rerankWithScorer()
- GraphRAG class
- createVectorQueryTool()
- createGraphRAGTool()
- DatabaseConfig
- createDocumentChunkerTool() and createBedrockKBTool()

---

## MDocument

Import: `import { MDocument } from '@mastra/rag'`

| Member | Signature |
|---|---|
| Constructor | `new MDocument({ docs: Array<{ text, metadata? }>, type: 'text' \| 'html' \| 'markdown' \| 'json' \| 'latex' })` |
| `MDocument.fromText(text, metadata?)` | Plain text |
| `MDocument.fromHTML(html, metadata?)` | HTML |
| `MDocument.fromMarkdown(markdown, metadata?)` | Markdown |
| `MDocument.fromJSON(json, metadata?)` | JSON string |
| `chunk(params?, { observabilityContext? })` | `Promise<Chunk[]>`, each `{ text, metadata, embedding? }` |
| `extractMetadata(params: ExtractParams)` | `Promise<MDocument>` |
| `getDocs()` / `getText()` / `getMetadata()` | Chunks, text strings, metadata objects |

---

## chunk() options

General options (each strategy uses a subset):

| Option | Default | Notes |
|---|---|---|
| `strategy` | by type | `.md` markdown, `.html` html, `.json` json, `.tex` latex, else `recursive` |
| `maxSize` | `4000` | Ignored by markdown/html with `headers` |
| `overlap` | `200` | `sentence` defaults to `0` |
| `lengthFunction` | char count | `(text) => number` |
| `separatorPosition` | discard | `'start' \| 'end'` |
| `addStartIndex` | `false` | Adds start index metadata |
| `stripWhitespace` | `true` | |
| `extract` | none | `ExtractParams`, LLM metadata extraction |

Strategy-specific options are top-level keys, not nested:

| Strategy | Options |
|---|---|
| `character` | `separator` (default `'\n\n'`), `isSeparatorRegex` |
| `recursive` | `separators: string[]`, `isSeparatorRegex`, `language` |
| `sentence` | `maxSize` (required), `minSize` (50), `targetSize` (80% of max), `sentenceEnders` (`['.', '!', '?']`), `fallbackToWords` (true), `fallbackToCharacters` (true) |
| `html` | `headers: [selector, key][]`, `sections: [selector, key][]`, `returnEachLine`. General options ignored. `sections` ignored when `headers` is set. |
| `markdown` | `headers: [level, key][]`, `stripHeaders`, `returnEachLine` |
| `semantic-markdown` | `joinThreshold` (500 tokens), `modelName`, `encodingName` (`cl100k_base`), `allowedSpecial`, `disallowedSpecial` |
| `token` | `encodingName`, `modelName`, `allowedSpecial`, `disallowedSpecial` |
| `json` | `maxSize`, `minSize` (no effect), `ensureAscii`, `convertLists` |
| `latex` | General options only |

---

## ExtractParams

Passed as `chunk({ extract })` or `doc.extractMetadata(...)`. Each key is `true` or a config object. Extraction calls an LLM.

| Key | Config | Output metadata key |
|---|---|---|
| `title` | `{ llm?, nodes?, nodeTemplate?, combineTemplate? }` | `documentTitle` |
| `summary` | `{ llm?, summaries?: ('self' \| 'prev' \| 'next')[], promptTemplate? }` | `sectionSummary` |
| `questions` | `{ llm?, questions?, promptTemplate?, embeddingOnly? }` (`embeddingOnly` has no effect) | `questionsThisExcerptCanAnswer` |
| `keywords` | `{ llm?, keywords?, promptTemplate? }` | `excerptKeywords` |
| `schema` | `{ schema: ZodType, llm?, instructions?, metadataKey? }` | spread, or under `metadataKey` |

Templates must include `{context}` (questions also `{numQuestions}`, keywords `{maxKeywords}`). Chunks that share `metadata.docId` share one extracted title.

---

## Embeddings

```typescript
import { embed, embedMany } from 'ai'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'

const model = new ModelRouterEmbeddingModel('openai/text-embedding-3-small')
const { embedding } = await embed({ model, value: 'text', maxRetries: 2 })
const { embeddings } = await embedMany({ model, values: ['a', 'b'], options: { dimensions: 256 } })
```

| Param | Notes |
|---|---|
| `model` | Embedding model |
| `value` / `values` | `string \| object` / array |
| `maxRetries` | Default `2`. `0` disables. |
| `abortSignal`, `headers` | Optional |

Direct versioned helpers live in `@mastra/core/vector`: `embedV1`, `embedV2`, `embedV3`, `embedV4` (AI SDK v4, v5, v6, v7 respectively).

Common dimensions: `text-embedding-3-small` 1536, Cohere `embed-multilingual-v3` 1024, `voyage-3.5` 1024, `gemini-embedding-001` 768.

---

## Vector store methods

All Mastra vector stores share this interface (see `mastra-vector-stores` for constructors).

| Method | Shape |
|---|---|
| `createIndex` | `{ indexName, dimension }` plus store extras (MongoDB `filterFields`, Oracle `indexConfig`) |
| `upsert` | `{ indexName, vectors: number[][], metadata?: object[] }`. Batches automatically. Same ID updates. |
| `query` | `{ indexName, queryVector, topK?, filter?, includeVector? }` returns `{ id, score, metadata, vector?, document? }[]` |
| `deleteVectors` | `{ indexName, filter }` or `{ indexName, ids }` |
| Qdrant `createPayloadIndex` | `{ indexName, fieldName, fieldSchema }`, required before filtering a field |
| Vectorize `createMetadataIndex` | Required before filtering a field |
| MongoDB `waitForIndexReady` | `{ indexName }` after `createIndex` |

Register shared stores on Mastra: `new Mastra({ vectors: { pgVector } })`, then `mastra.getVector('pgVector')`.

Filter prompt constants for agent instructions: `PGVECTOR_PROMPT` (`@mastra/pg`), `PINECONE_PROMPT`, `QDRANT_PROMPT`, `CHROMA_PROMPT`, `ASTRA_PROMPT`, `LIBSQL_PROMPT`, `UPSTASH_PROMPT`, `VECTORIZE_PROMPT`, `MONGODB_PROMPT`, `OPENSEARCH_PROMPT`, `ORACLEDB_PROMPT`, `S3VECTORS_PROMPT`, each from its store package.

---

## Metadata filter operators

MongoDB-style syntax, translated per store.

| Operator | Supported by |
|---|---|
| `$eq $ne $gt $gte $lt $lte $in $nin` | All except Couchbase |
| `$all` | Astra, Pinecone, Qdrant, Upstash, MongoDB, OracleDB |
| `$elemMatch` | libSQL, PgVector, MongoDB, OracleDB |
| `$and $or` | All except Vectorize, Couchbase |
| `$not` | Astra, Qdrant, Upstash, PgVector, libSQL, MongoDB, OracleDB |
| `$nor` | Qdrant, Upstash, PgVector, libSQL, MongoDB, OracleDB |
| `$exists` | All except Vectorize, Chroma, Couchbase |
| `$contains` | Upstash, libSQL, PgVector, OracleDB |
| `$regex` | Qdrant (token match), PgVector, Upstash, MongoDB, OracleDB |
| `$size` | Astra, libSQL, PgVector, MongoDB (integer only), OracleDB |
| `$geo $datetime $hasId $hasVector` | Qdrant |

Rules: logical operators only at top level or inside other logical operators. Field names cannot start with `$` or contain dots unless nested. Couchbase has no metadata filter support.

---

## rerank() and rerankWithScorer()

```typescript
rerank(results, query, model: MastraLanguageModel, options): Promise<RerankResult[]>
rerankWithScorer({ results, query, scorer: RelevanceScoreProvider, options }): Promise<RerankResult[]>
```

| Option | Default |
|---|---|
| `weights.semantic` | `0.4` |
| `weights.vector` | `0.4` |
| `weights.position` | `0.2` |
| `queryEmbedding` | optional |
| `topK` | optional |

Weights must sum to 1. Results need `metadata.text`. Returns `{ result, score, details: { semantic, vector, position, queryAnalysis } }`.

Scorers: `MastraAgentRelevanceScorer(name, 'provider/model')` and `CohereRelevanceScorer('rerank-v3.5')` from `@mastra/rag`, `VoyageRelevanceScorer({ model: 'rerank-2.5' })` from `@mastra/voyageai` (reads `VOYAGE_API_KEY`), `ZeroEntropyRelevanceScorer('zerank-1')`.

---

## GraphRAG class

```typescript
const graph = new GraphRAG(dimension = 1536, threshold = 0.7)
graph.createGraph(chunks, embeddings)
graph.query({ query: number[], topK = 10, randomWalkSteps = 100, restartProb = 0.15, filter? })
graph.serialize(): GraphRAGSnapshot
GraphRAG.deserialize(snapshot): GraphRAG
```

Query returns `{ id, content, metadata?, score }[]`. Snapshots contain full embeddings (about 20 MB per 1,000 nodes at 1536 dims). Rebuild when documents change.

---

## createVectorQueryTool()

| Param | Set at | Notes |
|---|---|---|
| `id` | creation | Default `VectorQuery {vectorStoreName} {indexName} Tool` |
| `description` | creation | Default "Access the knowledge base to find information needed to answer user questions" |
| `model` | creation or runtime | Embedding model |
| `vectorStoreName` | creation or runtime | Key in `Mastra.vectors`. Optional with `vectorStore`. |
| `vectorStore` | creation | `MastraVector` or `VectorStoreResolver` `({ requestContext }) => store` |
| `indexName` | creation or runtime | |
| `enableFilter` | creation | Default `false`. Auto-on if `filter` is in request context. |
| `includeVectors` | both | Default `false` |
| `includeSources` | both | Default `true` |
| `reranker` | both | `{ model, options: { weights, topK } }` |
| `databaseConfig` | both | See DatabaseConfig |
| `providerOptions` | creation | Embedding provider options (V2 models) |

Input: `queryText`, `topK`, `filter`. Output: `relevantContext` (metadata objects, text at `[i].text`) and `sources` (`QueryResult[]`). `document` is empty for stores like PgVector.

Request context keys: `vectorStoreName`, `indexName`, `topK`, `filter`, `databaseConfig`, `model`.

Standalone call: `await tool.execute({ queryText, topK }, { requestContext })`.

---

## createGraphRAGTool()

Same base params as the vector query tool, except `model` is creation-only and there is no `reranker`. Adds `graphOptions: { dimension, threshold, randomWalkSteps, restartProb }`. `randomWalkSteps` and `restartProb` can also come from request context. Default id `GraphRAG {vectorStoreName} {indexName} Tool`. Output `relevantContext` is `string[]` read from `metadata.text`. The graph is built on first execution from retrieved chunks.

---

## DatabaseConfig

| Store key | Options |
|---|---|
| `pinecone` | `namespace`, `sparseVector: { indices, values }` |
| `pgvector` | `minScore`, `ef` (HNSW, start 2 to 4x topK), `probes` (IVFFlat, start 1 to 10) |
| `chroma` | `where`, `whereDocument` (`$contains`, `$not_contains`) |
| `mongodb` | `numCandidates` (default 20 x topK, cap 10,000) |
| `turbopuffer` | `consistency: 'strong' \| 'eventual'` |
| `lance` | `tableName`, `includeAllColumns` (shown in retrieval docs) |

Override at runtime: `requestContext.set('databaseConfig', { pinecone: { namespace: 'prod' } })`.

---

## createDocumentChunkerTool() and createBedrockKBTool()

```typescript
createDocumentChunkerTool({ doc: MDocument, params?: ChunkParams })
// params defaults: strategy 'recursive', maxSize 512, overlap 50, separators ['\n']
// const { chunks } = await chunker.execute()
```

```typescript
createBedrockKBTool({ knowledgeBaseId, region?, numberOfResults?, useAgenticRetrieval?, userId? })
```

| Param | Default |
|---|---|
| `region` | `AWS_REGION` or `us-east-1` |
| `numberOfResults` | `5` |
| `useAgenticRetrieval` | `true` (disable with `USE_AGENTIC_RETRIEVAL=false`), falls back to standard retrieval |
| `userId` | Request context `userId` wins |

Input `queryText`. Output `results: { content, source?, score?, metadata }[]`. Needs IAM `bedrock:Retrieve` and `bedrock:AgenticRetrieveStream`, and `@aws-sdk/client-bedrock-agent-runtime` 3.1000 or later.
