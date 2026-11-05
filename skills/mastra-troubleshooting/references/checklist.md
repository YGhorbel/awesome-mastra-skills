# Troubleshooting checklist

Work top to bottom. Stop when the root cause is found.

## Gather

- [ ] Full error text and stack trace captured
- [ ] `npm list @mastra/core mastra` and other `@mastra/*` versions recorded
- [ ] `node --version` is `22.13.0` or later
- [ ] Failure stage known: dev, build, start, deployed, or client

## Environment

- [ ] `"type": "module"` in `package.json`
- [ ] tsconfig uses `ES2022` target and module with `bundler` resolution
- [ ] All Mastra packages on matching versions
- [ ] Provider env vars present in the running process (and in the deploy target)
- [ ] `.env` sits in the app directory (monorepos)

## Code shape

- [ ] Imports use subpaths (`@mastra/core/agent`, `/tools`, `/workflows`)
- [ ] Model strings use `provider/model`
- [ ] Tools use `execute(inputData, context)`
- [ ] `requestContext`, not `runtimeContext`
- [ ] Memory passed as `memory: { thread, resource }`
- [ ] Agents, workflows, and storage registered on `new Mastra({...})` with `id`s
- [ ] Workflows call `.commit()` and use `createRun()`

## Reproduce and fix

- [ ] Reproduced in Studio or with `mastra api`
- [ ] Debug logging enabled when the cause is unclear
- [ ] Fix verified against installed docs or `.d.ts`, not memory
- [ ] Reproduction passes after the fix; `tsc --noEmit` and tests pass

## Report

- [ ] Decided whether it is a Mastra defect, a docs defect, or a user mistake
- [ ] Report anonymized: no source, logs, paths, private URLs, or secrets
- [ ] User agreed before sending to `https://mastra.ai/api/feedback` (unless they asked for the report)
- [ ] One report per issue; duplicates not resent
