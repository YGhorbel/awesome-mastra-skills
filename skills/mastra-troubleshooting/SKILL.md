---
name: mastra-troubleshooting
description: "Diagnose and fix Mastra errors: ESM and CommonJS import failures, tsconfig settings, wrong model string format, missing provider env vars, outdated API shapes from older versions, the createTool execute signature, storage and memory errors, workflow commit and suspend mistakes, build and deploy failures, and client SDK error handling. Use this skill whenever the user pastes a Mastra error or stack trace, says an agent ignores its tools or forgets the conversation, sees Property does not exist on type after copying an example, gets 401s from a model provider, or wants to report a verified Mastra bug. Triggers on Cannot find module @mastra/core, Cannot use import statement outside a module, MastraError, Memory requires a storage provider, ValidationError, Tool output validation failed, openai:gpt, threadId resourceId, runtimeContext, getAgents, createRunAsync, ECONNREFUSED, JavaScript heap out of memory, SERVER_UNREACHABLE. Also triggers when code compiles against training-data examples but fails at runtime."
license: Apache-2.0
metadata:
  category: getting-started
  catalog_summary: "Diagnosis flow and fixes for ESM, tsconfig, model strings, env vars, outdated APIs, tools, storage, memory, client errors"
  display_order: 4
  docs: https://mastra.ai/reference/client-js/error-handling
---

# Mastra Troubleshooting

Find the real cause of a Mastra failure, fix it against the installed version's API, and report genuine Mastra defects with evidence.

---

## When to use

- A Mastra project fails to start, build, type-check, or deploy
- An agent ignores tools, loses conversation history, or returns empty answers
- A model call fails with auth, "model not found", or format errors
- Code copied from an older example fails (`Property 'x' does not exist`, renamed methods)
- Tool input or output validation errors
- Storage connection or schema errors after an upgrade
- Handling errors from `MastraClient` calls in a frontend or service
- Deciding whether a failure is a Mastra bug and how to report it

## When NOT to use

- Planned version upgrades and codemods (use `mastra-migrations`)
- Deploy target setup and platform config (use `mastra-deployment` or `mastra-platform`)
- Reading traces and spans to find a failing run (use `mastra-cli-api`, `mastra-observability`)
- Designing agents, tools, or memory from scratch (use `mastra-agents`, `mastra-tools`, `mastra-memory`)
- Picking a model or provider env var name (use `mastra-models`)
- Storage adapter configuration in depth (use `mastra-storage`)
- New project scaffolding (use `mastra-project-setup`)

---

## Required inputs

- The exact error message and stack trace (first Mastra frame matters most)
- Installed versions: `npm list @mastra/core mastra` plus any `@mastra/*` in use
- Node.js version (`node --version`, must be `22.13.0` or later)
- Where it fails: `mastra dev`, `mastra build`, runtime call, deployed server, or browser client
- The smallest code that reproduces it (agent, tool, or workflow definition)

Ask for the full error and versions before guessing. Most Mastra failures are version mismatches between the code and the installed package.

---

## The framework: classify, verify, fix

| Class | Typical signal | First check |
|---|---|---|
| Module system | `Cannot use import statement outside a module`, `Cannot find module` | `"type": "module"`, tsconfig `module`/`moduleResolution` |
| Version drift | `Property 'x' does not exist`, `is not a function` | Installed version vs the example's version |
| Model config | `Invalid model format`, 401, "API key not found" | `provider/model` string, provider env var |
| Wiring | Agent never calls tools, missing in Studio | Registration on `new Mastra({...})`, instructions |
| Memory and storage | History lost, `Memory requires a storage provider` | Storage on Mastra or Memory, `memory: { resource, thread }` |
| Validation | `ValidationError`, `Tool output validation failed` | `inputSchema`, `outputSchema`, `requestContextSchema` |
| Build and deploy | Heap OOM, missing native module, data loss | See `mastra-deployment` |
| Client | Thrown errors from `MastraClient` | Server reachable, auth headers, retries |

The current tool signature is the most common version-drift fix:

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const weatherTool = createTool({
  id: 'weather-tool',
  description: 'Get the current weather for a location',
  inputSchema: z.object({
    location: z.string(),
  }),
  outputSchema: z.object({
    location: z.string(),
    temperatureCelsius: z.number(),
    conditions: z.string(),
  }),
  execute: async ({ location }) => {
    return {
      location,
      temperatureCelsius: 21,
      conditions: 'sunny',
    }
  },
})
```

The first `execute` argument is the validated input. The optional second argument is the context (`requestContext`, `agent`, `workflow`, `mcp`).

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` (search `references/`, check `assets/SOURCE_MAP.json` for an export, then read its `.d.ts`). Otherwise fetch the live page as Markdown, for example `https://mastra.ai/reference/tools/create-tool.md`. Trust these over memory and over the user's copied example.
2. **Reproduce in isolation.** Run `mastra dev` and trigger the agent, tool, or workflow in Studio (`http://localhost:4111`) or with `mastra api` (see `mastra-cli-api`). Studio shows logs and traces.
3. **Check versions.** `npm list @mastra/core mastra`. All `@mastra/*` packages and `mastra` must move together. Mixed versions cause type and runtime errors.
4. **Classify the error** with the table above and the catalog in `references/api.md`.
5. **Check configuration.** `npx tsc --showConfig` for `target`/`module`/`moduleResolution`. Confirm env vars load (`mastra dev` and `mastra start` load `.env` files; `mastra build` does not).
6. **Turn up logging.** Set `PinoLogger` `level: 'debug'` and rerun.
7. **Fix the root cause.** Change code to the shape in the installed docs. For renamed APIs after an upgrade, use `mastra-migrations` and its codemods.
8. **Confirm the fix.** Rerun the reproduction, then `npx tsc --noEmit` and the test suite.
9. **Report real defects.** If the installed version contradicts its own docs or behaves wrongly in a minimal reproduction, draft a report (see the deep dive) and send it only with the user's agreement.

