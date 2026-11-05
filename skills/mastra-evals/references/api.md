# Evals API reference

Distilled from `https://mastra.ai/reference/evals/*.md` and `https://mastra.ai/docs/evals/*.md`. Verify against the installed version before relying on an option.

## Contents

- Imports
- createScorer options
- Step signatures
- scorer.run() input and result
- runEvals parameters and result
- Built-in scorers
- Quick Checks
- notScorable and filterRun
- Scorer utilities
- Live scorer config on agents and steps

---

## Imports

| Symbol | Import path |
|---|---|
| `createScorer`, `runEvals`, `filterRun`, `notScorable`, `createClassifierScorer` | `@mastra/core/evals` |
| `extractTrajectory`, `extractWorkflowTrajectory`, `extractTrajectoryFromTrace` | `@mastra/core/evals` |
| Built-in scorer factories (`create*Scorer*`) | `@mastra/evals/scorers/prebuilt` |
| `checks` | `@mastra/evals/checks` |
| `extractToolCalls`, `extractAgentResponseMessages`, `createTestMessage`, ... | `@mastra/evals/scorers/utils` |

Install: `npm install @mastra/evals@latest`.

---

## `createScorer(options)`

| Option | Type | Notes |
|---|---|---|
| `id` | `string` | Required. Used as name when `name` is absent. Persistence and Studio key off it. |
| `name` | `string` | Defaults to `id`. |
| `description` | `string` | Required. Stored with each score. |
| `type` | `'agent' \| 'trajectory' \| { input, output }` | `'agent'` types `run.input` as `ScorerRunInputForAgent` and `run.output` as `ScorerRunOutputForAgent`, and enables trace scoring. Generics also work: `createScorer<In, Out>({...})`. |
| `judge.model` | model | Router string such as `'openai/gpt-6-luna'`. Only needed for prompt-object steps. |
| `judge.instructions` | `string` | Judge system prompt. |
| `judge.jsonPromptInjection` | `boolean \| 'system' \| 'inline' \| 'auto'` | Default `'auto'`. |
| `judge.inputProcessors` / `outputProcessors` | `Processor[]` | Run on the internal judge agent. |
| `judge.errorProcessors` | `Processor[]` | For example `StreamErrorRetryProcessor` to retry transient judge failures. |
| `judge.maxProcessorRetries` | `number` | Defaults to 3 when `errorProcessors` is set. |
| `prepareRun` | `(run) => run \| Promise<run>` | Trim or reshape the run before the pipeline. `filterRun()` builds one. |

A step's own `judge` overrides scorer-level judge fields.

`ScorerRunInputForAgent` has `inputMessages`, `rememberedMessages`, `systemMessages`, `taggedSystemMessages`. `ScorerRunOutputForAgent` is the array of response messages.

---

## Step signatures

| Step | Function mode | Prompt-object mode | Result key |
|---|---|---|---|
| `.preprocess()` | `({ run, results }) => any` | `{ description, outputSchema, createPrompt, judge? }` | `preprocessStepResult` |
| `.analyze()` | `({ run, results }) => any` | `{ description, outputSchema, createPrompt, judge? }` | `analyzeStepResult` |
| `.generateScore()` | `({ run, results }) => number` | `{ description, createPrompt, judge? }` (no `outputSchema`; judge returns `{ score }`) | `score` |
| `.generateReason()` | `({ run, results, score }) => string` | `{ description, createPrompt, judge? }` | `reason` |

`run` carries `input`, `output`, `runId`, `requestContext`, and `groundTruth` (and `expectedTrajectory` for trajectory scorers). All step functions may be async. `generateScore` is the only required step.

---

## `scorer.run(input)`

Input: `{ input, output, runId?, requestContext?, groundTruth? }`.

Result:

| Field | Notes |
|---|---|
| `runId` | Run identifier. |
| `score` | Absent when a step returned `notScorable()`. Check `notScorable` first. |
| `notScorable` | `{ step, reason? }` when skipped. |
| `reason` | From `generateReason`. |
| `preprocessStepResult`, `analyzeStepResult` | Intermediate results. |
| `preprocessPrompt`, `analyzePrompt`, `generateScorePrompt`, `generateReasonPrompt` | Prompts sent to the judge. |
| `judge` | Per-step `{ executions: [...] }` with `status`, `judgeModelId`, `usage`, `durationMs`, `cost?`, `error?`. |

---

## `runEvals(options)`

