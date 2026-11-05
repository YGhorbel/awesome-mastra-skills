---
name: mastra-evals
description: "Measure Mastra agent and workflow quality with scorers: the built-in LLM judges and code scorers in @mastra/evals, zero-LLM Quick Checks, custom scorers built with createScorer, live scoring with sampling and eligibility filters, runEvals batches, and multi-turn and memory-aware evals. Use this skill whenever the user wants to evaluate, grade, judge, or test an agent's answers, add scorers to an agent or workflow step, write an LLM-as-judge, check tool calls, or score conversations. Triggers on @mastra/evals, @mastra/core/evals, createScorer, runEvals, checks.calledTool, checks.includes, createAnswerRelevancyScorer, createFaithfulnessScorer, createHallucinationScorer, createToxicityScorer, createRubricScorer, createMultiTurnJudgeScorer, createTrajectoryAccuracyScorerCode, notScorable, filterRun, scorers sampling, mastra_scorers. Also triggers when the user asks how to know whether an agent is any good, even if they never say eval or scorer."
license: Apache-2.0
metadata:
  category: quality
  catalog_summary: "Built-in and custom scorers, Quick Checks, createScorer pipeline, live scoring with sampling, runEvals, multi-turn and memory evals"
  display_order: 1
  docs: https://mastra.ai/docs/evals/overview
---

# Mastra Evals

Score agent and workflow output with scorers: built-in LLM judges, deterministic Quick Checks, and your own `createScorer` pipelines, run live or in batches with `runEvals`.

---

## When to use

- Picking built-in scorers for relevancy, faithfulness, hallucination, toxicity, bias, tool use, or trajectories
- Writing a custom scorer (rule-based, LLM judge, or mixed) with `createScorer`
- Adding live scoring to an agent or workflow step, with sampling and eligibility filters
- Asserting tool calls or text content with Quick Checks (`checks.*`)
- Running a batch of inputs through an agent with `runEvals`
- Evaluating multi-turn conversations or memory-enabled agents
- Making scores persist so they show up in Studio

## When NOT to use

- Stored datasets, experiments, comparing runs, CI gates, Vitest matchers (use `mastra-datasets-experiments`)
- Traces, spans, logs, metrics, user feedback (use `mastra-observability`)
- Reviewing scores and running experiments in the Studio UI (use `mastra-studio-editor`)
- Blocking bad input or output at runtime (use `mastra-processors-guardrails`)
- Classifying text into labels outside of scoring (use `mastra-classifier`)
- Defining the agent itself (use `mastra-agents`)
- Memory and thread setup (use `mastra-memory`)

---

## Required inputs

- The target: an agent or workflow registered on `new Mastra({...})`
- What "good" means: one sentence per quality dimension (correct, grounded, safe, used the right tool)
- Whether each dimension is deterministic (Quick Check or code scorer) or needs judgment (LLM judge)
- The judge model as a `provider/model` string, ideally from a different provider than the agent
- Live or offline: sampling rate for production, or a list of test inputs with optional `groundTruth`
- Whether the agent uses memory (thread-scoped memory needs a thread per eval)

---

## The framework: scorer, pipeline, runner

A scorer is a `MastraScorer`. Every scorer, built-in or custom, runs the same four-step pipeline:

1. `preprocess` (optional): extract or normalize data
2. `analyze` (optional): gather evidence
3. `generateScore` (required): return a number
4. `generateReason` (optional): explain the score

Each step is a **function** (deterministic, no LLM call) or a **prompt object** (`description` + `createPrompt`, plus `outputSchema` for `preprocess`/`analyze`) that calls the judge.

```typescript
// src/mastra/scorers/quote-sources.ts
import { createScorer } from '@mastra/core/evals'
import { z } from 'zod'

export const quoteSourcesScorer = createScorer({
  id: 'quote-sources',
  description: 'Check if the response includes sources',
  judge: { model: 'openai/gpt-6-luna', instructions: 'You are a strict evaluator.' },
})
  .analyze({
    description: 'Detect whether sources are present',
    outputSchema: z.object({ hasSources: z.boolean(), sources: z.array(z.string()) }),
    createPrompt: ({ run }) => `Does the response contain sources? Extract them.\n\n${run.output}`,
  })
  .generateScore(({ results }) => (results.analyzeStepResult.hasSources ? 1 : 0))
```

Three ways to run scorers:

| Runner | How | Use for |
|---|---|---|
| Live | `scorers: { name: { scorer, sampling } }` on an `Agent` or `createStep` | Production monitoring, async, non-blocking |
| Batch | `runEvals({ target, data, scorers })` from `@mastra/core/evals` | Local checks, CI scripts, multi-turn |
| Direct | `scorer.run({ input, output, groundTruth })` | Unit-testing a scorer |

