# Migration tooling reference

Distilled from `https://mastra.ai/reference/migrations/upgrade-to-v1/*` and `https://mastra.ai/reference/cli/mastra`. Codemods live at `https://github.com/mastra-ai/mastra/tree/main/packages/codemod`.

## Contents

- Upgrade commands
- Codemod catalog
- Rename map
- Data migration commands

---

## Upgrade commands

```bash
# Versions
npm list @mastra/core mastra

# Update every Mastra package together (add any other @mastra/* you use)
npm install @mastra/core@latest @mastra/loggers@latest @mastra/memory@latest mastra@latest

# All v1 codemods
npx @mastra/codemod@latest v1

# One codemod on the current directory
npx @mastra/codemod@latest v1/runtime-context .
```

pnpm: `pnpm dlx @mastra/codemod@latest ...`. Yarn: `yarn dlx ...`. Bun: `bun x ...`.

Requirements: Node.js `22.13.0` or later. Latest 0.x before moving to v1.

## Codemod catalog

| Codemod | Change |
|---|---|
| `v1` | Every v1 codemod |
| `v1/mastra-core-imports` | Root `@mastra/core` imports to subpaths |
| `v1/experimental-auth` | `experimental_auth` to `auth` |
| `v1/mastra-plural-apis` | `getAgents`, `getWorkflows`, `getVectors`, `getScorers`, `getMCPServers`, `getLogs`, `getLogsByRunId` to `list*` |
| `v1/runtime-context` | `RuntimeContext`/`runtimeContext` to `RequestContext`/`requestContext` |
| `v1/agent-property-access` | `agent.llm`, `agent.tools`, `agent.instructions` to getters |
| `v1/agent-voice` | Voice methods to `agent.voice.*` |
| `v1/agent-processor-methods` | Processor `get*` to `list*` |
| `v1/agent-abort-signal` | `modelSettings.abortSignal` to top-level `abortSignal` |
| `v1/agent-generate-stream-v-next` | `generateVNext`/`streamVNext` to `generate`/`stream` |
| `v1/client-msg-function-args` | Client `messages` match core agent syntax |
| `v1/client-sdk-types` | Client `Get*` types to `List*` |
| `v1/client-offset-limit` | Client `offset/limit` to `page/perPage` |
| `v1/client-get-memory-thread` | `getMemoryThread` parameters |
| `v1/client-to-ai-sdk-format` | Removes `toAISdkFormat` |
| `v1/evals-run-experiment` | `runExperiment` to `runEvals` |
| `v1/evals-scorer-by-name` | `getScorerByName` to `getScorerById` |
| `v1/evals-prebuilt-imports` | Scorer imports to `@mastra/evals/scorers/prebuilt` |
| `v1/mcp-get-tools` | `getTools` to `listTools` |
| `v1/mcp-get-toolsets` | `getToolsets` to `listToolsets` |
| `v1/memory-readonly-to-options` | `memory.readOnly` to `memory.options.readOnly` |
| `v1/memory-query-to-recall` | `Memory.query()` to `Memory.recall()` |
| `v1/memory-vector-search-param` | `recall()` parameter changes |
| `v1/memory-message-v2-type` | `MastraMessageV2` to `MastraDBMessage` |
| `v1/storage-get-messages-paginated` | `getMessagesPaginated` to `listMessages` |
| `v1/storage-list-threads-by-resource-to-list-threads` | `getThreadsByResourceId` to `listThreads` |
| `v1/storage-list-workflow-runs` | Storage `getWorkflowRuns` to `listWorkflowRuns` |
| `v1/storage-list-messages-by-id` | `getMessagesById` to `listMessagesById` |
| `v1/storage-postgres-schema-name` | `PostgresStore` `schema` to `schemaName` |
| `v1/vector-pg-constructor` | `PgVector` connection string to object |
| `v1/voice-property-names` | `speakProvider`/`listenProvider`/`realtimeProvider` to `output`/`input`/`realtime` |
| `v1/workflow-create-run-async` | `createRunAsync` to `createRun` |
| `v1/workflow-run-count` | `runCount` to `retryCount` |
| `v1/workflow-get-init-data` | `getInitData()` to `getInitData<any>()` |
| `v1/workflow-list-runs` | Workflow `getWorkflowRuns` to `listWorkflowRuns` |
| `v1/workflow-stream-vnext` | Removes workflow `streamVNext` variants |

No codemod is documented for: memory default changes, `threadId`/`resourceId` to `memory`, `format` removal, tripwire format, telemetry to observability, CLI flag removals, `CloudflareDeployer` property names, vector store positional to named arguments.

## Rename map

| Area | Before | After |
|---|---|---|
| Mastra | `experimental_auth` | `auth` |
| Mastra | `mastra.getTool('configKey')` | `mastra.getTool(tool.id)` |
| Agent | `agent.llm`, `agent.tools`, `agent.instructions` | `agent.getLLM()`, `await agent.listTools()`, `agent.getInstructions()` |
| Agent | `agent.fetchMemory()` | `(await agent.getMemory()).recall()` |
| Agent | `output` option | `structuredOutput.schema` |
| Agent | `threadId`, `resourceId` options | `memory: { thread, resource }` |
| Agent | `TMetrics` generic | Removed |
| Tools | `execute({ context, ... })` | `execute(inputData, context)` |
| Tools | `suspend`, `resumeData` | `context.agent.*` or `context.workflow.*` |
| MCP tools | `elicitation`, `extra` | `context.mcp.elicitation`, `context.mcp.extra` |
| Memory | `threads.generateTitle` | `options.generateTitle` |
| Memory | `processors` in constructor | Removed (memory processors moved to core) |
| Storage | `MastraStorage` | `MastraCompositeStore` |
| Storage | `offset`/`limit` | `page`/`perPage` |
| Storage | Score `getScores({ scorerName })` | `listScoresByScorerId({ scorerId })` |
| Vectors | `LibSQLVector` `connectionUrl` | `url` |
| Vectors | `OpenSearchVector` `url` | `node` |
| Vectors | `PgVector` `defineIndex` | `buildIndex` |
| RAG | `keepSeparator` | `separatorPosition` |
| Evals | Scorer `name` | `id` (`name` optional) |
| Evals | `createUIMessage` | `createTestMessage` |
| Processors | `name` | `id` |
| Tracing | `telemetry:` | `observability: new Observability({...})` |
| Tracing | `processors` | `spanOutputProcessors` |
| Tracing | `exportEvent` | `exportTracingEvent` |
| Tracing | `CloudExporter`, `DefaultExporter` | `MastraPlatformExporter`, `MastraStorageExporter` (old names deprecated) |
| Voice | `@mastra/speech-*` | `@mastra/voice-*` |
| Server | `GET /openapi.json` | `GET /api/openapi.json` |
| Cloudflare | `projectName`, `d1Databases`, `kvNamespaces` | `name`, `d1_databases`, `kv_namespaces` |
| CLI | `mastra build --env` | `mastra start --env` |
| CLI | `mastra dev --port` | `server.port` |
| CLI | `--no-telemetry` | Removed |

## Data migration commands

```bash
npx mastra migrate
```

Removes duplicate `(traceId, spanId)` rows and adds the unique constraint; also copies ClickHouse legacy spans to the vNext schema. SQL steps for scorers and JSONB are in `v1-changes.md`.
