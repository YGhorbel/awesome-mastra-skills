# Agent checklist

Run this before calling an agent done.

## Definition

- [ ] `id` is unique, kebab-case, and stable (renaming breaks stored threads, traces, and API URLs)
- [ ] `name` and `description` are set (description matters when used as a subagent)
- [ ] `model` is a verified `provider/model` string, or a fallback array
- [ ] Provider env var documented in `.env.example`
- [ ] Instructions state role, goal, constraints, output style, and when to call each tool
- [ ] Tools are keyed with names you want to see in streams and traces

## Behavior

- [ ] `maxSteps` (or `stopWhen`) bounds the loop
- [ ] `modelSettings.timeout` set for user-facing paths
- [ ] Per-request differences go through `requestContext`, with `requestContextSchema` for required keys
- [ ] Memory configured only if multi-turn is needed, with `resource` and `thread` set per call (see `mastra-memory`)
- [ ] Destructive tools gated by approval (see `mastra-agent-approval-hitl`)
- [ ] Input and output guardrails added for user-facing agents (see `mastra-processors-guardrails`)

## Wiring

- [ ] Registered in `new Mastra({ agents })`
- [ ] Callers use `mastra.getAgentById()`
- [ ] Visible and testable in Studio at `http://localhost:4111`

## Quality and operations

- [ ] At least one scorer or eval dataset covers the main task (see `mastra-evals`)
- [ ] Tracing enabled and a sample trace reviewed (see `mastra-observability`)
- [ ] Token usage per typical request checked against budget
- [ ] Error handling at the call site: provider errors, timeouts, aborted runs
