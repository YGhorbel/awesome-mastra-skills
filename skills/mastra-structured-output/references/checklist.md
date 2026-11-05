# Structured output checklist

Run this before calling typed agent output done.

## Schema

- [ ] Schema lives in a shared module imported by the caller and tests
- [ ] Labels use enums, not free strings
- [ ] Optional fields are explicit; required fields are truly required
- [ ] Ambiguous fields have `.describe()` text
- [ ] No deprecated `output` option; `structuredOutput` is used

## Mode

- [ ] Model supports native structured output, or `jsonPromptInjection` is set
- [ ] Agents with tools were tested with structured output on the chosen model
- [ ] Gemini 2.5 plus tools uses `jsonPromptInjection: true`
- [ ] Structuring `model` (if any) is a router string with its env var set
- [ ] `useAgent: true` set only when the structuring model needs thread memory
- [ ] Large schemas with injection have a compact `instructions` string listing every field

## Errors

- [ ] `errorStrategy` is chosen deliberately
- [ ] With `'fallback'`, the caller checks `usedFallbackValue`
- [ ] With `'strict'`, the caller catches and reports the error

## Consumption

- [ ] Callers read `response.object`, not `JSON.parse(response.text)`
- [ ] Streaming callers await `stream.object` or iterate `objectStream`
- [ ] Workflow agent steps pass `structuredOutput` so the next step's `inputSchema` matches

## Verification

- [ ] Representative and edge-case inputs return valid objects
- [ ] Token usage per call checked, especially with prompt injection or a structuring model
