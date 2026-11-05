# Phase map: commands, APIs, and files

Verify each API in the linked skill before use. This map shows where things go, not every option.

| Phase | Commands | Key APIs | Files |
|---|---|---|---|
| 2 Scaffold | `npm create mastra@latest`, `npx mastra dev` | `new Mastra({...})` | `package.json` (`"type": "module"`), `tsconfig.json` (ES2022), `.env`, `src/mastra/index.ts` |
| 3 First slice | `npx mastra api agent ...` to call it (see `mastra-cli-api`) | `new Agent({ id, name, instructions, model })`, `createTool({...})`, `createWorkflow`/`createStep` | `src/mastra/agents/*.ts`, `src/mastra/tools/*.ts`, `src/mastra/workflows/*.ts` |
| 4 Context | | `new Memory({...})` from `@mastra/memory`, `structuredOutput: { schema }`, `MDocument` and vector query tool from `@mastra/rag` | `src/mastra/memory.ts`, ingestion scripts |
| 5 Control | | `defaultOptions: { maxSteps, modelSettings: { timeout } }`, `inputProcessors`, `outputProcessors`, `requireToolApproval`, `suspend()` | Agent files |
| 6 Evals | | `mastra.datasets.create({ id, name })`, `dataset.addItems({ items })`, `createScorer({...}).analyze().generateScore().generateReason()`, `runEvals({ target, data, scorers })` | `src/mastra/scorers/*.ts`, `scripts/seed-dataset.ts`, `scripts/eval-regression.ts` |
| 7 Observability | | `observability` config on `new Mastra`, exporters | `src/mastra/index.ts` |
| 8 Integrate | | `MastraClient` from `@mastra/client-js`, `chatRoute` from `@mastra/ai-sdk`, `registerApiRoute`, auth providers | App routes, frontend |
| 9 Deploy | `npx mastra build`, `npx mastra deploy` (Platform) | Storage adapter (for example `@mastra/pg`), deployer or framework | CI workflow, infra config |

## Project layout

```
src/mastra/
  index.ts          # new Mastra({ agents, workflows, scorers, storage, observability })
  agents/
  tools/
  workflows/
  scorers/
scripts/
  seed-dataset.ts
  eval-regression.ts
.env.example        # names of required env vars, no values
```

## Environment variables by phase

| Phase | Variables |
|---|---|
| 2 | Provider key for the chosen model, for example `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (see `mastra-models`) |
| 6 | Judge model provider key if different from the agent's |
| 7 | Exporter keys (Langfuse, Datadog, etc.) |
| 9 | Database URL for storage, deploy target credentials |