---

## Deep dive: reporting a verified bug

Report only what you verified: a reproducible Mastra defect on an identified installed version, or documentation that is wrong or contradictory and affected the task. Do not report configuration mistakes, rate limits, unverified suspicions, or feature requests.

Build an anonymized report: no project names, source code, raw logs, local paths, private URLs, or secrets. Start `note` with one sentence naming the component and the failure, then versions tested, setup, steps, expected vs actual, and any workaround tried.

```bash
curl -i -X POST https://mastra.ai/api/feedback \
  -H 'Content-Type: application/json' \
  -d '{"category":"bug","note":"<one-sentence symptom>. Tested environment: @mastra/core <resolved-version>, Node <version>. Reproduction: ... Expected ... observed ..."}'
```

- `category`: `bug` or `docs`. `note`: 20 to 4,000 characters. Optional `url`: a public Mastra docs page you actually used. Body under 16 KiB. No other fields.
- `201` means created; `200` with `duplicate: true` means already reported. Do not resend.
- Show the drafted payload to the user and send it only when they agree, unless they explicitly asked you to report it. Alternatively, file an issue at `https://github.com/mastra-ai/mastra/issues`.

---

## Failure patterns

- **`Cannot use import statement outside a module`.** Add `"type": "module"` to `package.json` and use the ES2022 tsconfig from `references/api.md`.
- **`Cannot find module '@mastra/core/agent'` or a missing export.** Install or align versions. Import from subpaths; v1's `@mastra/core` root exports only `Mastra` and `Config`.
- **`model: 'openai:gpt-...'` or a bare model name.** Use the router string `'openai/gpt-6.1-sol'` and verify IDs with `mastra-models`.
- **401 or "API key not found".** The provider env var is missing in this process. Check `.env` placement (app directory in monorepos) and the platform's variables.
- **Tool `execute: async ({ context })`.** Pre-v1 shape. Use `execute: async (inputData, context)`.
- **`context.runtimeContext` is undefined.** Renamed to `requestContext`.
- **`agent.generate(msg, { threadId, resourceId })` forgets history.** Use `memory: { thread, resource }` and keep both stable across calls.
- **`Memory requires a storage provider to function`.** Add `storage` to `new Mastra({...})` or to `new Memory({...})`.
- **Agent never calls its tools.** Tools not passed to `new Agent({ tools })`, or instructions never mention them.
- **`ValidationError` from a tool.** The returned value does not match `outputSchema` (validated since v1). Fix the output or set `outputValidation: 'warn'`.
- **`MastraError` before any LLM call.** `requestContextSchema` rejected the request context. Set the missing keys.
- **Workflow fails immediately.** Missing `.commit()`, or `createRunAsync` from old code (now `createRun`).
- **`getAgents is not a function`.** Plural getters are `list*` now (`listAgents`).
- **`ECONNREFUSED 127.0.0.1:5432`.** Database not running or wrong `DATABASE_URL`.
- **`duplicate key value violates unique constraint` on spans after upgrading.** Run `npx mastra migrate`.
- **`SERVER_UNREACHABLE` from `mastra api`.** Start `mastra dev` or pass `--url`.

---

## Output format

A finished troubleshooting delivery contains:

- The root cause in one or two sentences, tied to the exact error line
- The installed versions checked and the docs page used to verify the fix
- The code or config diff, using current APIs only
- Proof the fix works: the reproduction passing, `tsc --noEmit`, tests, or a Studio run
- For genuine defects: a drafted anonymized report and whether it was sent

---

## Reference files

- [`references/api.md`](references/api.md) - Error catalog by symptom, required configs, diagnostic commands, client SDK error handling.
- [`references/examples.md`](references/examples.md) - Worked fixes: ESM setup, outdated tool and memory calls, lost history, client retries.
- [`references/checklist.md`](references/checklist.md) - Diagnosis checklist.

**Live docs**

- https://mastra.ai/reference/client-js/error-handling
- https://mastra.ai/reference/client-js/mastra-client
- https://mastra.ai/reference/manual-install
- https://mastra.ai/reference/tools/create-tool
- https://mastra.ai/reference/memory/memory-class
- https://mastra.ai/reference/migrations/upgrade-to-v1/overview
- https://mastra.ai/docs/deployment/mastra-server
