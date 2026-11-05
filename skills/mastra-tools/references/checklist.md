# Tool checklist

Run this before calling a tool done.

## Definition

- [ ] `id` is unique and stable
- [ ] `description` is one short sentence on what the tool does and when to use it
- [ ] `inputSchema` fields have clear names, `.describe()` where not obvious, and explicit optionals
- [ ] `outputSchema` matches what `execute` actually returns
- [ ] `execute(inputData, context)` uses the current signature
- [ ] `context.abortSignal` is passed to network calls
- [ ] Secrets and tenant ids come from `context.requestContext` or env vars, never from model input

## What each audience sees

- [ ] Large or noisy results are reduced with `toModelOutput`
- [ ] Secrets and PII are redacted for `transform.display` and `transform.transcript`
- [ ] Client tool results are treated as untrusted

## Side effects

- [ ] Non-idempotent tools set `outputValidation: 'warn'`
- [ ] Destructive or costly tools use `requireApproval: true` (see `mastra-agent-approval-hitl`)
- [ ] Lifecycle hooks (`onOutput` and others) are idempotent

## Wiring

- [ ] Attached under a deliberate key (the key is the `toolName` in streams, traces, `activeTools`)
- [ ] Agent instructions name the tool and the condition for calling it
- [ ] Client tools live on the supervisor, not on subagents
- [ ] `webSearchTool` only on OpenAI, Anthropic, Google Gemini, or xAI models
- [ ] Task tools only on agents with memory
- [ ] Code mode has an explicit boundary: sandbox or isolating transport
- [ ] Large catalogs use `ToolSearchProcessor` or code mode instead of one huge `tools` object

## Verification

- [ ] `npx mastra api tool execute <tool-id> '<json>'` returns the expected shape
- [ ] An agent run in Studio calls the tool and uses the result
- [ ] A trace shows the tool span with sensible input and output (see `mastra-observability`)
