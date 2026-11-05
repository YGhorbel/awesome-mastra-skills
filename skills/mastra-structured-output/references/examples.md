# Structured output examples

All examples follow the current docs. `testAgent` and `weatherTool` stand in for an agent and tool defined as in `mastra-agents` and `mastra-tools`.

## Contents

1. Extraction with a fallback value
2. Streaming partial objects
3. Tools plus a separate structuring model with memory
4. Splitting tools and structuring with prepareStep
5. Typed agent step in a workflow
6. Compact injected instructions for a large schema

---

## 1. Extraction with a fallback value

```typescript
import { z } from 'zod'

const summarySchema = z.object({
  summary: z.string(),
  keyFeatures: z.array(z.string()),
})

const response = await testAgent.generate('Tell me about TypeScript.', {
  structuredOutput: {
    schema: summarySchema,
    errorStrategy: 'fallback',
    fallbackValue: {
      summary: 'TypeScript is a typed superset of JavaScript',
      keyFeatures: ['Static typing', 'Compiles to JavaScript', 'Better tooling'],
    },
  },
})

if (response.usedFallbackValue) {
  // The model output failed validation. Log it and show a degraded state.
}
console.log(response.object)
```

---

## 2. Streaming partial objects

```typescript
import { z } from 'zod'

const stream = await testAgent.stream('Generate user data', {
  structuredOutput: {
    schema: z.object({
      name: z.string(),
      age: z.number(),
      email: z.string(),
    }),
  },
})

for await (const partial of stream.objectStream) {
  console.log('Progress:', partial) // { name: "John" }, then { name: "John", age: 30 }, ...
}

const user = await stream.object
console.log('Final:', user)
```

To watch the final object inside `fullStream`, look for the `object-result` chunk:

```typescript
for await (const chunk of stream.fullStream) {
  if (chunk.type === 'object-result') {
    console.log(JSON.stringify(chunk, null, 2))
  }
}
```

---

## 3. Tools plus a separate structuring model with memory

The main agent runs every step, including tool calls. The structuring model converts the final answer. `useAgent: true` lets it read the thread.

```typescript
import { z } from 'zod'

const response = await testAgent.generate('Return my profile as structured data.', {
  memory: {
    thread: 'thread-123',
    resource: 'user-123',
  },
  structuredOutput: {
    schema: z.object({
      favoriteColor: z.string(),
      hometown: z.string(),
      petName: z.string(),
    }),
    model: 'openai/gpt-6.1-sol',
    useAgent: true,
  },
})

console.log(response.object)
```

This costs two LLM calls. Leave `useAgent` unset to structure only from the current response.

---

## 4. Splitting tools and structuring with prepareStep

For models that cannot combine tools and `response_format`:

```typescript
import { z } from 'zod'

const result = await agent.stream('weather in vancouver?', {
  prepareStep: async ({ stepNumber }) => {
    if (stepNumber === 0) {
      return {
        model: 'openai/gpt-6.1-sol',
        tools: { weatherTool },
        toolChoice: 'required',
      }
    }
    return {
      model: 'openai/gpt-6.1-sol',
      tools: undefined,
      structuredOutput: {
        schema: z.object({
          temperature: z.number(),
          humidity: z.number(),
          windSpeed: z.number(),
        }),
      },
    }
  },
})
```

For Gemini 2.5 with tools, the simpler fix is `jsonPromptInjection: true`.

---

## 5. Typed agent step in a workflow

```typescript
import { createWorkflow, createStep } from '@mastra/core/workflows'
import { z } from 'zod'

const articleSchema = z.object({
  title: z.string(),
  summary: z.string(),
  tags: z.array(z.string()),
})

const agentStep = createStep(testAgent, {
  structuredOutput: { schema: articleSchema },
})

const processStep = createStep({
  id: 'process',
  inputSchema: articleSchema,
  outputSchema: z.object({ tagCount: z.number() }),
  execute: async ({ inputData }) => ({
    tagCount: inputData.tags.length,
  }),
})

export const testWorkflow = createWorkflow({})
  .map(async ({ inputData }) => ({
    prompt: `Generate an article about: ${inputData.topic}`,
  }))
  .then(agentStep)
  .then(processStep)
  .commit()
```

`createWorkflow({})` is shortened here. Give it an `id`, `inputSchema`, and `outputSchema` as shown in `mastra-workflows`.

---

## 6. Compact injected instructions for a large schema

```typescript
const response = await testAgent.generate('Summarize this ticket.', {
  structuredOutput: {
    schema: ticketSchema,
    jsonPromptInjection: 'system',
    instructions:
      'Reply with a JSON object: "summary" (one paragraph), "priority" ("low" | "high"), "tags" (up to 5 strings). No markdown.',
  },
})
```

The response is still validated against `ticketSchema`. List every field in `instructions`, because the model no longer sees the full schema.
