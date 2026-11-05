---
name: mastra-classifier
description: "Make typed runtime decisions with the Mastra Classifier: send JSON state and fixed choice, score, or boolean questions to a decision model and get one typed answer per question, then route workflows, gate tool approval, guard agent input and output with ClassifierProcessor, route cheap versus capable models with ModelSelectionProcessor, or score outputs with createClassifierScorer. Use this skill whenever the user wants to classify, route, triage, label, gate on a threshold, detect unsafe content, or pick a branch from a small known set of outcomes without parsing model text. Triggers on Classifier, @mastra/core/classifier, decide(), decision model, decisionModel, typeSafeAi, @ai-sdk/typesafe-ai, choice question, score question, boolean question, probability, refusal, ClassifierProcessor, ModelSelectionProcessor, createClassifierScorer, workflow .classifier(), MastraDecisionModel, getClassifierById. Also triggers for intent detection, ticket triage, and topic scoping."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Typed choice, score, and boolean decisions with decision models, plus routing, guardrails, and model selection"
  display_order: 9
  docs: https://mastra.ai/docs/classifier
---

# Mastra Classifier

Ask a decision model fixed, typed questions about JSON state and act on the typed answers in code.

---

## When to use

- Routing a request to a team, handler, or workflow branch
- Gating an action on a threshold (unsafe content, needs human review)
- Scoring one dimension of an output (tone, quality)
- Scoping an agent to allowed topics
- Downgrading easy requests to a cheaper model
- Turning a classifier answer into an eval score

The decision has a small, known set of outcomes. The model supplies the judgment; your code supplies the policy.

## When NOT to use

- Extracting a data object with many interdependent fields (use `mastra-structured-output`)
- LLM-based moderation, PII, or injection detection with built-in prompts (use `mastra-processors-guardrails`)
- Measuring output quality over time with datasets (use `mastra-evals` and `mastra-datasets-experiments`)
- Workflow branching mechanics beyond the classifier step (use `mastra-workflows`)
- Picking a language model or provider string (use `mastra-models`)
- The approval flow that a classifier gates (use `mastra-agent-approval-hitl`)

---

## Required inputs

- The decision: what outcome set, and what your code does with each outcome
- Question types: `choice` (pick a key), `score` (position on an ordered list), `boolean` (probability of true)
- The state fields the decision needs, and which fields are sensitive
- A decision model provider and its API key (for example `TYPESAFE_AI_API_KEY`)
- Thresholds and the policy for a refused question

---

## The framework: state plus questions in, typed answers out

```typescript
import { Classifier } from '@mastra/core/classifier'
import { typeSafeAi } from '@ai-sdk/typesafe-ai'

const classifier = new Classifier({
  id: 'request-classifier',
  model: typeSafeAi.decisionModel('jev-latest'),
  questions: {
    route: {
      type: 'choice',
      instructions: 'Choose the team that should handle this request.',
      criteria: {
        billing: 'Questions about invoices, charges, or refunds',
        support: 'Questions about using or troubleshooting the product',
      },
    },
    urgent: {
      type: 'boolean',
      instructions: 'Does this request require an immediate response?',
    },
  },
})

const result = await classifier.decide({
  state: {
    subject: 'Duplicate charge',
    message: 'I was charged twice for the same subscription.',
  },
})

result.answers.route.choice // 'billing' | 'support' | undefined
result.answers.urgent.probability // P(true), 0 to 1, or undefined
```

Added in `@mastra/core@1.69.0`. The model is a decision model from a provider's `decisionModel()` factory. It is not a language model and not a `'provider/model'` string. Install `@ai-sdk/typesafe-ai` and set `TYPESAFE_AI_API_KEY` for this example. OpenAI, Anthropic, and Google AI SDK providers also expose `decisionModel()`.

### Question types

| Type | `criteria` | Answer field | Notes |
|---|---|---|---|
| `choice` | Record of key to description | `choice`, optional `probabilities` per key | Choice keys are inferred as a union type |
| `score` | Ordered array, at least 2 levels | `score` (index range, may be fractional), optional `probabilities` | 3 levels give scores 0 to 2 |
| `boolean` | Optional `{ true?, false? }` | `probability` of true | Not "confidence in the likelier outcome" |

Every answer can instead be `{ type: 'refusal' }` with no `choice`, `score`, or `probability`. Check `type` first.

One `decide()` call sends the state once with all questions, so extra questions add no round trip.

### Where classifiers run

| Place | API |
|---|---|
| Your code | `classifier.decide({ state })` |
| Workflow routing | `.classifier(classifier)` then `.branch()` |
| Agent guardrail | `new ClassifierProcessor({ classifier, onResult })` |
| Model routing | `new ModelSelectionProcessor({ model, choices })` |
| Tool approval gate | `requireToolApproval: async ({ toolName, args }) => ...` |
| Evals | `createClassifierScorer({ classifier, question, ... })` |

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Classifier` types. Otherwise fetch `https://mastra.ai/docs/classifier.md` and `https://mastra.ai/reference/classifier/classifier.md`. Trust these over memory.
2. **Install a decision model provider** and set its key. Confirm the model supports every question type you use.
3. **Write one judgment per question.** Split multi-factor questions and combine the answers in code.
4. **Make criteria exclusive** and add an `other` key or level when the set is open.
5. **Put facts in `state`, not `instructions`.** Send only what the decision needs. Redact sensitive fields.
6. **Keep `questions` as an object literal** in the constructor so answer keys and choice unions are inferred. Processors, workflow steps, and scorers require constructor questions.
7. **Handle refusals and thresholds** explicitly in code.
8. **Register shared classifiers** on `new Mastra({ classifiers })` and reference them by ID where useful.
9. **Wire it in:** workflow `.classifier()`, `ClassifierProcessor`, `ModelSelectionProcessor`, or a scorer.
10. **Test each question** by changing one state field and confirming one answer moves. Review `CLASSIFIER_EVALUATION` spans in Studio.

