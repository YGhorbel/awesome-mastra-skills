# Processor examples

All examples follow the current docs. Verify against the installed version.

## Contents

1. Layered guardrails with tripwire handling and alerts
2. Custom input processor that rewrites text parts
3. Quality check that asks the model to retry
4. Redact a tool result before the model sees it
5. Per-step model switching and a final-step reminder
6. Cost cap and response cache

---

## 1. Layered guardrails with tripwire handling and alerts

```typescript
// src/mastra/agents/support-agent.ts
import { Agent } from '@mastra/core/agent'
import {
  UnicodeNormalizer,
  RegexFilterProcessor,
  PromptInjectionDetector,
  PIIDetector,
  ModerationProcessor,
  BatchPartsProcessor,
  SystemPromptScrubber,
} from '@mastra/core/processors'

const GUARDRAIL_MODEL = 'openai/gpt-6-luna'

const injection = new PromptInjectionDetector({
  model: GUARDRAIL_MODEL,
  threshold: 0.8,
  strategy: 'block',
  errorStrategy: 'strict', // fail closed if the guardrail model is down
  lastMessageOnly: true,
})

injection.onViolation = ({ processorId, message, detail }) => {
  console.warn('guardrail violation', { processorId, message, detail })
}

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  instructions: 'You help customers with account questions.',
  model: 'openai/gpt-6.1-sol',
  inputProcessors: [
    new UnicodeNormalizer({ stripControlChars: true, collapseWhitespace: true }),
    new RegexFilterProcessor({ presets: ['secrets'], strategy: 'block', phase: 'input' }),
    injection,
    new PIIDetector({ model: GUARDRAIL_MODEL, strategy: 'redact', redactionMethod: 'mask', lastMessageOnly: true }),
  ],
  outputProcessors: [
    new BatchPartsProcessor({ batchSize: 10 }),
    new ModerationProcessor({ model: GUARDRAIL_MODEL, strategy: 'block' }),
    new SystemPromptScrubber({ model: GUARDRAIL_MODEL, strategy: 'redact', placeholderText: '[REDACTED]' }),
  ],
})
```

```typescript
// call site
const stream = await supportAgent.stream(userMessage)

for await (const chunk of stream.fullStream) {
  if (chunk.type === 'tripwire') {
    console.log('Blocked by', chunk.payload.processorId, '-', chunk.payload.reason)
    break
  }
  if (chunk.type === 'text-delta') process.stdout.write(chunk.payload.text)
}
```

---

## 2. Custom input processor that rewrites text parts

```typescript
// src/mastra/processors/lowercase-input.ts
import type { Processor, ProcessInputArgs } from '@mastra/core/processors'
import type { MastraDBMessage } from '@mastra/core/memory'

export class LowercaseInput implements Processor {
  id = 'lowercase-input'

  async processInput({ messages }: ProcessInputArgs): Promise<MastraDBMessage[]> {
    return messages.map(msg => ({
      ...msg,
      content: {
        ...msg.content,
        parts: msg.content.parts?.map(part =>
          part.type === 'text' ? { ...part, text: part.text.toLowerCase() } : part,
        ),
      },
    }))
  }
}
```

Text is in `content.parts`. Rewrite only `text` parts and keep the rest.

---

## 3. Quality check that asks the model to retry

```typescript
import type { Processor } from '@mastra/core/processors'
import { Agent } from '@mastra/core/agent'

export class QualityChecker implements Processor {
  id = 'quality-checker'

  async processOutputStep({ messages, text, abort, retryCount }) {
    const qualityScore = await evaluateQuality(text) // your scoring function

    if (qualityScore < 0.7 && retryCount < 3) {
      abort('Response quality score too low. Please provide a more detailed answer.', {
        retry: true,
        metadata: { score: qualityScore },
      })
    }

    return messages
  }
}

export const qualityAgent = new Agent({
  id: 'quality-agent',
  name: 'Quality Agent',
  instructions: 'Answer thoroughly.',
  model: 'openai/gpt-6.1-sol',
  outputProcessors: [new QualityChecker()],
  maxProcessorRetries: 3, // required, or the retry never runs
})
```

---

## 4. Redact a tool result before the model sees it

```typescript
import type { Processor } from '@mastra/core/processors'

export class RedactToolResult implements Processor {
  id = 'redact-tool-result'

  async processToolResult({ toolName, toolCallId, args, result, messageList }) {
    if (toolName !== 'lookup-customer') return

    const redacted = {
      ...(result as Record<string, unknown>),
      ssn: '[REDACTED]',
      email: '[REDACTED]',
    }

    messageList.updateToolInvocation({
      type: 'tool-invocation',
      toolInvocation: { state: 'result', toolCallId, toolName, args, result: redacted },
    })
  }
}
```

Use this when the model must not see the field. If only the UI must not see it, use the tool's `transform` instead (see `mastra-tools`).

---

## 5. Per-step model switching and a final-step reminder

```typescript
import type { Processor, ProcessInputStepArgs, ProcessInputStepResult } from '@mastra/core/processors'

export class DynamicModelProcessor implements Processor {
  id = 'dynamic-model'

  async processInputStep({ stepNumber }: ProcessInputStepArgs): Promise<ProcessInputStepResult> {
    if (stepNumber === 0) return { model: 'openai/gpt-6-luna' }
    if (stepNumber > 5) return { toolChoice: 'none' }
    return {}
  }
}

export class EnsureFinalResponseProcessor implements Processor {
  readonly id = 'ensure-final-response'
  private maxSteps: number

  constructor(maxSteps: number) {
    this.maxSteps = maxSteps
  }

  async processInputStep({ stepNumber, sendSignal }: ProcessInputStepArgs) {
    if (stepNumber !== this.maxSteps - 1) return
    await sendSignal?.({
      type: 'reactive',
      contents:
        `This is your final step (step ${stepNumber + 1} of ${this.maxSteps}). ` +
        `Do not call any more tools. Give the user a complete final answer now.`,
      attributes: { reason: 'max-steps-reached', step: stepNumber + 1 },
    })
  }
}
```

Pass the same `maxSteps` to `generate()`/`stream()`. Tell the agent in its instructions that `<system-reminder>` tags come from the system. For one-off logic, `prepareStep` on the call does the same as `processInputStep`.

---

## 6. Cost cap and response cache

```typescript
import { Agent } from '@mastra/core/agent'
import { InMemoryServerCache } from '@mastra/core/cache'
import { ResponseCache, TokenCostControl } from '@mastra/core/processors'

const costCap = new TokenCostControl({
  maxCost: 5.0,
  scope: 'thread',
  window: '24h',
  warnAtPercent: 80,
})

costCap.onViolation = ({ processorId, message }) => {
  console.warn(`[${processorId}] ${message}`)
}

export const searchAgent = new Agent({
  id: 'search-agent',
  name: 'Search Agent',
  instructions: 'You answer questions concisely.',
  model: 'openai/gpt-6.1-sol',
  inputProcessors: [costCap, new ResponseCache({ cache: new InMemoryServerCache(), ttl: 600 })],
})
```

Force a refresh for one call:

```typescript
await searchAgent.stream('hello', {
  requestContext: ResponseCache.context({ bust: true }),
})
```

`TokenCostControl` needs observability storage with metric aggregates. Use `RedisServerCache` from `@mastra/redis` in production.
