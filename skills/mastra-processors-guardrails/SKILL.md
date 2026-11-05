---
name: mastra-processors-guardrails
description: "Add input, output, and error processors to Mastra agents: built-in guardrails for prompt injection, PII, moderation, system prompt leaks, regex filters, language detection, token and cost limits, response caching, and custom processors with processInput, processInputStep, processOutputStream, processOutputStep, processToolResult, and processAPIError. Use this skill whenever the user wants to block, redact, rewrite, moderate, validate, or limit what goes into or comes out of an agent, retry a bad response, cap spend, cache responses, or run guardrails in parallel. Triggers on inputProcessors, outputProcessors, errorProcessors, @mastra/core/processors, Processor interface, PromptInjectionDetector, PIIDetector, ModerationProcessor, SystemPromptScrubber, RegexFilterProcessor, TokenLimiter, TokenCostControl, ToolCallFilter, BatchPartsProcessor, ResponseCache, tripwire, onViolation, maxProcessorRetries. Also triggers for jailbreak defense, content safety, and redaction."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Input, output, and error processors: built-in guardrails, custom processors, tripwires, retries, and caching"
  display_order: 4
  docs: https://mastra.ai/docs/agents/processors
---

# Mastra Processors and Guardrails

Control what enters and leaves an agent with processors: built-in guardrails, custom processors, tripwires, and retries.

---

## When to use

- Blocking prompt injection, jailbreaks, or system prompt overrides
- Redacting PII or secrets on input, output, or tool results
- Moderating harmful content in either direction
- Limiting tokens, trimming context, or capping monetary cost
- Validating a response and asking the model to retry
- Switching model or tool choice per step
- Recovering from provider API errors
- Caching identical LLM requests
- Running several guardrails in parallel to cut latency

## When NOT to use

- Shaping one tool's output for the model or UI (use `mastra-tools`: `toModelOutput`, `transform`)
- Blocking a specific tool call before it runs (use `mastra-tools`: `hooks.beforeToolCall`)
- Human approval of tool calls (use `mastra-agent-approval-hitl`)
- Typed objects from the model (use `mastra-structured-output`)
- Labeling text with typed answers outside a pipeline (use `mastra-classifier`)
- Memory processors for history, semantic recall, and working memory (use `mastra-memory`)
- Large tool catalogs through `ToolSearchProcessor` (use `mastra-tools`)
- Scoring response quality offline or live (use `mastra-evals`)

---

## Required inputs

- The threat or rule: what must be blocked, redacted, rewritten, or limited
- Direction: input, output, tool results, or provider errors
- Strategy per rule: `block`, `warn`, `filter`, `redact`, `rewrite`, `detect`, or `translate`
- Fail mode if a guardrail model fails: fail-open (`warn`) or fail-closed (`strict`)
- Latency budget for LLM-based guardrails
- How the caller handles a blocked request (tripwire)

---

## The framework: three arrays, one interface

```typescript
import { Agent } from '@mastra/core/agent'
import {
  UnicodeNormalizer,
  PromptInjectionDetector,
  PIIDetector,
  ModerationProcessor,
} from '@mastra/core/processors'

const GUARDRAIL_MODEL = 'openai/gpt-6-luna'

export const secureAgent = new Agent({
  id: 'secure-agent',
  name: 'Secure Agent',
  instructions: 'You are a helpful assistant',
  model: 'openai/gpt-6.1-sol',
  inputProcessors: [
    new UnicodeNormalizer({ stripControlChars: true, collapseWhitespace: true }),
    new PromptInjectionDetector({ model: GUARDRAIL_MODEL, threshold: 0.8, strategy: 'block' }),
    new PIIDetector({ model: GUARDRAIL_MODEL, strategy: 'redact', redactionMethod: 'mask' }),
  ],
  outputProcessors: [new ModerationProcessor({ model: GUARDRAIL_MODEL, strategy: 'block' })],
})
```

| Array | Runs | Typical use |
|---|---|---|
| `inputProcessors` | Before the LLM, and per step | Normalize, detect injection, redact, trim tokens, switch models |
| `outputProcessors` | During and after the response | Moderate, scrub, redact, batch chunks, validate and retry |
| `errorProcessors` | When the provider call throws | Repair the request and retry |

Order matters. Processors run in array order. With memory: `[memory] -> [your inputProcessors]` and `[your outputProcessors] -> [memory]`. An output guardrail that aborts skips memory, so the message is not saved.

Every array also accepts a function of `{ requestContext }`. Passing an array to `generate()`/`stream()` replaces the agent's array for that call.

### Processor methods

| Method | Runs | Use |
|---|---|---|
| `processInput` | Once before the loop | Rewrite or reject user input |
| `processInputStep` | Before every model step | Swap `model`, `tools`, `toolChoice`, send signals |
| `processLLMRequest` | Right before each provider call | Transient prompt rewrites, cache lookup |
| `processOutputStream` | Each streamed chunk | Filter or edit chunks. Return `null` to drop |
| `processLLMResponse` | After each provider stream | Cache writes, side effects |
| `processOutputStep` | After each model step | Validate, `abort(reason, { retry: true })` |
| `processToolResult` | Each tool result before it enters history | Redact or block tool output |
| `processOutputResult` | Once at the end | Final transforms, usage tracking, metadata |
| `processAPIError` | On provider API errors | Fix the request, return `{ retry: true }` |

### Blocking and tripwires

`abort(reason, { retry?, metadata? })` throws a `TripWire`. Detect it at the call site:

```typescript
const result = await agent.generate('Is this credit card number valid?: 4543 1374 5089 4332')
if (result.tripwire) {
  console.error('Blocked:', result.tripwire.reason, result.tripwire.processorId)
}
```

