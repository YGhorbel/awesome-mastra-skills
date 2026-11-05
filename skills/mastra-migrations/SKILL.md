---
name: mastra-migrations
description: "Upgrade Mastra projects safely: the 0.x to v1 migration (subpath imports, createTool execute signature, RequestContext, list-style APIs, memory defaults and the memory option, storage pagination and schema migrations, Observability exporters, CLI changes), the @mastra/codemod codemods, and the targeted guides for VNext to standard APIs, AI SDK v4 to v5, AgentNetwork and .network() to supervisor agents, @mastra/mcp v1 to v2, and Mastra Cloud to Mastra Platform. Use this skill whenever the user bumps @mastra/core, sees breaking changes after npm update, asks what changed between versions, wants to run codemods, or must move off a deprecated API. Triggers on upgrade Mastra, migrate to v1, npx @mastra/codemod, breaking changes, RuntimeContext to RequestContext, getAgents to listAgents, createRunAsync, generateVNext, streamVNext, generateLegacy, telemetry to observability, CloudExporter, DefaultExporter, mastra migrate, .network() deprecated, Mastra Cloud migration, mcp v2."
license: Apache-2.0
metadata:
  category: getting-started
  catalog_summary: "v1 upgrade guide, codemods, AI SDK v5, supervisor agents, MCP v2, and Mastra Cloud to Platform migrations"
  display_order: 5
  docs: https://mastra.ai/reference/migrations/upgrade-to-v1/overview
---

# Mastra Migrations

Move a Mastra project from an older version or deprecated API to the current one, using official guides and codemods, without breaking runtime behavior.

---

## When to use

- Upgrading a project from Mastra 0.x to v1
- Bumping `@mastra/*` minor versions and hitting renamed or removed APIs
- Running `@mastra/codemod` transforms
- Moving from `generateVNext`/`streamVNext` or legacy AI SDK v4 models
- Replacing `AgentNetwork` or `.network()` with supervisor agents
- Upgrading `@mastra/mcp` from 1.x to 2.x
- Moving from Mastra Cloud to Mastra Platform
- Running storage schema migrations after an upgrade

## When NOT to use

- A single error with an unknown cause (use `mastra-troubleshooting`)
- Deploying after the upgrade (use `mastra-deployment` or `mastra-platform`)
- Writing new agents, tools, or workflows on the current API (use `mastra-agents`, `mastra-tools`, `mastra-workflows`)
- Supervisor agent design beyond the migration steps (use `mastra-multi-agent`)
- MCP server and client usage on v2 (use `mastra-mcp`)
- Configuring observability exporters in depth (use `mastra-observability`)

---

## Required inputs

- Current versions: `npm list @mastra/core mastra` and every `@mastra/*` package
- Target version (default: latest v1)
- Package manager and repo layout (monorepos must update every package together)
- Storage backend in use (PostgreSQL and LibSQL need database steps)
- Whether the project used `telemetry:`, Mastra Cloud, `.network()`, or `@mastra/mcp`
- A clean git state and a passing test baseline

---

## The framework: upgrade in one pass, verify in layers

1. **All packages move together.** Every `@mastra/*` package and `mastra` go to `latest` in one change.
2. **Codemods first, hand edits second.** Codemods handle mechanical renames. The guide pages cover behavior changes codemods cannot.
3. **Behavior changes need explicit config.** v1 changed defaults (memory scope, `lastMessages`, semantic recall, title generation, input validation). Restore old behavior on purpose, not by accident.
4. **Data migrations are separate.** SQL or `mastra migrate` steps run against the database.
5. **Observability must migrate in the same change.** v1 ignores `telemetry:` silently, so traces stop with no error.

```bash
npm install @mastra/core@latest @mastra/loggers@latest @mastra/memory@latest mastra@latest
npx @mastra/codemod@latest v1
```

Node.js `22.13.0` or later is required for v1. Update to the latest 0.x before jumping to v1.

The highest-impact v1 change, the tool signature:

```diff
createTool({
    id: 'weather-tool',
-   execute: async ({ context, requestContext, mastra }) => {
-     const location = context.location;
-     const userTier = requestContext.get('userTier');
-     return getWeather(location, userTier);
-   },
+   execute: async (inputData, context) => {
+     const location = inputData.location;
+     const userTier = context?.requestContext?.get('userTier');
+     return getWeather(location, userTier);
+   },
  });
```

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` for the installed version. Fetch `https://mastra.ai/reference/migrations/upgrade-to-v1/overview.md` and the area pages you need, and the package changelog (`https://github.com/mastra-ai/mastra/blob/main/packages/core/CHANGELOG.md`) for minor bumps. Trust these over memory.
2. **Baseline.** Commit, record versions, run `npx tsc --noEmit` and tests. Back up the database.
3. **Inventory usage.** Grep for the APIs in `references/v1-changes.md` (`RuntimeContext`, `getAgents`, `createRunAsync`, `telemetry:`, `threadId:`, `offset`, `generateVNext`, `.network(`, `@mastra/speech-`).
4. **Update packages together.** Use `@latest` for every Mastra package. Update Node if needed.
5. **Run codemods.** `npx @mastra/codemod@latest v1` for everything, or one transform at a time (`npx @mastra/codemod@latest v1/runtime-context .`). Review the diff.
6. **Apply hand edits.** Work the checklist in order: high impact (tools, imports, pagination, observability), medium, low.
7. **Decide on behavior defaults.** Set memory `scope`, `lastMessages`, `semanticRecall`, `generateTitle` explicitly if the app relied on 0.x defaults.
8. **Migrate data.** Run the SQL for scorer columns and JSONB if applicable, and `npx mastra migrate` for duplicate spans.
9. **Verify.** `npx tsc --noEmit`, tests, `mastra dev`, a Studio run of each agent and workflow, and traces visible in Studio or the platform.
10. **Update deploy commands.** Replace `mastra server deploy` and `mastra studio deploy` with `mastra deploy` (see `mastra-platform`).

