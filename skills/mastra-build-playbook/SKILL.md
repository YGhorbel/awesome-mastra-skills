---
name: mastra-build-playbook
description: "End-to-end playbook for building a production AI app with Mastra, from framing the job through a first working agent, context design, safety, an eval loop, observability, integration, and deployment. Use this skill whenever the user wants to build a complete Mastra app or agent product, plan a Mastra project, take a prototype to production, or asks how to go from idea to deployed agent. Triggers on build an app with Mastra, Mastra project plan, from prototype to production, ship a Mastra agent, Mastra best practices, Mastra architecture plan, end to end Mastra, production-ready agent. Also triggers when a request spans several Mastra features at once (agent plus memory plus UI plus deploy), even if the user does not ask for a plan."
license: Apache-2.0
metadata:
  category: getting-started
  catalog_summary: "Idea to production in 9 phases: scope, scaffold, first slice, context, safety, evals, tracing, integrate, deploy"
  display_order: 3
  docs: https://mastra.ai/docs/guides/overview
---

# Mastra Build Playbook

Take a Mastra app from idea to production in nine phases, each with an exit gate and the skill that does the work.

---

## When to use

- Starting a new Mastra product or agent feature from scratch
- Turning a working prototype into something you can ship
- Planning which Mastra features a project needs, in what order
- Reviewing a Mastra project for production gaps

## When NOT to use

- A single, already-scoped feature (go to its skill through `mastra-guide`)
- Only creating the project scaffold (use `mastra-project-setup`)
- Only setting up evals (use `mastra-evals` and `mastra-datasets-experiments`)
- Only deploying an existing app (use `mastra-deployment` or `mastra-platform`)
- Fixing an error (use `mastra-troubleshooting`)

---

## Required inputs

- The job: who uses it, what they ask, what a correct outcome looks like
- Hard constraints: data it may touch, actions that need approval, latency and cost budget
- Where it runs: standalone server, inside an existing web app, or Mastra Platform
- Who owns quality: example inputs and expected behavior, even five cases

If the user cannot state a correct outcome for three real inputs, do phase 1 before writing code.

---

## The framework: 9 phases with exit gates

| # | Phase | Exit gate | Skills |
|---|---|---|---|
| 1 | Frame the job | Five example inputs with expected behavior. Agent vs workflow decided. | `mastra-guide` |
| 2 | Scaffold | `npx mastra dev` runs, Studio opens at `http://localhost:4111` | `mastra-project-setup`, `mastra-models` |
| 3 | First slice | One agent or workflow answers one real input end to end | `mastra-agents`, `mastra-tools`, `mastra-workflows` |
| 4 | Context design | Each piece of information has one home (instructions, tool, memory, RAG, signal) | `mastra-memory`, `mastra-rag`, `mastra-knowledge`, `mastra-structured-output` |
| 5 | Control and safety | Loops bounded, risky actions gated, inputs and outputs filtered | `mastra-processors-guardrails`, `mastra-agent-approval-hitl` |
| 6 | Eval loop | Golden dataset, judge scorer, baseline experiment recorded | `mastra-evals`, `mastra-datasets-experiments` |
| 7 | Observability | Every run traced, cost per request known | `mastra-observability` |
| 8 | Integrate | Users reach it through an authenticated API or UI | `mastra-server`, `mastra-client-sdk`, `mastra-framework-integration`, `mastra-agentic-ui`, `mastra-auth`, `mastra-channels` |
| 9 | Deploy and operate | Production storage, CI eval gate, deploy pipeline, alerts | `mastra-storage`, `mastra-deployment`, `mastra-platform`, `mastra-harness` |

Phases 3 to 6 repeat. Every change to instructions, model, or tools reruns the eval loop.

### Phase 1 decision: agent or workflow

- Steps unknown, model must choose tools and loop: **agent**.
- Steps known, needs branching, retries, or human checkpoints: **workflow**.
- Both: a workflow whose steps call agents, or an agent that calls a workflow as a tool.

### The minimal first slice

```typescript
// src/mastra/agents/refund-agent.ts
import { Agent } from '@mastra/core/agent'

export const refundAgent = new Agent({
  id: 'refund-agent',
  name: 'Refund Agent',
  instructions: `Answer reservation-deposit refund questions using the policy below.
    Ask for missing information. Do not invent policy exceptions.
    ...policy...`,
  model: 'openai/gpt-6.1-sol',
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { refundAgent } from './agents/refund-agent'

export const mastra = new Mastra({ agents: { refundAgent } })
```