On streams, look for `chunk.type === 'tripwire'` with `chunk.payload.reason` and `chunk.payload.processorId`. `generate()` also sets `finishReason: 'other'`.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed processor types. Otherwise fetch `https://mastra.ai/docs/agents/processors.md`, `https://mastra.ai/docs/agents/guardrails.md`, and the processor reference page. Trust these over memory.
2. **List the rules.** For each, pick direction, built-in processor, and strategy (see `references/built-in-processors.md`).
3. **Prefer cheap checks first.** `UnicodeNormalizer` and `RegexFilterProcessor` make no LLM calls. Put them before LLM-based guardrails.
4. **Use a small guardrail model.** Guardrails do not need the primary model. Set `lastMessageOnly: true` on long threads.
5. **Choose fail mode.** Model-backed guardrails default to `errorStrategy: 'warn'` (fail-open). Use `'strict'` when unchecked content must never pass.
6. **Order the arrays.** Normalize, then detect, then redact. For output, put `BatchPartsProcessor` before heavier stream processors.
7. **Parallelize independent checks** with a processor workflow (see Deep dive).
8. **Handle tripwires** in every caller: check `result.tripwire` or the `tripwire` chunk and show a safe message.
9. **Add `onViolation`** for alerting and audit logs.
10. **Set `maxProcessorRetries`** if any processor uses `abort(..., { retry: true })`. Without it, step retries do not run.
11. **Test** with benign and adversarial inputs in Studio. Processor workflows appear there as workflows.

---

## Deep dive: parallel guardrails

Processors run sequentially by default. Run independent checks in parallel with a workflow. Map to the `redact` branch so its rewritten messages carry forward.

```typescript
import { createWorkflow, createStep } from '@mastra/core/workflows'
import {
  ProcessorStepSchema,
  PIIDetector,
  PromptInjectionDetector,
  ModerationProcessor,
} from '@mastra/core/processors'

export const inputGuardrails = createWorkflow({
  id: 'input-guardrails',
  inputSchema: ProcessorStepSchema,
  outputSchema: ProcessorStepSchema,
})
  .parallel([
    createStep(new PIIDetector({ model: 'openai/gpt-6-luna', strategy: 'redact' })),
    createStep(new PromptInjectionDetector({ model: 'openai/gpt-6-luna', strategy: 'block' })),
    createStep(new ModerationProcessor({ model: 'openai/gpt-6-luna', strategy: 'block' })),
  ])
  .map(async ({ inputData }) => inputData['processor:pii-detector'])
  .commit()

// new Agent({ ..., inputProcessors: [inputGuardrails] })
```

Branch results are keyed `processor:<id>`. If every branch only blocks, map to any branch.

---

## Failure patterns

- **Retry never happens.** `abort(..., { retry: true })` needs `maxProcessorRetries` on the agent or call. It is unset by default.
- **Guardrail model outage lets content through.** Default `errorStrategy` is `'warn'` (fail-open). Set `'strict'` for must-block rules.
- **Caller ignores tripwires.** The response looks empty. Check `result.tripwire` or the `tripwire` chunk.
- **Redaction lost after a parallel step.** `.map()` picked a block-only branch. Map to the `redact` branch.
- **Slow streams.** LLM guardrails run per chunk. Add `BatchPartsProcessor` first, or set `bufferSize` on `ModerationProcessor`/`SystemPromptScrubber`.
- **One LLM call per old message.** Set `lastMessageOnly: true` on detectors in long threads.
- **Reading `message.content` as a string in a custom processor.** Text lives in `message.content.parts`. Filter `part.type === 'text'`.
- **`processOutputStream` returns nothing.** `undefined` drops the chunk. Return `part` to pass it through.
- **Custom `data-*` chunks never reach the processor.** Set `processDataParts = true`.
- **Per-call `errorProcessors` drops defaults.** A per-call list replaces the resolved list, defaults included. Pass a same-`id` instance on the agent to customize one default instead.
- **Expecting `onViolation` for every block.** It does not fire for `processToolResult` aborts or for processor workflows while streaming output.
- **Caching tools with side effects.** `ResponseCache` replays tool calls without running them. Skip it for side-effecting agents.
- **`TokenCostControl` overshoots.** Metrics persist asynchronously. Treat the limit as approximate and set `warnAtPercent`.

---

## Output format

A finished processor delivery contains:

- Custom processors in `src/mastra/processors/<id>.ts`, each with a stable `id`
- Processor workflows (if any) in `src/mastra/processors/` with `ProcessorStepSchema`
- The agent's `inputProcessors`, `outputProcessors`, and `errorProcessors` in a deliberate order
- `maxProcessorRetries` set when retries are used
- Tripwire handling at each call site, and `onViolation` wiring for alerts
- Tests or Studio runs with benign and adversarial inputs, plus a latency check

---

## Reference files

- [`references/api.md`](references/api.md) - `Processor` interface, method arguments and returns, abort and tripwire shapes, agent options.
- [`references/built-in-processors.md`](references/built-in-processors.md) - Built-in guardrail and utility processors with their options.
- [`references/examples.md`](references/examples.md) - Layered guardrails, custom input and output processors, quality retry, tool result redaction, cost cap, response cache.
- [`references/checklist.md`](references/checklist.md) - Guardrail production checklist.

**Live docs**

- https://mastra.ai/docs/agents/processors
- https://mastra.ai/docs/agents/guardrails
- https://mastra.ai/reference/processors/processor-interface
- https://mastra.ai/docs/guides/agent-lifecycle
- https://mastra.ai/docs/memory/memory-processors
