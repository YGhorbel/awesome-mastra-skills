# Datasets and experiments examples

All examples follow the current docs. Model IDs are the ones the docs use. Verify against the installed version before copying.

## Contents

1. Seed a golden dataset and run a baseline
2. Compare a model swap with agentModel
3. Deterministic experiment with tool mocks
4. CI regression script with a verdict
5. Vitest suite with reporter and matchers

---

## 1. Seed a golden dataset and run a baseline

```typescript
// scripts/seed-dataset.ts
import { z } from 'zod'
import { mastra } from '../src/mastra'

const refundCases = [
  {
    input: "I paid my deposit ten days ago and haven't accepted an assignment. Can I cancel for a refund?",
    groundTruth: {
      must: ['Confirm a full deposit refund to the original payment method.'],
      mustNot: ['Claim that all deposits are nonrefundable.'],
    },
  },
  {
    input: 'I paid my deposit ten days ago. Can I cancel for a refund?',
    groundTruth: {
      must: ['Ask whether the customer has accepted a mission assignment.'],
      mustNot: ['Make an unconditional eligibility decision without knowing assignment status.'],
    },
  },
]

const dataset = await mastra.datasets.create({
  id: 'aster-refunds',
  name: 'Aster refunds',
  groundTruthSchema: z.object({ must: z.array(z.string()), mustNot: z.array(z.string()) }),
})
await dataset.addItems({ items: refundCases })
```

```typescript
// scripts/run-baseline.ts
import { mastra } from '../src/mastra'

const dataset = await mastra.datasets.get({ id: 'aster-refunds' })

const summary = await dataset.startExperiment({
  name: 'baseline',
  targetType: 'agent',
  targetId: 'refund-policy-agent',
  scorers: ['refund-correctness'], // registered scorer id (see mastra-evals)
})

console.log(summary.status, `${summary.succeededCount}/${summary.totalItems} executed`)
for (const item of summary.results) {
  for (const s of item.scores) console.log(item.itemId, s.scorerName, s.score, s.reason)
}
```

The guide passes `id` to `create()` so later scripts can `get()` it. The reference page does not list `id`, so confirm it in your installed types.

---

## 2. Compare a model swap with agentModel

```typescript
import { mastra } from '../src/mastra'

const dataset = await mastra.datasets.get({ id: 'aster-refunds' })
const { version } = await dataset.getDetails()

const baseline = await dataset.startExperiment({
  name: 'baseline',
  targetType: 'agent',
  targetId: 'refund-policy-agent',
  scorers: ['refund-correctness'],
  version,
})

const candidate = await dataset.startExperiment({
  name: 'haiku',
  targetType: 'agent',
  targetId: 'refund-policy-agent',
  agentModel: 'anthropic/claude-haiku-5-5',
  scorers: ['refund-correctness'],
  version,
})

const comparison = await mastra.datasets.compareExperiments({
  experimentIds: [baseline.experimentId, candidate.experimentId],
  baselineId: baseline.experimentId,
})

for (const item of comparison.items) {
  console.log(item.itemId, item.results)
}
```

Pinning `version` keeps both runs on the same snapshot. Compare outputs, latency, and cost too, not only scores.

---

## 3. Deterministic experiment with tool mocks

```typescript
import { mastra } from '../src/mastra'

const dataset = await mastra.datasets.create({ name: 'weather-mocked' })

await dataset.addItem({
  input: 'What is the weather in Seattle?',
  groundTruth: 'rainy',
  toolMocks: [
    {
      toolName: 'getWeather',
      args: { city: 'Seattle' },
      output: { temperature: 60, conditions: 'rainy' },
    },
  ],
})

const summary = await dataset.startExperiment({
  name: 'mocked-run',
  targetType: 'agent',
  targetId: 'weather-agent',
  scorers: ['accuracy'],
  unmockedToolPolicy: 'deny', // any undeclared tool call fails the item
  maxConcurrency: 2,
  itemTimeout: 30_000,
})

for (const item of summary.results) {
  const report = item.toolMockReport
  if (!report) continue
  console.log(report.served, report.unconsumed, report.liveCalls, report.failure)
}
```

---

## 4. CI regression script with a verdict

```typescript
// scripts/eval-regression.ts
import { runEvals } from '@mastra/core/evals'
import { checks } from '@mastra/evals/checks'
import { mastra } from '../src/mastra'

const dataset = await mastra.datasets.get({ id: 'aster-refunds' })
const { items } = await dataset.listItems({ page: 0, perPage: 100 })
const data = items.map(item => ({ input: item.input, groundTruth: item.groundTruth }))

const scorer = mastra.getScorer('refundCorrectnessScorer')

try {
  const result = await runEvals({
    target: mastra.getAgent('refundPolicyAgent'),
    data,
    gates: [checks.noToolErrors()],
    scorers: [{ scorer, threshold: 1 }],
    onItemComplete: ({ item, targetResult, scorerResults }) => {
      const judgment = scorerResults[scorer.id]
      console.log(`${judgment?.score === 1 ? 'PASS' : 'FAIL'}: ${item.input}`)
      if (judgment?.score !== 1) {
        console.log('Answer:', targetResult.text)
        console.log('Judge:', judgment?.reason)
      }
    },
  })

  console.log('Verdict:', result.verdict)
  if (result.verdict !== 'passed') process.exitCode = 1
} catch (error) {
  console.error('Regression check could not complete:', error)
  process.exitCode = 1
}
```

Run it as a required CI job before deploy, with the agent and judge provider keys as secrets. `scored` and `failed` both exit 1.

---

## 5. Vitest suite with reporter and matchers

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import { MastraEvalsReporter } from '@mastra/evals/vitest'

export default defineConfig({
  test: {
    reporters: ['default', new MastraEvalsReporter()],
    setupFiles: ['@mastra/evals/vitest/setup'],
    testTimeout: 60_000,
  },
})
```

```typescript
// tests/weather.eval.test.ts
import { test, expect } from 'vitest'
import { expectEval, expectEvals } from '@mastra/evals/vitest'
import { runEvals } from '@mastra/core/evals'
import { checks } from '@mastra/evals/checks'
import { mastra } from '../src/mastra'

test('weather agent calls the tool and answers relevantly', async () => {
  await expectEvals({
    target: mastra.getAgent('weatherAgent'),
    data: [{ input: "What's the weather in London?" }],
    gates: [checks.calledTool('weatherTool'), checks.noToolErrors(), checks.includes('London')],
    scorers: [{ scorer: mastra.getScorer('answerRelevancyScorer'), threshold: 0.7 }],
  }).toPass(0.8)
})

test.for([
  { input: "What's the weather in Tokyo?", groundTruth: 'Tokyo' },
  { input: "What's the weather in Sydney?", groundTruth: 'Sydney' },
])('weather agent: $input', async item => {
  await expectEval({
    target: mastra.getAgent('weatherAgent'),
    data: item,
    gates: [checks.calledTool('weatherTool'), checks.includes(item.groundTruth)],
  }).toPass()
})

test('weather agent quality', async () => {
  const result = await runEvals({
    target: mastra.getAgent('weatherAgent'),
    data: [{ input: "What's the weather in London?" }],
    scorers: [mastra.getScorer('answerRelevancyScorer')],
    gates: [checks.noToolErrors()],
  })

  expect(result).toHaveVerdict('passed')
  expect(result).toPassGates()
  expect(result).toHaveScoreAbove('answer-relevancy-scorer', 0.7)
})
```

On provider rate limits, lower `concurrency` or set `fileParallelism: false`.
