---
name: mastra-datasets-experiments
description: "Build a repeatable eval loop in Mastra: versioned datasets of test cases, experiments that run a dataset through an agent, workflow, or scorer, comparisons between runs, gates and thresholds that produce a passed, scored, or failed verdict, CI scripts, and Vitest matchers. Use this skill whenever the user wants a golden dataset, regression tests for an agent, to compare prompts or models, to block a deploy on eval results, to mock tools during evals, or to run evals in Vitest or GitHub Actions. Triggers on mastra.datasets, dataset.addItems, dataset.startExperiment, startExperimentAsync, compareExperiments, runExperimentItem, submitExperimentResult, toolMocks, unmockedToolPolicy, runEvals gates, verdict, threshold, expectEvals, expectEval, MastraEvalsReporter, @mastra/evals/vitest, toHaveVerdict, eval loop. Also triggers when the user asks whether a prompt or model change made the agent better or worse."
license: Apache-2.0
metadata:
  category: quality
  catalog_summary: "Versioned datasets, experiments, comparisons, gates and verdicts, CI and Vitest integration, the eval loop"
  display_order: 2
  docs: https://mastra.ai/docs/evals/datasets
---

# Mastra Datasets and Experiments

Turn scorers into a repeatable loop: curate a versioned dataset, run experiments against it, compare runs, and gate releases on a verdict.

---

## When to use

- Creating a golden dataset of inputs and ground truth, in code or from production traces
- Running an experiment against a registered agent, workflow, or scorer
- Comparing two or more experiments (prompt change, model swap, code change)
- Making evals deterministic with tool mocks
- Failing CI when quality drops, with gates, thresholds, and a verdict
- Running evals as Vitest tests with matchers and a score reporter
- Driving experiments from an external orchestrator (Temporal, Airflow, workers)

## When NOT to use

- Choosing or writing scorers, Quick Checks, live scoring (use `mastra-evals`)
- Traces, logs, metrics, user feedback (use `mastra-observability`)
- The Studio UI for datasets and experiments (use `mastra-studio-editor`)
- Configuring storage adapters (use `mastra-storage`)
- The `mastra api` CLI in depth (use `mastra-cli-api`)
- Overall build process from idea to production (use `mastra-build-playbook`)

---

## Required inputs

- The target and how it is registered (`targetType` plus `targetId`, or an agent from `mastra.getAgent()`)
- A storage adapter with the `datasets` domain (LibSQL, PostgreSQL, MongoDB, and others)
- Five or more representative cases with `input` and `groundTruth` (expected meaning, not exact wording)
- The scorers, registered on the `Mastra` instance (see `mastra-evals`)
- Pass criteria: which checks are hard gates, which scores need a threshold
- Whether tools have side effects that must be mocked

---

## The framework: dataset, experiment, verdict

| Concept | API | Persisted | Answers |
|---|---|---|---|
| Dataset | `mastra.datasets.create()`, `dataset.addItems()` | Yes, versioned on every change | What should the agent handle? |
| Experiment | `dataset.startExperiment()` | Yes (results, scores, traces) | How did this version do on each item? |
| Comparison | `mastra.datasets.compareExperiments()` | Read-only | What changed between runs? |
| Verdict | `runEvals({ gates, scorers: [{ scorer, threshold }] })` | Scores only | Should this ship? |

Experiment `status` and counts describe **execution**, not quality. A `completed` experiment with `failedCount: 0` can still score 0 on every item. Verdicts belong to `runEvals`.

```typescript
import { mastra } from '../src/mastra'

const dataset = await mastra.datasets.create({ name: 'translation-pairs' })
await dataset.addItems({
  items: [
    { input: 'Hello', groundTruth: 'Hola' },
    { input: 'Thank you', groundTruth: 'Gracias' },
  ],
})

const summary = await dataset.startExperiment({
  name: 'baseline',
  targetType: 'agent',
  targetId: 'translation-agent',
  scorers: ['accuracy'],
})

for (const item of summary.results) {
  for (const s of item.scores) console.log(item.itemId, s.scorerName, s.score, s.reason)
}
```

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and `node_modules/@mastra/evals/dist/docs/` plus the installed types. Otherwise fetch `https://mastra.ai/docs/evals/datasets.md`, `https://mastra.ai/docs/evals/experiments.md`, and `https://mastra.ai/reference/datasets/startExperiment.md`. Trust these over memory. Datasets need `@mastra/core` 1.4.0 or later.
2. **Configure storage** on `new Mastra({ storage })` with an adapter that provides the `datasets` domain.
3. **Seed a small golden dataset.** Five to ten cases you can read by hand. Add `inputSchema` and `groundTruthSchema` to reject malformed items. Pass a fixed `id` when scripts need to find it again.
4. **Register the target and scorers** on the `Mastra` instance. Experiments reference them by ID.
5. **Mock side-effecting tools** with per-item `toolMocks`, and set `unmockedToolPolicy: 'deny'` when a live call would be harmful.
6. **Run a baseline experiment** with a descriptive `name`. Read every output, score, and reason.
7. **Change one thing** (instructions, model through `agentModel`, a tool). Keep the dataset version and scorers fixed. Run again.
8. **Compare** in Studio or with `compareExperiments({ experimentIds, baselineId })`.
9. **Grow the dataset** from production traces (Studio: Add full trace to dataset) whenever a new failure appears.
10. **Gate releases** with a `runEvals` script or Vitest test that requires `verdict === 'passed'` and exits non-zero otherwise.

