# Structured output API reference

Distilled from `https://mastra.ai/docs/agents/structured-output.md`, `https://mastra.ai/reference/agents/generate.md`, `https://mastra.ai/reference/streaming/agents/MastraModelOutput.md`, and `https://mastra.ai/docs/workflows/agents-and-tools.md`. Verify against the installed version.

## Contents

- structuredOutput options
- Result fields
- Stream fields and chunks
- Workflow agent steps
- Deprecated options

---

## `structuredOutput` options

Passed to `agent.generate(messages, { structuredOutput })` and `agent.stream(messages, { structuredOutput })`. Also accepted by `@mastra/client-js` agent calls.

| Option | Type | Notes |
|---|---|---|
| `schema` | `StandardJSONSchemaV1` or JSON Schema object | Required. Zod, Valibot (`toStandardJsonSchema`), ArkType, or plain JSON Schema. |
| `model` | `MastraLanguageModel` (router string) | Separate structuring model. Enables multi-step runs with tool calls, text, then a structured object. Two LLM calls. |
| `useAgent` | `boolean` | With `model`: reuse the parent agent with the structuring model and attach read-only memory context when a thread exists. |
| `errorStrategy` | `'strict' \| 'warn' \| 'fallback'` | Default `'strict'` throws. `'warn'` logs. `'fallback'` returns `fallbackValue`. |
| `fallbackValue` | schema output type | Returned under `'fallback'`. Not validated. |
| `instructions` | `string` | Extra instructions for the structuring model. With `jsonPromptInjection` and no structuring model, replaces the serialized schema in the prompt. |
| `jsonPromptInjection` | `boolean \| 'system' \| 'inline' \| 'auto'` | How the schema reaches the model. See below. |
| `logger` | `IMastraLogger` | Logger for structured output generation. |
| `providerOptions` | `ProviderOptions` | Options for the internal structuring agent, for example `{ openai: { reasoningEffort: 'low' } }`. |

### `jsonPromptInjection` values

| Value | Behavior |
|---|---|
| `false` or omitted | Provider native structured output (`response_format`). |
| `'inline'` | Schema instructions added to the latest user message. |
| `true` or `'system'` | Schema instructions added to the system message. |
| `'auto'` | Native when the model supports it, inline injection otherwise or when capability data is missing. |

The response is always validated against `schema`, whichever mode is used.

---

## Result fields (`generate()`)

| Field | Notes |
|---|---|
| `object` | Parsed, schema-validated object. `undefined` without `structuredOutput`. |
| `usedFallbackValue` | `true` when `object` is `fallbackValue` because validation or the structuring model failed. |
| `text` | Natural language text, still produced. |
| `toolCalls`, `toolResults`, `steps`, `usage`, `finishReason` | As for any run. See `mastra-agents`. |

---

## Stream fields and chunks (`stream()`)

| Field | Notes |
|---|---|
| `objectStream` | `ReadableStream<Partial<OUTPUT>>` of progressive partial objects. |
| `object` | Promise of the final validated object. Await after or while consuming. |
| `fullStream` | Includes `object` chunks (partial data) and an `object-result` chunk with the final object. |
| `textStream` | Still emits natural language text, not structured data. |

```typescript
for await (const partial of stream.objectStream) {
  console.log('Progress:', partial)
}
const final = await stream.object
```

---

## Workflow agent steps

Without `structuredOutput`, an agent step has input `{ prompt: string }` and output `{ text: string }`.

With it, the step's `outputSchema` becomes your schema:

```typescript
const agentStep = createStep(testAgent, {
  structuredOutput: { schema: articleSchema },
})

// or the shorthand
createWorkflow({ /* ... */ }).agent(testAgent, { structuredOutput: { schema: articleSchema } })
```

The next step can declare `inputSchema: articleSchema`. See `mastra-workflows`.

---

## `prepareStep` with structured output

`prepareStep` may return `structuredOutput` for a given step, alongside `model`, `tools`, and `toolChoice`. Use it to call tools in early steps and structure the answer in a later step.

---

## Deprecated options

| Old | Replacement |
|---|---|
| `output: schema` | `structuredOutput: { schema }` with no `model` |
| `generateLegacy` / `streamLegacy` | `generate` / `stream`. See `mastra-migrations`. |
