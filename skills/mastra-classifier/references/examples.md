# Classifier examples

All examples follow the current docs and use the TypeSafe AI provider (`npm install @ai-sdk/typesafe-ai`, set `TYPESAFE_AI_API_KEY`). Swap in another provider's `decisionModel()` if needed.

## Contents

1. Ticket triage workflow with a registered classifier
2. Safety guardrail with audit records
3. Output quality gate
4. Cost routing with ModelSelectionProcessor
5. Classifier answer as an eval score

---

## 1. Ticket triage workflow with a registered classifier

```typescript
// src/mastra/classifiers/ticket-router.ts
import { Classifier } from '@mastra/core/classifier'
import { typeSafeAi } from '@ai-sdk/typesafe-ai'

export const router = new Classifier({
  id: 'ticket-router',
  model: typeSafeAi.decisionModel('jev-latest'),
  questions: {
    route: {
      type: 'choice',
      criteria: {
        billing: 'Billing, invoices, refunds, and payments',
        support: 'Account access and product help',
        other: 'Anything else',
      },
    },
  },
})
```

```typescript
// src/mastra/workflows/ticket-triage.ts
import { createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'
import { router } from '../classifiers/ticket-router'

export const ticketTriage = createWorkflow({
  id: 'ticket-triage',
  inputSchema: z.object({ message: z.string() }),
  outputSchema: z.any(),
})
  .map({ message: { initData: true, path: 'message' } })
  .classifier(router)
  .branch([
    [async ({ inputData }) => inputData.answers.route.choice === 'billing', billingStep],
    [async ({ inputData }) => inputData.answers.route.choice === 'support', supportStep],
    [
      async ({ inputData }) =>
        inputData.answers.route.choice === 'other' || inputData.answers.route.type === 'refusal',
      fallbackStep,
    ],
  ])
  .commit()
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { router } from './classifiers/ticket-router'
import { ticketTriage } from './workflows/ticket-triage'

export const mastra = new Mastra({
  classifiers: { router },
  workflows: { ticketTriage },
})
```

`billingStep`, `supportStep`, and `fallbackStep` are ordinary steps (see `mastra-workflows`). Conditions are mutually exclusive, so exactly one branch runs.

---

## 2. Safety guardrail with audit records

```typescript
import { Agent } from '@mastra/core/agent'
import { Classifier } from '@mastra/core/classifier'
import { typeSafeAi } from '@ai-sdk/typesafe-ai'
import { ClassifierProcessor } from '@mastra/core/processors'

const safety = new Classifier({
  id: 'safety',
  model: typeSafeAi.decisionModel('jev-latest'),
  questions: {
    unsafe: {
      type: 'boolean',
      criteria: { true: 'The message is unsafe', false: 'The message is safe' },
    },
  },
})

const safetyCheck = new ClassifierProcessor({
  id: 'safety-check',
  classifier: safety,
  lastMessageOnly: true,
  errorStrategy: 'strict', // block if the decision model is down
  onResult: (answers, { abort }) => {
    // A refusal has no probability, so ?? 1 treats it as unsafe.
    if ((answers.unsafe.probability ?? 1) > 0.8) {
      abort('Message rejected by safety policy', { metadata: { policy: 'unsafe' } })
    }
  },
  onDecision: async decision => {
    await auditLog.insert({
      threadId: decision.ids.threadId,
      messageId: decision.ids.messageId,
      outcome: decision.outcome,
      answers: decision.result ? decision.result.answers : null,
      error: decision.result ? null : String(decision.error),
      durationMs: decision.durationMs,
    })
  },
})

export const chatAgent = new Agent({
  id: 'chat-agent',
  name: 'chat-agent',
  instructions: 'You are a helpful assistant',
  model: 'openai/gpt-6.1-sol',
  inputProcessors: [safetyCheck],
})
```

Callers detect blocks through `result.tripwire` or `tripwire` chunks (see `mastra-processors-guardrails`). `auditLog` stands in for your store.

---

## 3. Output quality gate

```typescript
import { Agent } from '@mastra/core/agent'
import { Classifier } from '@mastra/core/classifier'
import { typeSafeAi } from '@ai-sdk/typesafe-ai'
import { ClassifierProcessor } from '@mastra/core/processors'

const quality = new Classifier({
  id: 'quality',
  model: typeSafeAi.decisionModel('jev-latest'),
  questions: {
    quality: {
      type: 'score',
      instructions: 'Rate how well the response answers the user',
      criteria: ['Off-topic', 'Partial', 'Complete'],
    },
  },
})

export const gatedAgent = new Agent({
  id: 'quality-gated-agent',
  name: 'quality-gated-agent',
  instructions: 'You are a helpful assistant',
  model: 'openai/gpt-6.1-sol',
  outputProcessors: [
    new ClassifierProcessor({
      classifier: quality,
      onResult: (answers, { filter }) => {
        if ((answers.quality.score ?? 0) < 1) filter()
      },
    }),
  ],
})
```

---

## 4. Cost routing with `ModelSelectionProcessor`

```typescript
import { Agent } from '@mastra/core/agent'
import { ModelSelectionProcessor } from '@mastra/core/processors'
import { typeSafeAi } from '@ai-sdk/typesafe-ai'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'support-agent',
  instructions: 'Answer the user concisely.',
  model: 'openai/gpt-6.1-sol', // capable default
  inputProcessors: [
    new ModelSelectionProcessor({
      model: typeSafeAi.decisionModel('jev-latest'),
      choices: [
        {
          model: 'openai/gpt-6-luna',
          criteria: 'Answerable in one or two sentences from general knowledge, with no reasoning steps',
        },
        {
          model: 'openai/gpt-6.1-sol',
          criteria: 'Requires multi-step reasoning, planning, weighing trade-offs, or careful judgment',
        },
      ],
      onDecision: decision => console.log('model routing', decision),
    }),
  ],
})
```

Never downgrade sensitive requests by combining questions in `select`:

```typescript
new ModelSelectionProcessor({
  classifier: triage, // questions: complexity (choice), sensitive (boolean)
  select: ({ complexity, sensitive }) => {
    if ((sensitive.probability ?? 1) >= 0.3) return undefined
    return complexity.choice === 'trivial' ? 'openai/gpt-6-luna' : undefined
  },
})
```

Compare cost per completed task with and without routing before enabling it.

---

## 5. Classifier answer as an eval score

```typescript
import { Classifier } from '@mastra/core/classifier'
import { typeSafeAi } from '@ai-sdk/typesafe-ai'
import { createClassifierScorer } from '@mastra/core/evals'
import {
  getAssistantMessageFromRunOutput,
  getUserMessageFromRunInput,
} from '@mastra/evals/scorers/utils'

const responseJudge = new Classifier({
  id: 'response-judge',
  model: typeSafeAi.decisionModel('jev-latest'),
  questions: {
    quality: {
      type: 'score',
      instructions: 'How well does the response answer the request?',
      criteria: ['Incorrect or irrelevant', 'Partially correct', 'Correct and complete'],
    },
  },
})

export const qualityScorer = createClassifierScorer({
  id: 'response-quality',
  description: 'Scores response quality with the configured classifier',
  classifier: responseJudge,
  question: 'quality',
  type: 'agent',
  state: ({ run }) => ({
    input: getUserMessageFromRunInput(run.input) ?? '',
    output: getAssistantMessageFromRunOutput(run.output) ?? '',
  }),
})
```

`Partially correct` scores 0.5. Attach the scorer to an agent or experiment (see `mastra-evals`).