Scores land in the `mastra_scorers` table only when the `Mastra` instance has `storage` and the scorer is registered (see Deep dive: persistence).

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/evals/dist/docs/` and `node_modules/@mastra/core/dist/docs/` plus the installed types. Otherwise fetch `https://mastra.ai/docs/evals/overview.md`, `https://mastra.ai/reference/evals/create-scorer.md`, and `https://mastra.ai/reference/evals/run-evals.md`. Trust these over memory.
2. **Install.** `npm install @mastra/evals@latest`. `createScorer`, `runEvals`, `filterRun`, and `notScorable` come from `@mastra/core/evals`. Built-ins come from `@mastra/evals/scorers/prebuilt`, checks from `@mastra/evals/checks`, helpers from `@mastra/evals/scorers/utils`.
3. **Map each quality dimension to a scorer.** Deterministic first: Quick Checks for tool calls and text, code scorers for trajectories. Then LLM judges for semantics (see `references/api.md` for the full built-in list).
4. **Write custom scorers** in `src/mastra/scorers/`. Use `type: 'agent'` for agent targets so `run.input` and `run.output` are typed and the scorer also works on traces.
5. **Anchor judge scales.** In a prompt-object `generateScore`, name both endpoints and at least one middle value. Clamp in a function step if the range must hold.
6. **Skip irrelevant runs.** Return `notScorable('reason')` from a function step (usually `preprocess`) instead of scoring 0.
7. **Register scorers** on `new Mastra({ scorers: {...}, storage })` so scores persist and appear in Studio.
8. **Attach live scorers** to the agent or step with `sampling: { type: 'ratio', rate }`. Add a `filter` to target a segment.
9. **Run a batch** with `runEvals`, resolving the target through `mastra.getAgent()` or `mastra.getWorkflow()`.
10. **Read scores and reasons**, not only averages. Move stable checks into CI (see `mastra-datasets-experiments`).

---

## Deep dive: live scoring and persistence

```typescript
import { Agent } from '@mastra/core/agent'
import { createAnswerRelevancyScorer, createToxicityScorer } from '@mastra/evals/scorers/prebuilt'

export const evaluatedAgent = new Agent({
  id: 'evaluated-agent',
  name: 'Evaluated Agent',
  instructions: 'Answer product questions.',
  model: 'openai/gpt-6.1-sol',
  scorers: {
    relevancy: {
      scorer: createAnswerRelevancyScorer({ model: 'openai/gpt-6-luna' }),
      filter: { op: 'eq', left: { path: 'requestContext.plan' }, right: { literal: 'enterprise' } },
      sampling: { type: 'ratio', rate: 0.1 },
    },
    safety: {
      scorer: createToxicityScorer({ model: 'openai/gpt-6-luna' }),
      sampling: { type: 'ratio', rate: 1 },
    },
  },
})
```

- Sampling is deterministic per trace ID (or run ID without tracing). Scorers at the same rate score the same traces.
- If trace sampling dropped the trace, live scorers skip the run.
- `filter` runs before sampling. It can read `requestContext.*`, `entity.*`, `entityType`, `source`, `threadId`, `resourceId`, `projectId`. It cannot see input or output.
- Attached scorers register themselves. Scorers passed straight to `runEvals` (including checks) must also be listed in `new Mastra({ scorers })`, or each save logs `Scorer with id <id> not found`.
- Lookup is by ID only. One registered `checks.calledTool('get_weather')` covers every `check-called-tool` use.

---

## Failure patterns

- **Scores never appear in Studio.** No `storage`, or the scorer is not in `new Mastra({ scorers })`. Register it (any config with the same ID works).
- **Importing the agent directly into `runEvals`.** Registry lookups fail, scores do not persist, trace trajectories are unavailable. Use `mastra.getAgent('id')` or `mastra.getWorkflow('id')`.
- **Judge returns 1 to 10.** Mastra stores the number unclamped, so thresholds between 0 and 1 always pass. Ask for 0 to 1 with anchored descriptions.
- **Prompt says "return only the number".** The step already requests `{ score: number }`. Remove output-format instructions from `generateScore` prompts.
- **Setting `outputSchema` on a prompt-object `generateScore`.** Not allowed. Only `preprocess` and `analyze` take one.
- **Scoring 0 when the scorer does not apply.** Drags averages down. Return `notScorable()` from a function step.
- **Prebuilt judges on multi-turn `inputs`.** They grade only the last assistant message and see only the first user input. Use `createMultiTurnJudgeScorer` or per-turn `turns[].scorers`.
- **ObservationalMemory `threadId` error in evals.** Thread-scoped memory needs a thread. Pass `targetOptions.memory` and create the thread first (see `references/examples.md`).
- **Same model judges itself.** Bias toward its own answers. Use a judge from another provider and keep it fixed across comparisons.
- **`checks.equals` unexpectedly passing.** It ignores case by default. Pass `{ ignoreCase: false }`.
- **`createContentSimilarityScorer({ ignoreCase: true })` treating whitespace strictly.** Passing an options object turns omitted flags to `false`. Set both flags.

---

## Output format

A finished eval delivery contains:

- `src/mastra/scorers/<scorer-id>.ts` for each custom scorer, exported
- Scorers registered in `src/mastra/index.ts` under `scorers`, with `storage` configured
- Live scorers attached to the agent or step with an explicit `sampling.rate`
- A runnable script or test that calls `runEvals` and prints `scores`, `verdict`, and failing reasons
- The judge model's env var in `.env.example`
- A short note on what each scorer measures and which direction is better (some are lower-is-better)

---

## Reference files

- [`references/api.md`](references/api.md) - `createScorer`, step signatures, `runEvals` options and results, every built-in scorer and Quick Check, helpers.
- [`references/examples.md`](references/examples.md) - Custom judge, Quick Checks plus judge batch, multi-turn conversation, memory-enabled agent.
- [`references/checklist.md`](references/checklist.md) - Scorer design and rollout checklist.

**Live docs**

- https://mastra.ai/docs/evals/overview
- https://mastra.ai/docs/evals/built-in-scorers
- https://mastra.ai/docs/evals/custom-scorers
- https://mastra.ai/docs/evals/quick-checks
- https://mastra.ai/docs/evals/evals-with-memory
- https://mastra.ai/docs/evals/multi-turn
- https://mastra.ai/reference/evals/create-scorer
- https://mastra.ai/reference/evals/run-evals
- https://mastra.ai/reference/evals/checks
