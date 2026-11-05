# Multi-agent checklist

Run this before calling a multi-agent system done.

## Design

- [ ] A single agent was tried or ruled out with a reason
- [ ] The pattern is chosen on purpose: supervisor, workflow, handoff, or council
- [ ] Each subagent has one responsibility and its own minimal tool set
- [ ] No two subagents overlap enough to confuse routing

## Subagents

- [ ] Every subagent has a `description` covering purpose, return format, and when to use it
- [ ] Every subagent has `defaultOptions.maxSteps`
- [ ] Subagents do not depend on client tools (no `execute`); those live on the supervisor
- [ ] Subagent models are sized to the job (smaller models for narrow tasks)

## Supervisor

- [ ] Instructions list available resources, the delegation strategy, and success criteria
- [ ] Every call sets `maxSteps`
- [ ] Shared hooks live in `defaultOptions.delegation`
- [ ] `messageFilter` trims or redacts context when subagents should not see everything
- [ ] Hooks that must succeed use `hookErrorStrategy: 'throw'`
- [ ] Failure handling is explicit: `bail()`, `feedback`, or a curated `resultText` (never raw provider errors)
- [ ] `isTaskComplete` with a rubric or custom scorer is set when output quality must meet criteria
- [ ] `abortSignal` is wired from the caller for user-facing runs

## Memory and context

- [ ] Supervisor memory configured if the conversation is multi-turn (see `mastra-memory`)
- [ ] `threadMetadata` set in `onDelegationStart` when subagent threads must be filterable by tenant
- [ ] Values passed through `context.requestContext` are JSON-serializable

## Operations

- [ ] Supervisor and subagents registered on `new Mastra({ agents })`
- [ ] A trace reviewed: each delegation prompt, step count, and result look right (see `mastra-observability`)
- [ ] Token cost per typical task measured, including grader calls
- [ ] Approval-gated subagent tools tested end to end through the supervisor stream (see `mastra-agent-approval-hitl`)
- [ ] No new code uses `agent.network()`