---

## Deep dive: gates, thresholds, verdict

```typescript
import { runEvals } from '@mastra/core/evals'
import { checks } from '@mastra/evals/checks'
import { mastra } from '../src/mastra'

const result = await runEvals({
  target: mastra.getAgent('weatherAgent'),
  data: [{ input: 'What is the weather in Brooklyn?' }],
  gates: [checks.calledTool('get_weather'), checks.noToolErrors()],
  scorers: [
    { scorer: mastra.getScorer('faithfulnessScorer'), threshold: 0.7 },
    { scorer: mastra.getScorer('hallucinationScorer'), threshold: { max: 0.3 } },
    checks.includes('Brooklyn'), // tracked only
  ],
})

if (result.verdict !== 'passed') process.exitCode = 1
```

| Verdict | Meaning |
|---|---|
| `failed` | A gate averaged below 1.0 (a throwing gate counts as 0) |
| `scored` | Gates passed, a threshold was missed |
| `passed` | All gates at 1.0 and all thresholds met |
| absent | No gates or thresholds, or all returned `notScorable()` |

Averages hide single failures. Five 1s and one 0 average 0.83. For "every item must pass", use a binary scorer with `threshold: 1` or make it a gate.

---

## Failure patterns

- **Treating `status: 'completed'` as success.** It only means items executed. Read `results[].scores`.
- **`startExperiment` throws on scorer ID.** The ID in `scorers` (run or dataset level) is not registered. Register it on `new Mastra({ scorers })`. A stale item-level ID fails only that item with `EXPERIMENT_ITEM_SCORER_NOT_FOUND`.
- **Expecting scorer sources to merge.** Run-level `scorers` override item `scorerIds`, which override dataset `scorerIds`. `[]` means no scorers. `null` on an item update restores inheritance.
- **Experiments sending real emails or refunds.** Add `toolMocks` and `unmockedToolPolicy: 'deny'`. Mocks match `args` strictly unless `matchArgs: 'ignore'`.
- **Tool mocks on a workflow target.** Supported for `agent` targets only. MySQL rejects mocks.
- **Memory leaks between items.** A shared resource id shares working memory and semantic recall. Use a dedicated evaluation resource or let the runner isolate each item.
- **Comparing runs on different data.** Pin `version` so both experiments use the same dataset snapshot.
- **Vitest timeouts.** LLM evals exceed the 5-second default. Set `timeout` per test or `testTimeout`, and lower `concurrency` or set `fileParallelism: false` on rate limits.
- **Gate never fires on a judge scored 1 to 10.** Thresholds are 0 to 1 and the judge's number is stored as returned. Fix the judge prompt (see `mastra-evals`).
- **`listItems({ version })` returning a bare array.** That form is deprecated. Pass `page` and `perPage` for the paginated shape.
- **Importing the agent into `runEvals` directly.** Scores do not persist and registry lookups fail. Use `mastra.getAgent()`.

---

## Output format

A finished eval-loop delivery contains:

- A seed script (for example `scripts/seed-dataset.ts`) that creates the dataset with schemas and a fixed `id`
- Registered target and scorers in `src/mastra/index.ts`, with dataset-capable `storage`
- An experiment script or Studio instructions, with named baseline and candidate runs
- A regression check (`scripts/eval-regression.ts` or `*.eval.test.ts`) that fails on any verdict other than `passed`
- CI wiring that runs the check before deploy, with provider keys as secrets
- A short readme section on how to add a case from a production trace

---

## Reference files

- [`references/api.md`](references/api.md) - `DatasetsManager`, `Dataset` methods, `startExperiment` options and summary, caller-driven experiments, tool mocks, Vitest API.
- [`references/examples.md`](references/examples.md) - Golden dataset and baseline, tool-mocked experiment, CI regression script, Vitest suite.
- [`references/checklist.md`](references/checklist.md) - Dataset quality and CI gating checklist.

**Live docs**

- https://mastra.ai/docs/evals/datasets
- https://mastra.ai/docs/evals/experiments
- https://mastra.ai/docs/evals/gates-and-verdicts
- https://mastra.ai/docs/evals/running-in-ci
- https://mastra.ai/docs/evals/vitest-integration
- https://mastra.ai/docs/guides/build-an-eval-loop
- https://mastra.ai/reference/datasets/startExperiment
- https://mastra.ai/reference/datasets/dataset
