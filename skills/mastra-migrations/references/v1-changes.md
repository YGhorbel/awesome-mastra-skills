# v1 breaking changes by area

Distilled from `https://mastra.ai/reference/migrations/upgrade-to-v1/*`. Each section lists what changed, the before and after, and the codemod when one exists. Work through them in the order of the overview checklist: high impact first.

## Contents

- Mastra class and imports
- Agents
- Tools
- Workflows
- Memory
- Storage and database
- Vectors and RAG
- Tracing and observability
- Evals and scorers
- MCP, processors, voice
- Client SDK
- CLI and deployment

---

## Mastra class and imports

The root `@mastra/core` exports only `Mastra` and `Config`. Codemod: `v1/mastra-core-imports`.

```diff
- import { Mastra, Agent, Workflow, createTool } from '@mastra/core';
+ import { Mastra, type Config } from '@mastra/core';
+ import { Agent } from '@mastra/core/agent';
+ import { Workflow } from '@mastra/core/workflows';
+ import { createTool } from '@mastra/core/tools';
```

Every storage, vector store, agent, workflow, MCP server, processor, scorer, and tool needs an `id`. Use unique IDs when one class is instantiated twice.

```diff
- const storage = new LibSQLStore({
-   url: ':memory:',
- });
+ const storage = new LibSQLStore({
+   id: 'my-app-storage',
+   url: ':memory:',
+ });
```

Plural getters became `list*` (codemod `v1/mastra-plural-apis`): `listAgents()`, `listWorkflows()`, `listVectors()`, `listScorers()`, `listMCPServers()`, `listLogs()`, `listLogsByRunId()`. Each primitive has `get` (registry key) and `getById` (intrinsic ID). Auto-registered tools use the tool's intrinsic `id`.

## Agents

- `RuntimeContext` to `RequestContext` (codemod `v1/runtime-context`).
- Property access to getters (codemod `v1/agent-property-access`): `agent.getLLM()`, `await agent.listTools()`, `agent.getInstructions()`.
- Voice methods under `agent.voice` (codemod `v1/agent-voice`).
- `agent.fetchMemory()` to `(await agent.getMemory()).recall()`.
- Processor `get*` to `list*` (codemod `v1/agent-processor-methods`).
- `modelSettings.abortSignal` to top-level `abortSignal` (codemod `v1/agent-abort-signal`).
- `output` to `structuredOutput.schema`. Zod v3 and v4 schemas both remain supported.
- Agent `id` required. Stream responses redact sensitive data.
- Removed: `generateVNext`/`streamVNext` (codemod `v1/agent-generate-stream-v-next`), `format` parameter, `agent.toStep()`, `TMetrics` generic. Tripwire response format and `prepareStep` message format changed.
- `threadId` and `resourceId` options removed:

```diff
await agent.stream('Hello', {
-   threadId: 'thread-123',
-   resourceId: 'user-456',
+   memory: {
+     thread: 'thread-123',
+     resource: 'user-456',
+   },
  });
```

## Tools

```diff
createTool({
    id: 'weather-tool',
-   execute: async ({ context, requestContext, mastra }) => {
-     const location = context.location;
-     const userTier = requestContext.get('userTier');
-     return getWeather(location, userTier);
-   },
+   execute: async (inputData, context) => {
+     const location = inputData.location;
+     const userTier = context?.requestContext?.get('userTier');
+     return getWeather(location, userTier);
+   },
  });
```

- Agent-only properties under `context.agent` (`suspend`, `resumeData`), workflow-only under `context.workflow` (`state`, `setState`), MCP under `context.mcp`.
- `suspendPayload` validates against `suspendSchema`; `resumeData` validates against `resumeSchema`.
- `outputSchema` is now enforced. A mismatch returns a `ValidationError` (`outputValidation: 'strict'` default). `outputValidation: 'warn'` logs and returns the original output.
- `tool.execute` return type includes `ValidationError`; narrow before reading fields.

## Workflows

| Change | Codemod |
|---|---|
| `getWorkflows` to `listWorkflows` | `v1/mastra-plural-apis` |
| `RuntimeContext` to `RequestContext` in steps | `v1/runtime-context` |
| `createRunAsync` to `createRun` | `v1/workflow-create-run-async` |
| `runCount` to `retryCount` (old name deprecated) | `v1/workflow-run-count` |
| `getInitData()` returns `unknown`; use `getInitData<any>()` | `v1/workflow-get-init-data` |
| `getWorkflowRuns` to `listWorkflowRuns` | `v1/workflow-list-runs` |
| `streamVNext`, `resumeStreamVNext`, `observeStreamVNext` removed | `v1/workflow-stream-vnext` |

Also: inputs validate by default (opt out with `options: { validateInputs: false }`), step `suspendPayload` validates, `.branch()` outputs are optional, `writableStream` became an `outputWriter` callback on `Run.start()` and `Run.timeTravel()`, `setState()` is async and validated. Removed: `suspend()`/`setState()` in condition functions, legacy workflows export, `pipeThrough`/`pipeTo`, watch events API, `waitForEvent`, `sendEvent`.

## Memory

New defaults: `lastMessages` 10 (was 40), semantic recall off, title generation off, scope `resource` (was `thread`). Restore old behavior explicitly:

```diff
const memory = new Memory({
    storage,
    vector,
    embedder,
+   options: {
+     lastMessages: 40, // Was default before
+     semanticRecall: {
+       topK: 2,
+       messageRange: 2,
+       scope: 'thread',
+     }, // Was enabled by default before
+     generateTitle: true, // Was enabled by default before
+   },
  });
```

