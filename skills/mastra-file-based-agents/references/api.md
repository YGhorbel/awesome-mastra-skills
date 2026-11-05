# File-based agents API reference

Distilled from the pages under `https://mastra.ai/reference/file-based-agents/` and `https://mastra.ai/docs/develop.md`. Verify against the installed version before relying on a convention.

## Contents

- Discovery
- Agent directory files
- config.ts
- instructions.md and instructions.ts
- tools/
- skills/
- subagents/
- memory.ts
- workspace.ts and workspace/
- processors/
- scorers/
- schedules/
- Project-level files

---

## Discovery

- Runs only under `mastra dev` and `mastra build`. The bundler reads supported files under `src/mastra/`, imports TS and JS modules, reads Markdown instructions and skills, copies workspace seed files, and registers everything on the Mastra app.
- Skips symlinks, test files (`*.test.ts`, `*.spec.ts`), and directories that are not agent directories.
- Server adapters and direct imports of the `mastra` instance do not run discovery. Register those primitives in code.
- After discovery a file-based agent is a normal `Agent`: same runtime for the Agent API, Studio, workflows, and app code.

---

## Agent directory files

| Path | Export | Registers as |
|---|---|---|
| `config.ts` | `default agentConfig({...})` (or `new Agent({...})`) | Agent options. Directory name is the default `id` and `name`. |
| `instructions.md` | Markdown body | Always-on prompt, inlined at build time |
| `instructions.ts` | `default agentInstructions(...)` | Always-on prompt, bundled as code |
| `tools/<key>.ts` | `default createTool(...)` | Tool `<key>` |
| `skills/<name>.md`, `skills/<name>/SKILL.md`, `skills/<name>.ts` | Frontmatter skill, packaged skill, or `default createSkill(...)` | Skill `<name>` |
| `subagents/<id>/` | Its own agent directory | Entry in the parent's `agents` map |
| `memory.ts` | `default new Memory(...)` | `memory` |
| `workspace.ts` | `default new Workspace(...)` | `workspace` |
| `workspace/` | Files | Seed files mirrored into the agent workspace |
| `processors/input/<key>.ts` | `default` a `Processor` | Input processor |
| `processors/output/<key>.ts` | `default` a `Processor` | Output processor |
| `scorers/<key>.ts` | `default` a scorer or `{ scorer, sampling }` | Scorer `<key>` |
| `schedules/<path>.ts` or `.md` | `default defineSchedule(...)` or frontmatter | Schedule id `<path>` |

---

## config.ts

Import: `import { agentConfig } from '@mastra/core/agent'`

- `model` is required. Missing model fails the build.
- Accepts `Agent` constructor options (`description`, `defaultOptions`, `maxRetries`, `scorers`, and so on). `id`, `name`, and sibling-file fields may be supplied by convention.
- Override `id` or `name` when the routing key and display name should differ.
- Subagent `config.ts` must set a non-empty `description`.
- `workspace: undefined` disables the default workspace.
- Exporting `new Agent({...})` uses that agent verbatim. Then `subagents/`, `processors/`, and `schedules/` are ignored with a warning.

---

## instructions.md and instructions.ts

Import (TS): `import { agentInstructions } from '@mastra/core/agent'`

- `instructions.ts` default-exports a string, a system message, a non-empty array of strings or system messages, or a function returning one. `agentInstructions()` only types the export.
- A function receives `{ requestContext, mastra }` on every turn and may be async. `mastra` is optional in the type. Guard it (`mastra?.getStorage()`).
- `instructions.md` is inlined into generated code at build time. `instructions.ts` is imported and bundled. Neither is read from disk at runtime.
- Precedence: function `config.instructions` > `instructions.ts` > `instructions.md` > static `config.instructions`. None present fails the build. Multiple sources log a warning.

---

## tools/

- Only `.ts` and `.js` files directly under `tools/`. Nested directories are not discovered.
- Each file default-exports a `createTool()` result. Filename without extension is the tool key.
- Name files after the action (`get_weather.ts`, `calendar_create_event.ts`). Avoid `helper.ts`, `utils.ts`.
- Merges with `config.tools`. `config.tools` wins on collisions (warning). A function `config.tools` ignores discovered tools (warning).
- Tool code runs in the app or server process, not in the workspace sandbox.

---

## skills/

Three formats:

| Format | Rules |
|---|---|
| Flat Markdown (`skills/units.md`) | Frontmatter `description` required. Filename is the name unless frontmatter `name` is set. |
| Packaged directory (`skills/code-review/SKILL.md`) | `description` required. Files directly under `references/` are bundled, keyed by filename. Symlinks skipped. |
| Module (`skills/x.ts`) | Default-exports `createSkill(...)`. |

Skills are bundled at build time. Merges with `config.skills`. `config.skills` wins on name collisions. A function `config.skills` ignores discovered skills.

---

## subagents/

