# Migration checklist

## Before

- [ ] Clean git branch; current versions recorded (`npm list @mastra/core mastra`)
- [ ] Tests and `npx tsc --noEmit` pass on the old version
- [ ] Database backed up
- [ ] On the latest 0.x before moving to v1
- [ ] Node.js `22.13.0` or later everywhere (dev, CI, production)
- [ ] Target version's guide pages and changelog read

## Upgrade

- [ ] Every `@mastra/*` package and `mastra` updated in one change (all workspaces in a monorepo)
- [ ] Codemods run (`npx @mastra/codemod@latest v1` or individual transforms) and the diff reviewed
- [ ] High impact: tool signatures, subpath imports, `page/perPage`, `observability:` config
- [ ] Medium impact: `RequestContext`, `list*` storage methods, getters, memory scope, named vector args, `format` removed, `agent.voice`, `spanOutputProcessors`
- [ ] Low impact: `separatorPosition`, `createRun`, `@mastra/voice-*`, `runEvals`/`getScorerById`, CLI flags, client `List*` types, `retryCount`, `exportTracingEvent`
- [ ] `threadId`/`resourceId` moved to `memory: { thread, resource }`
- [ ] Every storage, vector, agent, workflow, processor, scorer, tool has an `id`

## Behavior

- [ ] Memory `lastMessages`, `semanticRecall`, `generateTitle`, and `scope` set explicitly where the app relied on 0.x defaults
- [ ] Tool outputs match `outputSchema` (now enforced)
- [ ] Workflow inputs match `inputSchema` (now validated)
- [ ] Branch outputs handled as optional

## Data

- [ ] `npx mastra migrate` run if spans exist from before v1
- [ ] Scorer `runtimeContext` column SQL run (pg or libsql with score data)
- [ ] JSONB conversion run on PostgreSQL (recommended)

## Verify

- [ ] `npx tsc --noEmit` and tests pass
- [ ] `mastra dev` starts; every agent and workflow runs in Studio
- [ ] Traces visible in Studio or on the platform
- [ ] Scripts and CI use `mastra start --env`, `server.port`, and `mastra deploy`
- [ ] OpenAPI consumers point at `/api/openapi.json`
- [ ] Remaining deprecation warnings listed for follow-up