Run it in Studio before adding anything else.

---

## Workflow

1. **Verify the API.** For each phase, read the embedded docs in `node_modules/@mastra/*/dist/docs/` or the live `.md` pages linked from the phase's skill. Trust these over memory.
2. **Frame the job.** Write five test cases as `{ input, groundTruth: { must: [...], mustNot: [...] } }`. These become the golden dataset in phase 6.
3. **Scaffold** with `npm create mastra@latest`, or add Mastra to the existing app. Set the provider key in `.env`.
4. **Build the first slice.** One agent, no memory, at most one tool. Register it. Run the five cases by hand in Studio.
5. **Design context.** Use the context table in `mastra-guide`. Add memory only for multi-turn needs. Add RAG only when the knowledge does not fit in instructions.
6. **Add control.** `maxSteps` and `modelSettings.timeout` on every agent. Approval on tools with side effects. Guardrail processors on user-facing input and output.
7. **Build the eval loop.** Create the dataset, an LLM judge scorer from a different provider than the agent, and a baseline experiment. Change one thing at a time and compare.
8. **Turn on tracing.** Inspect a trace for each test case. Note tokens and latency per request.
9. **Integrate.** Expose through the Mastra server or your framework, add auth, connect the UI with `MastraClient` or AI SDK UI.
10. **Deploy.** Switch to production storage (Postgres or similar), run the regression eval in CI as a required check, deploy, and set alerts.
11. **Operate.** Add failing production traces to the dataset. Repeat from step 7.

---

## Deep dive: the eval loop is the development loop

Mastra's recommended loop: curate cases, evaluate, diagnose and improve, repeat.

- Keep the dataset and the judge fixed while changing the agent. Otherwise you cannot tell what helped.
- Use a binary judge (1 pass, 0 fail) for policy correctness. Fractional scores hide unsafe answers.
- Treat the judge as fallible. Read its reasons, including on passing cases.
- Grow the dataset from production: Studio can add a full trace to a dataset.
- Gate releases with `runEvals` and require `verdict === 'passed'` (see [`references/examples.md`](references/examples.md)).

---

## Failure patterns

- **Building phases 4 to 9 before phase 3 works.** Memory, RAG, and UI on top of a broken agent multiply debugging time. Get one input right first.
- **No expected behavior written down.** "It looks good" is not an eval. Write `must` and `mustNot` per case.
- **Changing prompt, model, and tools at once.** You lose attribution. One change per experiment.
- **Judging with the same model as the agent.** Shared blind spots. Use another provider.
- **In-memory or file storage in production.** Threads, snapshots, and traces vanish on restart. Use a production adapter (`mastra-storage`).
- **Unbounded agent loops.** Always set `maxSteps` and timeouts.
- **Side-effecting tools without approval.** Refunds, emails, deletes need `mastra-agent-approval-hitl`.
- **Secrets in code or committed `.env` files.** Keep keys in the environment and `.env.example` without values.
- **Shipping without traces.** You cannot debug what you cannot see. Enable observability before the first user.

---

## Output format

A build plan or review delivers:

- A phase table for the project: status per phase, owner, exit gate evidence
- The feature list with the skill for each
- The golden dataset (5+ cases) checked into the repo
- `src/mastra/` structure: `agents/`, `tools/`, `workflows/`, `scorers/`, `index.ts`
- A CI job that runs the regression eval and blocks deploy on failure
- A deploy target and the env vars it needs

---

## Reference files

- [`references/api.md`](references/api.md) - Phase map: commands, key APIs, and files per phase.
- [`references/examples.md`](references/examples.md) - Worked build: a refund policy agent from first slice to CI regression gate.
- [`references/checklist.md`](references/checklist.md) - Launch checklist across all nine phases.

**Live docs**

- https://mastra.ai/docs
- https://mastra.ai/docs/guides/overview
- https://mastra.ai/docs/guides/context-engineering
- https://mastra.ai/docs/guides/agent-lifecycle
- https://mastra.ai/docs/guides/build-an-eval-loop
- https://mastra.ai/docs/deployment/overview