---

## Deep dive: guardrails and routing

`ClassifierProcessor` runs the classifier over message text. `onResult` owns the policy: `abort(reason)` stops with a tripwire, `filter()` drops the message or chunk, doing nothing lets it pass.

```typescript
import { Agent } from '@mastra/core/agent'
import { ClassifierProcessor } from '@mastra/core/processors'

export const agent = new Agent({
  id: 'support-agent',
  name: 'support-agent',
  instructions: 'You help customers with billing and account questions.',
  model: 'openai/gpt-6.1-sol',
  inputProcessors: [
    new ClassifierProcessor({
      classifier: topic, // a Classifier with a 'topic' choice question
      lastMessageOnly: true,
      onResult: (answers, { abort }) => {
        if (answers.topic.type === 'refusal' || answers.topic.choice === 'other') {
          abort('This assistant only handles billing and account questions')
        }
      },
    }),
  ],
})
```

Workflow routing:

```typescript
createWorkflow({ id: 'ticket-triage', inputSchema: z.object({ message: z.string() }), outputSchema: z.any() })
  .map({ message: { initData: true, path: 'message' } })
  .classifier(router)
  .branch([
    [async ({ inputData }) => inputData.answers.route.choice === 'billing', billingStep],
    [async ({ inputData }) => inputData.answers.route.choice === 'support', supportStep],
    [async ({ inputData }) => inputData.answers.route.choice === 'other', fallbackStep],
  ])
  .commit()
```

Every `.branch()` condition that is true runs. Keep conditions mutually exclusive and do not end with `async () => true` unless the fallback should also run.

---

## Failure patterns

- **Passing `'openai/gpt-6.1-sol'` as `model`.** The classifier needs a decision model, for example `typeSafeAi.decisionModel('jev-latest')`.
- **Reading `probability` on a refusal.** It is `undefined`. Check `answer.type === 'refusal'` and apply a fallback (often fail closed with `?? 1`).
- **Treating boolean `probability` as confidence.** It is P(true). `0.1` means likely false.
- **Multi-factor questions.** "Is this urgent and from a VIP?" moves on either factor. Ask two questions and combine in code.
- **Overlapping criteria** ("good fit" vs "maybe a fit"). Probability leaks between them. Make them exclusive.
- **Closed list with no escape.** Every input is forced into a listed team. Add `other`.
- **Questions in `decide()` when the constructor has them.** They are mutually exclusive. Constructor questions are required for processors, workflow steps, and scorers.
- **Lost types with a string reference.** Pass the question type: `.classifier<typeof router.questions>('router')` or `new ClassifierProcessor<SafetyQuestions>({ classifier: 'safety', ... })`.
- **Unconditional fallback branch** after `.classifier()`. It runs alongside the match. Add an explicit `other` or `refusal` condition.
- **Expecting partial answers on failure.** `decide()` rejects on provider failure or invalid output. Only retryable `APICallError`s retry (`maxRetries` default 2).
- **Two `ClassifierProcessor`s with the same `id`.** They share per-run state. Give each a unique `id`.
- **Slow `onDecision` in streams.** It runs per chunk and delays output. Queue the write.
- **Sensitive data in `state`.** It goes to the provider and into trace spans. Redact, or set `hideInput`/`hideOutput` in tracing options.
- **Calling `evaluate()`.** Deprecated alias. Use `decide()`.

---

## Output format

A finished classifier delivery contains:

- The classifier in `src/mastra/classifiers/<id>.ts` with constructor questions as an object literal
- Registration in `new Mastra({ classifiers })` when shared or referenced by ID
- The decision provider package installed and its env var in `.env.example`
- Code that handles every choice, the threshold, and refusals
- Wiring into the workflow, processor, model selection, approval gate, or scorer
- Tests that change one state field per question and check the answer moves

---

## Reference files

- [`references/api.md`](references/api.md) - Constructor, question shapes, `decide()` options, results, validation, `MastraDecisionModel`, registration, processor and workflow options.
- [`references/examples.md`](references/examples.md) - Ticket triage workflow, safety guardrail with audit, output quality gate, model routing, classifier scorer.
- [`references/checklist.md`](references/checklist.md) - Classifier design and production checklist.

**Live docs**

- https://mastra.ai/docs/classifier
- https://mastra.ai/reference/classifier/classifier
- https://mastra.ai/reference/processors/classifier-processor
- https://mastra.ai/reference/processors/model-selection-processor
- https://mastra.ai/reference/workflows/workflow-methods/classifier
- https://mastra.ai/reference/evals/create-classifier-scorer
