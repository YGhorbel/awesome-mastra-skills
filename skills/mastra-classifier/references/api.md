# Classifier API reference

Distilled from `https://mastra.ai/reference/classifier/classifier.md`, `https://mastra.ai/reference/processors/classifier-processor.md`, `https://mastra.ai/reference/processors/model-selection-processor.md`, `https://mastra.ai/reference/workflows/workflow-methods/classifier.md`, and `https://mastra.ai/reference/evals/create-classifier-scorer.md`. Verify against the installed version.

## Contents

- Classifier constructor
- Question shapes
- Answer shapes
- decide()
- Result
- Validation and errors
- Decision models and MastraDecisionModel
- Registration
- Workflow step
- ClassifierProcessor
- ModelSelectionProcessor
- createClassifierScorer
- Observability

---

## Classifier constructor

Import: `import { Classifier } from '@mastra/core/classifier'`. Added in `@mastra/core@1.69.0`.

| Option | Type | Notes |
|---|---|---|
| `id` | `string` | Non-empty. Used in tracing and errors. |
| `model` | `DecisionModelV4 \| EvaluationModelV4 \| MastraDecisionModel` | Decision model. Not a language model or `'provider/model'` string. |
| `questions` | `ClassifierQuestions` | Non-empty record. Omit to pass questions per `decide()` call. |

Constructor `questions` and per-call `questions` are mutually exclusive (enforced at compile time). Processors, workflow steps, and scorers need constructor questions.

---

## Question shapes

Every question has `type` and optional `instructions` (JSON-compatible). Without `instructions`, the question name is used.

```typescript
// choice: pick one key
{ type: 'choice', instructions?: unknown, criteria: { [key: string]: unknown } }

// score: ordered list, at least 2 levels, index range 0..N-1
{ type: 'score', instructions?: unknown, criteria: unknown[] }

// boolean: P(true)
{ type: 'boolean', instructions?: unknown, criteria?: { true?: unknown; false?: unknown } }
```

Use `as const` or an inline object literal so keys and choice unions are inferred.

---

## Answer shapes

```typescript
{ type: 'choice', choice: 'negative', probabilities?: { positive: 0.05, neutral: 0.15, negative: 0.8 } }
{ type: 'score', score: 1.7, probabilities?: { '0': 0.05, '1': 0.2, '2': 0.75 } }
{ type: 'boolean', probability: 0.92 }
{ type: 'refusal' } // no choice, score, or probability
```

Choice probabilities cover every key and sum to 1 within the provider's rounding precision.

---

## `decide(options)`

| Option | Notes |
|---|---|
| `state` | JSON-compatible state sent with every question. |
| `questions` | Required only when the constructor omitted them. |
| `abortSignal` | Cancels the provider request and retry waits. |
| `providerOptions` | Forwarded unchanged to the decision model. |
| `maxRetries` | Retries after retryable provider API errors. Default `2`. |

`evaluate(options)` is a deprecated alias.

---

## Result

| Field | Notes |
|---|---|
| `answers` | One typed answer per question, keyed by question name. |
| `usage` | `{ inputTokens?, outputTokens?, totalTokens }`. |
| `warnings` | Provider warnings. |
| `rounding` | `{ probabilityDecimals?, scoreDecimals? }`. |
| `providerMetadata` | Provider-specific metadata. |
| `response` | `{ id?, timestamp, modelId, headers?, body? }`. |

---

## Validation and errors

Inputs checked: non-empty `id`, JSON-compatible state, instructions, and criteria, non-empty question record and choice criteria, at least two score levels, every question type supported by the model, valid `maxRetries`.

Provider output checked: exactly one answer per question, matching type or refusal, valid choices, in-range scores and probabilities, complete distributions, valid token counts, warnings, and timestamps.

Only retryable AI SDK `APICallError` failures retry. Other errors reject immediately. After the last retry, the last provider error is rethrown. `decide()` never returns partial answers.

---

## Decision models and `MastraDecisionModel`

Providers expose `decisionModel()` (formerly `evaluationModel()`, now a deprecated alias). Mastra calls `doDecide()` and falls back to `doEvaluate()`.

```typescript
import { createTypeSafeAi } from '@ai-sdk/typesafe-ai'

const model = createTypeSafeAi({ apiKey: process.env.TYPESAFE_AI_API_KEY }).decisionModel('jev-latest')
```

Normalize provider output before validation by subclassing:

```typescript
import { Classifier, MastraDecisionModel, type DecisionModelResult } from '@mastra/core/classifier'

class NormalizedDecisionModel extends MastraDecisionModel {
  protected override transformResult(result: DecisionModelResult): DecisionModelResult {
    return { ...result, answers: normalizeAnswers(result.answers) }
  }
}
```

`MastraEvaluationModel` and `EvaluationModelResult` are deprecated aliases.

---

## Registration