Import from `@mastra/core/evals`.

| Parameter | Notes |
|---|---|
| `target` | `Agent` or `Workflow`. Resolve with `mastra.getAgent()` / `mastra.getWorkflow()`. |
| `data` | `RunEvalsDataItem[]`. |
| `scorers` | `ScorerEntry[]`, or `AgentScorerConfig` `{ agent?, trajectory? }`, or `WorkflowScorerConfig` `{ workflow?, steps?, trajectory? }`. Optional when `gates` is set. |
| `gates` | `MastraScorer[]` that must average 1.0. See `mastra-datasets-experiments`. |
| `targetOptions` | Forwarded to `agent.generate()` (for example `maxSteps`, `modelSettings`, `memory`) or `run.start()`. Global per call. |
| `concurrency` | Default `1`. |
| `onItemComplete` | `({ item, targetResult, scorerResults }) => void`. |

`ScorerEntry`: a bare scorer, or `{ scorer, threshold }` where `threshold` is a number (minimum) or `{ min?, max? }` in 0 to 1.

Data item fields: `input`, `inputs` (multi-turn, agents only), `turns` (`[{ input, gates?, scorers? }]`, agents only), `groundTruth`, `expectedTrajectory`, `requestContext`, `tracingContext`, `startOptions` (workflows). `input`, `inputs`, `turns` are mutually exclusive. Empty `inputs` throws `MastraError`.

Result:

| Field | Notes |
|---|---|
| `scores` | Averages keyed by scorer id (nested under `agent`, `trajectory`, `workflow`, `steps` for categorized configs). |
| `summary.totalItems` | Items processed. |
| `summary.notScorable` | Count per scorer id of skipped runs. |
| `verdict` | `'passed' \| 'scored' \| 'failed'`, present when a gate or threshold produced a number. |
| `gateResults`, `thresholdResults`, `turnResults` | Detail arrays. |

---

## Built-in scorers

All from `@mastra/evals/scorers/prebuilt`. LLM scorers take `{ model, options? }`. Range is `0-1` unless noted (`scale` option multiplies it).

