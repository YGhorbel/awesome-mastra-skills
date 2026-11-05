# Datasets and experiments API reference

Distilled from `https://mastra.ai/reference/datasets/*.md`, `https://mastra.ai/docs/evals/experiments.md`, and `https://mastra.ai/docs/evals/vitest-integration.md`. Datasets were added in `@mastra/core@1.4.0`. Verify against the installed version.

## Contents

- DatasetsManager (`mastra.datasets`)
- Dataset item methods
- Item fields
- startExperiment options
- ExperimentSummary
- Async and caller-driven experiments
- Tool mocks
- Lifecycle hooks and events
- Snapshot utilities
- Vitest integration
- CLI

---

## `DatasetsManager` (`mastra.datasets`)

| Method | Notes |
|---|---|
| `create({ name, description?, inputSchema?, groundTruthSchema?, metadata? })` | Returns a `Dataset`. Schemas are Standard JSON Schema (Zod, Valibot, ArkType). The eval-loop guide also passes `id`. |
| `get({ id })` | Returns a `Dataset`. |
| `list({ page?, perPage?, filters? })` | `{ datasets, pagination }`. Filters: `name`, `targetType`, `targetIds`, `datasetIds`, `organizationId`, `projectId`. |
| `delete({ id })` | Deletes a dataset. |
| `getExperiment({ experimentId })` | Across all datasets. |
| `deleteExperiment({ experimentId, organizationId?, projectId? })` | Also deletes its traces, spans, scores, feedback, logs where storage supports it. |
| `compareExperiments({ experimentIds, baselineId? })` | Needs 2 distinct IDs. Returns `{ baselineId, items: [{ itemId, input, groundTruth, results: { [expId]: { output, scores } \| null } }] }`. |

`new Dataset(id, mastra)` exists but skips tenancy scoping.

## Dataset item methods

| Method | Notes |
|---|---|
| `addItem(item)` / `addItems({ items })` | Bumps the version. Items failing the schema are rejected. |
| `updateItem({ itemId, ...fields })` | Bumps the version. `scorerIds: null` restores inheritance, `[]` disables scoring, omitted keeps value. |
| `deleteItem({ itemId })` / `deleteItems({ itemIds })` | Bumps the version. Content stays in history. |
| `purgeItem({ itemId })` | `@mastra/core@1.65.0`. Redacts content across history and linked results. No new version. Irreversible. MongoDB needs transactions. |
| `getItem`, `getItemHistory({ itemId })` | History rows carry `datasetVersion`. |
| `listItems({ version?, page?, perPage?, search? })` | Paginated `{ items, pagination }`. `version` alone returns a deprecated bare array. Default `perPage` 20. |
| `listVersions()` | `{ versions, pagination }`. |
| `getDetails()` / `update({...})` / `delete()` | Dataset record: `id`, `name`, `description`, schemas, `version`, timestamps. |
| `listExperiments({ page?, perPage? })` | `{ experiments, pagination }`. |
| `getExperiment({ experimentId })` | May return `null`. |
| `listExperimentResults({ experimentId, page?, perPage?, traceId?, status? })` | Per-item rows with `output`, `error`, `traceId`, `retryCount`. |

## Item fields

| Field | Notes |
|---|---|
| `input` | Passed to the target. Agents accept a string, message, or message array. Workflows get it as `inputData`. Scorer targets call `scorer.run(item.input)`. |
| `groundTruth` | Expected outcome, passed to scorers as `run.groundTruth`. |
| `expectedTrajectory` | For trajectory scorers. |
| `scorerIds` | Item-level scorer override. |
| `metadata` | Available to inline `task` and hooks. |
| `requestContext` | Applied when the item runs. Can carry `MASTRA_RESOURCE_ID_KEY` or `MASTRA_THREAD_ID_KEY`. |
| `toolMocks` | `[{ toolName, args, output, matchArgs? }]`, agent targets only. |
| `unmockedToolPolicy` | `'allow' \| 'deny'`, overrides the experiment value. |
| `externalId` | Stable identity for idempotent inserts. Do not put sensitive data in it. |

---

## `dataset.startExperiment(options)`

Blocks until all items finish.

| Option | Notes |
|---|---|
| `targetType` + `targetId` | `'agent' \| 'workflow' \| 'scorer'` and the registered ID. |
| `task` | Inline `async ({ input, metadata, ... }) => output` instead of a registered target (shown in the docs, not in the reference table). |
| `agentModel` | Run an agent target on another model without changing the agent. Recorded as `metadata.agentModel`. |
| `scorers` | `(MastraScorer \| string)[]`, `AgentScorerConfig`, or `WorkflowScorerConfig`. Overrides item and dataset scorer IDs. |
| `name`, `description`, `metadata` | Labels. |
| `version` | Pin a dataset version. Default latest. |
| `maxConcurrency` | Default 5. |
| `itemTimeout` | Per-item ms. |
| `maxRetries` | Default 0. Exponential backoff. Abort errors never retry. |
| `signal` | `AbortSignal`. Remaining items become skipped. |
| `unmockedToolPolicy` | `'allow'` (default) or `'deny'`. |
| `requestContext` | Experiment-level request context (item values win). |
| `beforeAll`, `beforeEach`, `afterEach`, `afterAll` | Lifecycle hooks. |
| `onEvent` | Serialized lifecycle event observer. |
| `persistence` | `{ experiments?: 'default' \| 'none', scores?: 'default' \| 'none' }`. |

