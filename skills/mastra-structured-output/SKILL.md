---
name: mastra-structured-output
description: "Make a Mastra agent return a typed, schema-validated object instead of text, with structuredOutput on generate() or stream(), response.object, objectStream, a separate structuring model, jsonPromptInjection, and errorStrategy fallbacks. Use this skill whenever the user wants JSON output, typed results, data extraction, classification labels, or form-like answers from an agent, or when tools and structured output conflict on a model. Triggers on structuredOutput, response.object, stream.object, objectStream, object-result, jsonPromptInjection, errorStrategy, fallbackValue, usedFallbackValue, structuring model, useAgent, response_format, JSON schema output, Zod output schema, Valibot, ArkType, deprecated output option. Also triggers when an agent step in a workflow must return typed data, or when Gemini errors with function calling and a JSON response mime type."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Typed agent output with structuredOutput, streaming objects, structuring models, prompt injection, and error strategies"
  display_order: 3
  docs: https://mastra.ai/docs/agents/structured-output
---

# Mastra Structured Output

Get a validated, typed object from an agent by passing a schema in `structuredOutput` and reading `response.object`.

---

## When to use

- The caller needs data, not prose: extraction, classification, summaries with fixed fields, UI payloads
- Reading `response.object` or streaming partial objects with `objectStream`
- An agent step in a workflow must return typed data for the next step
- Tools and structured output fail together on a model
- Large schemas cost too many tokens per step
- Deciding what happens when the model returns an invalid object

## When NOT to use

- Tool input and output schemas (use `mastra-tools`)
- General agent setup and `generate()`/`stream()` basics (use `mastra-agents`)
- Stream chunk types and stream consumption in general (use `mastra-streaming`)
- Labeling inputs with a dedicated classifier primitive (use `mastra-classifier`)
- Validating or rewriting output with processors and guardrails (use `mastra-processors-guardrails`)
- Workflow step wiring beyond the agent step itself (use `mastra-workflows`)
- Picking a model that supports native JSON output (use `mastra-models`)

---

## Required inputs

- The target shape: fields, types, required versus optional, enums
- Schema library in the project (Zod, Valibot, ArkType, or plain JSON Schema)
- Whether the agent also calls tools in the same run
- Whether the caller needs partial results while streaming
- What to do on invalid output: throw, warn, or return a fallback

---

## The framework: schema in, object out

```typescript
import { z } from 'zod'

const response = await testAgent.generate('Help me plan my day.', {
  structuredOutput: {
    schema: z.array(
      z.object({
        name: z.string(),
        activities: z.array(z.string()),
      }),
    ),
  },
})

console.log(response.object) // typed from the schema
```

The schema is input. The object is output. `response.object` is already parsed and validated, so do not parse it again. `response.text` is still available.

Schemas: any Standard JSON Schema library (Zod, Valibot through `toStandardJsonSchema`, ArkType) or a plain JSON Schema object. Zod gives type inference and runtime validation.

### Four ways the schema reaches the model

| Mode | How | Cost | Use when |
|---|---|---|---|
| Native (default) | Provider `response_format` | One call | The model supports native JSON output |
| `jsonPromptInjection: 'auto'` | Native if supported, else inline injection | One call | You do not know the model's capability |
| `jsonPromptInjection: 'inline' \| 'system' \| true` | Schema text injected into the prompt | One call, more input tokens | Model rejects tools plus `response_format` |
| `model: 'provider/model'` | A second structuring agent converts the main answer | Two calls | Main model is weak at structuring, or uses tools heavily |

`'inline'` adds to the latest user message. `true` or `'system'` adds to the system message.

### Errors

| `errorStrategy` | Behavior |
|---|---|
| `'strict'` (default) | Throws on validation or structuring failure |
| `'warn'` | Logs a warning and continues |
| `'fallback'` | Returns `fallbackValue` and sets `response.usedFallbackValue: true` |