| Factory | Measures | Better | Key options |
|---|---|---|---|
| `createAnswerRelevancyScorer` | Does the answer address the query | higher | `options.uncertaintyWeight` (0.3), `options.scale` |
| `createAnswerSimilarityScorer` | Semantic match to `groundTruth` | higher | `requireGroundTruth`, `semanticThreshold`, `exactMatchBonus`, `missingPenalty`, `contradictionPenalty`, `extraInfoPenalty` |
| `createFaithfulnessScorer` | Claims supported by context | higher | `options.context` (else tool results), `options.scale` |
| `createHallucinationScorer` | Contradictions with context | lower | `options.context`, `options.getContext` (dynamic, wins) |
| `createCompletenessScorer` | Input elements covered in output (code) | higher | none |
| `createContentSimilarityScorer` | Character-level similarity (code) | higher | `ignoreCase`, `ignoreWhitespace` (both false once you pass an object) |
| `createTextualDifferenceScorer` | Sequence-match similarity (code) | higher | none |
| `createKeywordCoverageScorer` | Input keywords present in output (code) | higher | none |
| `createToneScorer` | Sentiment consistency (code) | higher | `referenceTone` (else stability across sentences) |
| `createToxicityScorer` | Harmful content | lower | `options.scale` |
| `createBiasScorer` | Biased opinions | lower | `options.scale` |
| `createPromptAlignmentScorerLLM` | Intent, requirements, completeness, format | higher | `options.evaluationMode`: `'user' \| 'system' \| 'both'` (default `'both'`) |
| `createContextPrecisionScorer` | Relevant context ranked early (MAP) | higher | `options.context` or `options.contextExtractor` (one required) |
| `createContextRecallScorer` | Ground-truth claims covered by context | higher | `options.context` or extractor |
| `createContextRelevanceScorerLLM` | Context usefulness and gaps | higher | `options.context`, `options.penalties` |
| `createNoiseSensitivityScorerLLM` | Robustness to distractors (CI only) | higher | `options.baselineResponse`, `noisyQuery`, `noiseType` |
| `createSummarizationScorer` | min(alignment, coverage) of a summary | higher | `options.source`, `sourceExtractor`, `maxQuestions` (10) |
| `createToolCallAccuracyScorerCode` | Expected tool called (binary) | higher | `expectedTool`, `strictMode`, `expectedToolOrder` |
| `createToolCallAccuracyScorerLLM` | Tool choice appropriateness | higher | `model`, `availableTools` (this run's tools) |
| `createTrajectoryAccuracyScorerCode` | Step sequence vs expected | higher | `expectedTrajectory`, `comparisonOptions.ordering` (`'strict' \| 'relaxed'` default \| `'unordered'`) |
| `createTrajectoryAccuracyScorerLLM` | Trajectory necessity and order | higher | `model`, `expectedTrajectory?` |
| `createTrajectoryScorerCode` | Accuracy, efficiency, blacklist, tool failures | higher | `defaults` (`blacklistedTools`, `maxSteps`, ...), `weights` |
| `createRubricScorer` (`@mastra/evals@1.3.0`) | All required criteria met (binary) | higher | `model`, `criteria` (array of `{ description, required? }` or newline string) |
| `createMultiTurnJudgeScorer` (`@mastra/evals@1.9.0`) | Whole conversation meets one criterion (binary) | higher | `model`, `criterion` |

Also `createClassifierScorer` from `@mastra/core/evals` (see `mastra-classifier`).

Trajectory scorers go in `scorers.trajectory` (`AgentScorerConfig` or `WorkflowScorerConfig`). They read `expectedTrajectory` from the constructor or from each data item. Expected steps look like `{ stepType: 'tool_call' | 'workflow_step', name }`.

---

## Quick Checks

From `@mastra/evals/checks`. Zero LLM calls. Fixed ids (for example `check-includes`, `check-called-tool`, `check-no-tool-errors`).

| Check | Score |
|---|---|
| `checks.includes(str, { ignoreCase? = true })` | 1 if output contains str |
| `checks.excludes(str, { ignoreCase? = true })` | 1 if absent |
| `checks.equals(str, { ignoreCase? = true })` | 1 if equal |
| `checks.matches(regex, { exact? = false })` | 1 if matched |
| `checks.similarity(str, { threshold?, ignoreCase? })` | Dice coefficient, or 1/0 with threshold |
| `checks.calledTool(name, { times? = 1 })` | 1 if called at least `times` |
| `checks.didNotCall(name)` | 1 if never called |
| `checks.toolOrder([a, b])` | 1 if subsequence order holds |
| `checks.maxToolCalls(n)` | 1 if total calls at most n |
| `checks.usedNoTools()` | 1 if no calls |
| `checks.noToolErrors()` | 1 if no error results or incomplete calls |

---

## `notScorable(reason?)` and `filterRun(options)`

- `notScorable` (from `@mastra/core/evals`): return it directly from a function step. Remaining steps skip. Live scoring stores no row. `runEvals` excludes the run from averages, gates, thresholds, and counts it in `summary.notScorable`. Experiments record `score: null` plus `notScorable`.
- `filterRun` options: `partTypes` (`'text'`, `'tool-invocation'`, `'reasoning'`, `'data-'`, ...), `toolNames`, `maxRememberedMessages`, `maxOutputMessages`, `dropRequestContext`, `dropExpectedTrajectory`, `dropGroundTruth`. System messages are never filtered.

---

## Scorer utilities (`@mastra/evals/scorers/utils`)

| Helper | Returns |
|---|---|
| `getAssistantMessageFromRunOutput(output)` | Assistant text |
| `getUserMessageFromRunInput(input)` | First user text |
| `extractInputMessages(input)` | User message texts |
| `extractAgentResponseMessages(output)` | Each assistant message text, in order |
| `getReasoningFromRunOutput(output)` | Reasoning text |
| `getSystemMessagesFromRunInput(input)`, `getCombinedSystemPrompt(input)` | System prompts |
| `extractToolCalls(output)` | `{ tools: string[], toolCallInfos }` |
| `createTestMessage({...})`, `createAgentTestRun({...})` | Test fixtures |
| `compareTrajectories`, `createTrajectoryTestRun` | Trajectory helpers |

---

## Live scorer config

On `new Agent({ scorers })` and `createStep({ scorers })`:

```typescript
scorers: {
  <key>: {
    scorer: MastraScorer,
    sampling: { type: 'ratio', rate: 0..1 },
    filter?: { op, left: { path }, right: { literal } }, // plus and, or, not, in, exists, truthy ...
  },
}
```

Per-call scoring: `agent.generate(msg, { scorers, returnScorerData })`. Scores persist to `mastra_scorers` when storage is configured and the scorer is registered.