Scorer source per item, first match wins, never merged: run `scorers` > item `scorerIds` > dataset `scorerIds` > none.

## `ExperimentSummary`

| Field | Notes |
|---|---|
| `experimentId` | UUID. |
| `status` | `'pending' \| 'running' \| 'completed' \| 'failed'`. |
| `totalItems`, `succeededCount`, `failedCount`, `skippedCount` | Execution counts. |
| `completedWithErrors` | Finished but some items failed. |
| `startedAt`, `completedAt` | Dates. |
| `results[]` | `itemId`, `itemVersion`, `input`, `output`, `groundTruth`, `error`, `retryCount`, `scores[]`, `toolMockReport?`. |
| `results[].scores[]` | `scorerId`, `scorerName`, `score` (`null` on scorer error), `reason`, `error`. |

---

## Async and caller-driven experiments

| Method | Since | Notes |
|---|---|---|
| `startExperimentAsync(options)` | 1.4.0 | Returns `{ experimentId, status: 'pending' }`. Poll `getExperiment`. |
| `createExperiment({ id?, targetType?, targetId?, scorers?, name?, version?, ... })` | 1.61.0 | Idempotent on caller `id`. Returns `{ experimentId, status, totalItems, datasetVersion }`. |
| `runExperimentItem({ experimentId, itemId, attempt?, requestContext? })` | 1.61.0 | Mastra runs target and scorers for one item. Upsert on `(experimentId, itemId, attempt)`. |
| `submitExperimentResult({ experimentId, itemId, output, scores?, error?, traceId?, attempt? })` | 1.61.0 | For target-less experiments only. |
| `finalizeExperiment({ experimentId })` | 1.61.0 | Computes counts. Idempotent and terminal. |

Errors: `EXPERIMENT_ID_CONFLICT` (409), `EXPERIMENT_ALREADY_FINALIZED` (409), 404 for items not visible at the pinned version.

## Tool mocks

- Strict `args` match by default (key order ignored, array order matters). `matchArgs: 'ignore'` matches by tool name. Mock subagents with tool name `agent-<name>`.
- Repeated mocks for the same `(toolName, args)` are consumed in order.
- Failures abort the run and never retry: `TOOL_MOCK_MISMATCH`, `TOOL_MOCK_EXHAUSTED`, `TOOL_MOCK_NOT_DECLARED`.
- `toolMockReport`: `served`, `unconsumed`, `liveCalls`, `failure`.

## Lifecycle hooks and events

- Hooks receive `experimentId`, `mastra`, `signal`. Item hooks add `item` (`id`, `input`, `groundTruth`, `metadata`). `afterEach` gets `result`, `afterAll` gets `summary`.
- `beforeAll` failure fails the experiment. `beforeEach` failure fails the item (`EXPERIMENT_ITEM_BEFORE_EACH_FAILED`). Teardown failures are logged.
- Events (`import type { ExperimentEvent } from '@mastra/core/datasets'`): `experiment.run.started`, `experiment.item.completed`, `experiment.run.finished`. A throwing observer aborts with `EXPERIMENT_EVENT_OBSERVER_FAILED`.

## Snapshot utilities

`createDatasetSnapshot()` and `parseDatasetSnapshot(text, { maxBytes? })` from `@mastra/core/datasets` build and validate a portable, digest-checked JSON artifact (default 4 MiB budget). They do not import into storage.

---

## Vitest integration (`@mastra/evals/vitest`)

Requires Vitest 3, 4, or 5.

| Export | Use |
|---|---|
| `MastraEvalsReporter` | Add to `test.reporters` to print a score table. |
| `@mastra/evals/vitest/setup` | Add to `test.setupFiles` to register matchers. Or call `registerEvalMatchers()`. |
| `expectEvals(runEvalsConfig).toPass(rate?)` | Dataset assertion. `toPass()` requires every item to pass every gate. Thresholds still apply. Await it. |
| `expectEval({ target, data: item, ... }).toPass()` | Single item, pair with `test.for`. |

Matchers on a `runEvals` result: `toHaveVerdict('passed' \| 'scored' \| 'failed')`, `toHaveScoreAbove(name, min)`, `toHaveScoreBelow(name, max)`, `toPassGates()`, `toPassThresholds()`. Categorized configs use dot paths such as `'trajectory.code-trajectory-accuracy-scorer'`.

## CLI

With a running server (`npx mastra dev` or `--url`): `npx mastra api dataset create '{"name":"..."}'`, `npx mastra api dataset list`, `npx mastra api experiment run <datasetId> '{"name":"..."}'`. Add `--schema` to inspect inputs. Experiments make model calls, so confirm with the user first. See `mastra-cli-api`.