```typescript
export const mastra = new Mastra({ classifiers: { safety } })

mastra.getClassifier('safety') // by key
mastra.getClassifierById('safety') // by id
mastra.listClassifiers()
```

A registered classifier evaluated outside a trace starts a root `CLASSIFIER_EVALUATION` span.

---

## Workflow step

`createStep(classifier)` or `workflow.classifier(classifierOrId, options?, stepOptions?)`.

- Input: the complete previous step output. Use `.map()` before it to shape the state.
- Output: `{ answers, usage }`. No warnings, raw responses, headers, or provider metadata.
- `options`: `maxRetries` (model call), `providerOptions`, `retries` (workflow step), metadata, `id`.
- `stepOptions.id` overrides `options.id`. Default step id is the classifier id.
- Errors fail the step. There is no fail-open.
- String IDs resolve at run time. Type them: `.classifier<typeof router.questions>('router')`.

---

## `ClassifierProcessor`

Import from `@mastra/core/processors`. Hybrid: input, output result, and stream.

| Option | Notes |
|---|---|
| `classifier` | `Classifier` with constructor questions, or a registered key or id (resolved lazily). |
| `onResult(answers, context)` | Policy. `context` has `abort(reason, { metadata }?)`, `filter()`, `phase`, and the full `ClassifierResult`. |
| `onDecision(decision)` | Audit hook after each call, including failures. Awaited before content passes. |
| `id` | Unique per processor. Same ids share per-run state. |
| `errorStrategy` | `'warn'` (fail-open) or `'strict'` (abort with metadata `{ processorId, classifierId, code: 'CLASSIFIER_FAILED' }`). Configuration errors always throw. |
| `lastMessageOnly` | Classify only the last message in input and output phases. |
| `chunkWindow` | Trailing stream chunks classified together. `0` means the current chunk only. Each text chunk triggers a call. |
| `maxInputLength` | Truncate text sent to the classifier. |
| `providerOptions` | Forwarded to the decision model. |

| Phase | No action | `abort()` | `filter()` |
|---|---|---|---|
| Input | Message passes | Abort before the LLM | Message removed from context |
| Output result | Message passes | Abort the response | Message removed from response |
| Stream | Chunk emitted | Abort the stream | Chunk not emitted |

Messages with no text skip the classifier. Abort reasons are always your string, never provider text.

`ClassifierProcessorDecision`: `processorId`, `classifierId`, `phase`, `outcome` (`'allowed' | 'filtered' | 'aborted'`), `state`, `result?`, `error?`, `tripwire?`, `durationMs`, `ids` (`runId`, `threadId`, `resourceId`, `messageId`, `traceId`, `spanId`), `requestContext?`.

---

## `ModelSelectionProcessor`

Classifies the latest user message once per request (in `processInput`) and overrides the model.

| Option | Notes |
|---|---|
| `choices` | Two or more `{ model, criteria, name? }`. Builds the classifier for you. Excludes `classifier`. |
| `model` | Decision model for the routing decision. Required with `choices`. Not a `'provider/model'` string. |
| `instructions` | Objective. Defaults to the least capable model that can answer correctly. |
| `classifier` + `select` | Use your own classifier. `select(answers, { result })` returns a model or `undefined` to abstain. |
| `minProbability` | With `choices`. Abstains when below, or when no distribution is reported. No default. |
| `scope` | `'run'` (default, every step) or `'first-step'`. |
| `onDecision` | `{ model?, choice?, probability?, abstained? }`. `abstained`: `'below-threshold' \| 'no-model-for-choice' \| 'no-text' \| 'error' \| 'refused'`. |
| `id` | Default `'model-selection'`. |
| `providerOptions` | Forwarded to `decide()`. |

Fails open: classifier errors keep the agent's configured model. Keep the capable model as default and only downgrade. Measure cost per completed task first: prompt caches are not shared between models.

---

## `createClassifierScorer`

Import from `@mastra/core/evals`.

| Option | Notes |
|---|---|
| `id`, `description` | Scorer metadata. |
| `classifier` | Constructor-configured classifier or registered id. |
| `question` | The question projected to a 0 to 1 score. All questions are still evaluated each run. |
| `scores` | Required exhaustive `{ choiceKey: 0..1 }` map for choice questions. Rejected for score and boolean. |
| `type` | `'agent' \| 'trajectory' \| { input, output }`. |
| `state` | `(context) => ClassifierState`. Required for agent runs. |
| `maxRetries`, `providerOptions`, `prepareRun` | Optional. |

Score questions map level `k` of `N` to `k / (N - 1)`. See `mastra-evals`.

---

## Observability

`decide()` inside an active span creates a `CLASSIFIER_EVALUATION` child span with state, questions, answers, model ids, attempts, duration, and token usage (which also feeds cost metrics). Hide state and answers with `hideInput` and `hideOutput` in the run's `tracingOptions`. Filter by the Classifier entity type in Studio.