- `threads.generateTitle` to `options.generateTitle`.
- `memory.readOnly` to `memory.options.readOnly` (codemod `v1/memory-readonly-to-options`).
- `Memory.query()` to `Memory.recall()` (codemods `v1/memory-query-to-recall`, `v1/memory-vector-search-param`).
- `MastraMessageV2` to `MastraDBMessage` (codemod `v1/memory-message-v2-type`).
- Removed: working memory `text-stream` mode, `rememberMessages()`, `format` parameter, `MastraMessageV3`, `processors` in the constructor.

## Storage and database

Database steps (run through your normal migration process):

```sql
-- Scorers: only with @mastra/pg or @mastra/libsql and existing score data
UPDATE mastra_scorers SET "requestContext" = "runtimeContext" WHERE "runtimeContext" IS NOT NULL;
ALTER TABLE mastra_scorers DROP COLUMN "runtimeContext";

-- PostgreSQL only, recommended: TEXT to JSONB
ALTER TABLE mastra_threads
ALTER COLUMN metadata TYPE jsonb
USING metadata::jsonb;

ALTER TABLE mastra_workflow_snapshot
ALTER COLUMN snapshot TYPE jsonb
USING snapshot::jsonb;
```

Duplicate spans: `npx mastra migrate`. For ClickHouse, LibSQL, MongoDB, MSSQL you can also call `observabilityStore.checkSpansMigrationStatus()` and `migrateSpans()` from `await mastra.getStorage().getStore('observability')`.

API changes: `MastraStorage` to `MastraCompositeStore` (can compose domains from different adapters), `id` required, `offset/limit` to `page/perPage` (0-indexed), domain access via `getStore()`, `getMessagesPaginated` to `listMessages`, `getThreadsByResourceId` to `listThreads`, `getWorkflowRuns` to `listWorkflowRuns`, `getMessagesById` to `listMessagesById`, `PostgresStore` `schema` to `schemaName`, score methods to `listScoresBy*`. Removed: non-paginated functions, `getTraces`/`getTracesPaginated`, evals test utilities, MSSQL `TABLE_EVALS`.

```diff
memoryStore.listMessages({
    threadId: 'thread-123',
-   offset: 0,
-   limit: 20,
+   page: 0,
+   perPage: 20,
  });
```

## Vectors and RAG

Named arguments everywhere:

```diff
- await vectorDB.query(indexName, [1, 2, 3], 5);
+ await vectorDB.query({
+   indexName: indexName,
+   queryVector: [1, 2, 3],
+   topK: 5,
+ });
```

`id` required, `getVectors` to `listVectors`, `PgVector` takes an object (codemod `v1/vector-pg-constructor`), `defineIndex` to `buildIndex`, `LibSQLVector` `connectionUrl` to `url`, `OpenSearchVector` `url` to `node`, `PineconeVector` `environment` removed. RAG chunking: `keepSeparator` to `separatorPosition`.

## Tracing and observability

v1 ignores `telemetry:` with no error. Install `@mastra/observability` and configure exporters in the same change (see `examples.md`). `processors` to `spanOutputProcessors`; custom exporter `exportEvent` to `exportTracingEvent`; `instrumentation.mjs` and custom instrumentation files removed. For OTLP, install `@mastra/otel-exporter` and `@opentelemetry/exporter-trace-otlp-proto`.

## Evals and scorers

`runExperiment` to `runEvals` (codemod `v1/evals-run-experiment`), `getScorerByName` to `getScorerById` (codemod `v1/evals-scorer-by-name`), scorer `name` to `id`, prebuilt scorers from `@mastra/evals/scorers/prebuilt` (codemod `v1/evals-prebuilt-imports`), scorer messages use `MastraDBMessage` with nested `content`, `createUIMessage` to `createTestMessage`. Legacy evals and `TMetrics` removed.

## MCP, processors, voice

- MCP: `listMCPServers`, `listTools` (codemod `v1/mcp-get-tools`), `listToolsets` (codemod `v1/mcp-get-toolsets`), tool context under `context.mcp`, deprecated client classes removed.
- Processors: `name` to `id`, `MastraMessageV2` to `MastraDBMessage`, memory processor exports moved to core.
- Voice: `@mastra/speech-*` to `@mastra/voice-*`; `speakProvider`, `listenProvider`, `realtimeProvider` to `output`, `input`, `realtime` (codemod `v1/voice-property-names`).

## Client SDK

`messages` match core agent syntax, `threadId`/`resourceId` to `memory`, `Get*` types to `List*`, `offset/limit` to `page/perPage`, `getMemoryThread` parameter shape, unified `runById` for workflow runs. Removed: `runExecutionResult`, `toAISdkFormat`, network memory methods and endpoints, watch types, deprecated stream endpoints, `streamVNext` variants, eval types. Codemods: `v1/client-msg-function-args`, `v1/client-sdk-types`, `v1/client-offset-limit`, `v1/client-get-memory-thread`, `v1/client-to-ai-sdk-format`.

## CLI and deployment

- Added `mastra migrate`.
- Removed `mastra build --env` (use `mastra start --env`), `mastra dev --port` (use `server.port`), telemetry flags.
- The v1 guide lists `mastra deploy` as removed. The current CLI has a new `mastra deploy` for Mastra Platform (see `mastra-platform`).
- OpenAPI spec moved from `/openapi.json` to `/api/openapi.json`.
- `CloudflareDeployer` uses wrangler property names (`name`, `d1_databases`, `kv_namespaces`); `workerNamespace` removed. Old names migrate at runtime with warnings.