`fallbackValue` never went through the schema. Check `usedFallbackValue` before trusting the object.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `StructuredOutputOptions` type. Otherwise fetch `https://mastra.ai/docs/agents/structured-output.md` and `https://mastra.ai/reference/agents/generate.md`. Trust these over memory.
2. **Write the schema.** Keep it flat where possible. Use enums for labels. Add `.describe()` on ambiguous fields.
3. **Call with `structuredOutput: { schema }`** and read `response.object` (or `await stream.object`).
4. **Check tools.** If the agent has tools, test the model with both. On errors or tools never being called, pick a workaround: `jsonPromptInjection: 'auto'`, a structuring `model`, or `prepareStep`.
5. **Set `errorStrategy`.** Use `'fallback'` with a safe `fallbackValue` on user-facing paths, and branch on `usedFallbackValue`.
6. **Trim tokens.** With prompt injection and a large schema, set `instructions` to a compact field description.
7. **Stream if needed.** Iterate `stream.objectStream` for partial objects. Read `await stream.object` for the final one.
8. **In workflows,** pass `structuredOutput` to `createStep(agent, {...})` or `.agent(agent, {...})` so the step's `outputSchema` matches.
9. **Test** with real inputs, including edge cases that tempt the model to add prose or skip fields.

---

## Deep dive: tools plus structured output

Some provider APIs cannot combine function calling and `response_format` in one call. This is a model limitation, not a Mastra one. Gemini 2.5 with tools fails with `Function calling with a response mime type: 'application/json' is unsupported` unless you set `jsonPromptInjection: true`.

Option 1, let Mastra choose:

```typescript
structuredOutput: { schema, jsonPromptInjection: 'auto' }
```

Option 2, a separate structuring model. The main agent does all steps including tool calls. The structuring model only builds the object. Add `useAgent: true` to let it see conversation memory.

```typescript
const response = await testAgent.generate('Tell me about TypeScript.', {
  structuredOutput: {
    schema: yourSchema,
    model: 'openai/gpt-6.1-sol',
  },
})
```

Option 3, split steps with `prepareStep`: call tools in step 0 with `toolChoice: 'required'`, then return `tools: undefined` and `structuredOutput` for later steps (see `references/examples.md`).

---

## Failure patterns

- **Using the deprecated `output` option.** Use `structuredOutput` without a `model` for the same behavior.
- **Parsing `response.text` with `JSON.parse`.** Read `response.object`. It is already validated and typed.
- **Treating a fallback as a real answer.** Check `response.usedFallbackValue` under `errorStrategy: 'fallback'`.
- **Tools never called once structured output is on.** The model cannot combine them. Use `jsonPromptInjection: 'auto'`, a structuring `model`, or `prepareStep`.
- **Gemini 2.5 JSON mime type error with tools.** Set `jsonPromptInjection: true`.
- **Huge token bills per step.** Prompt injection embeds the full schema every call. Add a compact `instructions` string that lists every field.
- **`instructions` set with native structured output.** It has no effect without injection or a structuring model.
- **Structuring model ignores earlier turns.** It only sees the current response. Set `useAgent: true` with memory.
- **Reading `stream.object` before the stream finishes.** Await it, or consume `objectStream` for partials.
- **`model: 'openai:gpt-...'` or a provider object for the structuring model.** Use a router string such as `'openai/gpt-6.1-sol'`.

---

## Output format

A finished structured output delivery contains:

- The schema in a shared module (for example `src/mastra/schemas/<name>.ts`) so callers and tests import the same type
- The `generate()`/`stream()` call, workflow step, or route using `structuredOutput`
- An explicit `errorStrategy`, with `usedFallbackValue` handled when using `'fallback'`
- A note on the chosen mode (native, injection, or structuring model) and why
- A test or Studio run showing a valid object for representative inputs

---

## Reference files

- [`references/api.md`](references/api.md) - `structuredOutput` options, result fields, stream fields, workflow step usage.
- [`references/examples.md`](references/examples.md) - Extraction with fallback, streaming partial objects, tools plus structuring model, `prepareStep` split, workflow agent step.
- [`references/checklist.md`](references/checklist.md) - Checklist for typed agent output.

**Live docs**

- https://mastra.ai/docs/agents/structured-output
- https://mastra.ai/reference/agents/generate
- https://mastra.ai/reference/streaming/agents/MastraModelOutput
- https://mastra.ai/docs/workflows/agents-and-tools