- One directory per subagent, each a full agent directory. The parent model sees a delegation tool named after the directory.
- `description` required in the subagent's `config.ts`. Missing description fails the build (unless the parent exports `new Agent()`, in which case `subagents/` is ignored).
- Isolated: no inherited tools, skills, workspace, memory, processors, or subagents.
- Nesting: up to three levels below the top-level agent. Deeper `subagents/` directories are ignored with a warning.
- Build errors: subagent id equals a parent tool key, or duplicate subagent ids under one parent.
- `config.agents` entry with the same id wins (warning). Function `config.agents` ignores discovered subagents.
- Subagents cannot declare `schedules/`.

---

## memory.ts

- Default-exports a `Memory` instance (`import { Memory } from '@mastra/memory'`).
- Without `memory.ts` or `config.memory`, the agent has no memory.
- `config.memory` wins. Memory data uses the storage configured on the Mastra instance (for example `storage.ts`).

---

## workspace.ts and workspace/

- Without `workspace.ts`, a discovered agent gets a default `Workspace` with `LocalFilesystem` and `LocalSandbox` rooted at its bundled workspace directory: file tools and shell tools by default. Subagents get nested workspace directories.
- `workspace.ts` default-exports a `Workspace` (`@mastra/core/workspace`).
- `config.workspace` wins over `workspace.ts`, including when set to `undefined`.
- `workspace/` files are mirrored into the runtime workspace at build time. Symlinks skipped.

---

## processors/

- `processors/input/*` run before the model. `processors/output/*` run after.
- Each file default-exports one `Processor`. Filename is the key.
- Order: `config.inputProcessors` then `processors/input/*` then model; model then `config.outputProcessors` then `processors/output/*`.
- A function-valued `config.*Processors` ignores discovered processors of that type.

---

## scorers/

- Each file default-exports a `MastraScorer` or `{ scorer, sampling }` (for example `sampling: { type: 'ratio', rate: 0.5 }`). Filename is the key.
- Merges with `config.scorers`. Precedence: function `config.scorers`, then record `config.scorers`, then discovered files.

---

## schedules/

Import: `import { defineSchedule } from '@mastra/core/agent'` (also exported from `@mastra/core/schedules`).

| Option | Type | Notes |
|---|---|---|
| `cron` | `string` | Required. 5, 6, or 7 parts. |
| `prompt` | `string` | Prompt mode. Set this or `handler`. |
| `handler` | `(ctx) => result \| null \| undefined \| void` (async allowed) | Handler mode. `ctx` includes `mastra` and `agentId`. Return overrides such as `{ prompt, threadId, resourceId }`, or `null` to skip. Returning nothing fails the fire. |
| `timezone` | `string` | IANA zone. Defaults to the host timezone. |
| `name` | `string` | Label in Studio, filterable with `mastra.schedules.list({ name })`. |
| `threadId` | `string` | Send the fire as a signal into a thread. Requires `resourceId`. |
| `resourceId` | `string` | Thread owner. |
| `signalType` | `'user' \| 'state' \| 'reactive' \| 'notification' \| 'user-message' \| 'system-reminder'` | Threaded only. Default `'notification'`. |
| `tagName` | `string` | Signal XML tag. Default `'schedule'`. |
| `attributes` | `Record<string, string \| number \| boolean \| null>` | Attributes on the signal tag. |
| `providerOptions` | `Record<string, unknown>` | JSON-safe. |
| `ifActive` / `ifIdle` | Delivery policies | Threaded only. |
| `status` | `'active' \| 'paused'` | Applies on first create only. Default `'active'`. |
| `metadata` | `Record<string, unknown>` | JSON-safe. |

Markdown schedules use frontmatter for every option except `handler` and `prompt` (the body is the prompt). Unknown frontmatter fields fail the build. `x.ts` and `x.md` with the same id is a build error.

Lifecycle: synced into schedule storage at startup and on later agent registration. New file creates, edited `cron`/`timezone` patches, deleted file removes. API pauses survive redeploys. Requires storage and a long-running host. Stored ids are namespaced and URL-encoded (`fsa_support__billing%2Fsweep`).

---

## Project-level files (directly under `src/mastra/`)

| File | Default export | Notes |
|---|---|---|
| `storage.ts` | A store, for example `new LibSQLStore({ id, url })` from `@mastra/libsql` | Replaces the in-memory store. Registered before agents and workflows. |
| `logger.ts` | A logger, for example `new PinoLogger({ name, level })` from `@mastra/loggers` | Ignored if `new Mastra({ logger })` is set (including `false`). |
| `observability.ts` | `new Observability({ configs })` from `@mastra/observability` | Code registration wins. |
| `server.ts` | A `ServerConfig` object (`satisfies ServerConfig` from `@mastra/core/server`) | `port`, `host`, `cors`, `apiRoutes`, `build`. Code registration wins. |
| `studio.ts` | A `StudioConfig` object with `auth` (and RBAC or FGA) | Code registration wins. |
| `workflows/<key>.ts` | `default createWorkflow(...).commit()` | Filename is the workflow key. Files without a default export are skipped. Code-registered workflows win on collision. |