---

## Deep dive: other migration guides

| Guide | From | To | Key moves |
|---|---|---|---|
| `vnext-to-standard-apis` | `generateVNext`/`streamVNext` (0.20) | `generate`/`stream` | Old `generate`/`stream` became `generateLegacy`/`streamLegacy` for AI SDK v4 models; standard methods need v5 models |
| `ai-sdk-v4-to-v5` | AI SDK v4 | AI SDK v5 | No DB migration; stored messages convert on the fly. Use `convertMessages(...).to('AIV5.UI')`. Keep backups, v5 data does not downgrade |
| `agentnetwork` | `AgentNetwork` | `Agent` with `agents` and memory | Memory is required |
| `network-to-supervisor` | `.network()` (deprecated) | `stream()`/`generate()` with `maxSteps` | Clear supervisor instructions, subagent descriptions, `delegation` hooks |
| `mcp-v2` | `@mastra/mcp` 1.x | 2.x (MCP 2026-07-28 only) | Needs `@mastra/core` 1.76+. Elicitation becomes `suspend()`/`resumeData`. SSE transport removed. Stay on 1.x to serve pre-2026 clients |
| `mastra-cloud` | Mastra Cloud | Mastra Platform | New tokens (`mastra auth tokens create`), export Cloud Store, `observability:` with `MastraPlatformExporter`, then deploy |

Details and code are in `references/other-guides.md`.

---

## Failure patterns

- **Upgrading one package at a time.** Peer mismatches cause type and runtime errors. Bump all Mastra packages in one change.
- **Skipping the latest 0.x.** Jumping straight to v1 hides intermediate deprecations. Update to latest 0.x first.
- **Traces vanish after upgrade, no error.** `telemetry:` is ignored. Install `@mastra/observability` and configure `observability: new Observability({...})`.
- **Agent now remembers across conversations.** Memory scope default changed to `resource`. Set `scope: 'thread'` if needed.
- **Only 10 messages of history.** `lastMessages` default dropped from 40 to 10.
- **History lost entirely.** `threadId`/`resourceId` call options were removed. Use `memory: { thread, resource }`.
- **Storage init fails on a unique constraint.** Duplicate spans. Run `npx mastra migrate`.
- **Scorer request context data missing.** Run the `runtimeContext` to `requestContext` column SQL.
- **`Tool output validation failed`.** v1 validates `outputSchema`. Fix outputs or set `outputValidation: 'warn'`.
- **Workflow start rejects input.** Inputs validate by default now.
- **`mastra dev --port` or `mastra build --env` rejected.** Use `server.port` and `mastra start --env`.
- **Codemod run on uncommitted work.** Hard to review. Commit first, run one transform per commit for large repos.
- **Old docs for `format: 'aisdk'`.** The `format` parameter was removed in v1.
- **Platform deploy fails with `MASTRA_CORE_TOO_OLD`.** The environment pipeline needs `@mastra/core >= 1.44`.

---

## Output format

A finished migration delivery contains:

- Version table: before and after for every Mastra package, plus Node
- The codemods run and the hand edits made, grouped by area
- Explicit config for any v1 default the app depended on
- Database steps run (SQL or `mastra migrate`) and their result
- Verification: `tsc --noEmit`, tests, a Studio run, traces visible
- Remaining warnings or deprecations to address later

---

## Reference files

- [`references/api.md`](references/api.md) - Codemod catalog, upgrade commands, rename map by area.
- [`references/v1-changes.md`](references/v1-changes.md) - v1 breaking changes by area with before and after code.
- [`references/other-guides.md`](references/other-guides.md) - VNext, AI SDK v5, supervisor agents, MCP v2, Mastra Cloud.
- [`references/examples.md`](references/examples.md) - Full v1 upgrade run, observability migration, memory defaults, `.network()` to supervisor.
- [`references/checklist.md`](references/checklist.md) - Pre- and post-migration checklist.

**Live docs**

- https://mastra.ai/reference/migrations/upgrade-to-v1/overview
- https://mastra.ai/reference/migrations/upgrade-to-v1/tools
- https://mastra.ai/reference/migrations/upgrade-to-v1/memory
- https://mastra.ai/reference/migrations/upgrade-to-v1/storage
- https://mastra.ai/reference/migrations/upgrade-to-v1/tracing
- https://mastra.ai/reference/migrations/vnext-to-standard-apis
- https://mastra.ai/reference/migrations/ai-sdk-v4-to-v5
- https://mastra.ai/reference/migrations/network-to-supervisor
- https://mastra.ai/reference/migrations/mcp-v2
- https://mastra.ai/reference/migrations/mastra-cloud
