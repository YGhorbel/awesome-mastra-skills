---
name: mastra-file-based-agents
description: "Define Mastra agents by file convention instead of code: an agent directory under src/mastra/agents with config.ts (agentConfig), instructions.md or instructions.ts, and tools/, skills/, subagents/, processors/, scorers/, schedules/, memory.ts, workspace.ts, plus project files like storage.ts, logger.ts, observability.ts, server.ts, studio.ts, and src/mastra/workflows. Use this skill whenever the user wants to create an agent as a folder, add a tool or skill by dropping in a file, declare subagents or cron schedules as files, debug why a file-based agent is not discovered, or resolve precedence between config.ts and sibling files. Triggers on file-based agents, agentConfig, agentInstructions, defineSchedule, config.ts, instructions.md, src/mastra/agents folder, subagents directory, file routing, mastra dev discovery, mastra build discovery. Also triggers when a project has agent folders but no new Agent() calls."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Agents as directories: config.ts, instructions.md, tools/, skills/, subagents/, schedules/, and precedence rules"
  display_order: 8
  docs: https://mastra.ai/reference/file-based-agents/config
---

# Mastra File-Based Agents

Define an agent as a directory. Mastra discovers the files under `src/mastra/` during `mastra dev` and `mastra build`, assembles a normal `Agent`, and registers it.

---

## When to use

- Creating an agent by convention (`src/mastra/agents/<name>/config.ts` plus `instructions.md`)
- Adding tools, skills, processors, scorers, or schedules by adding files
- Declaring specialist subagents as nested directories
- Setting project-wide storage, logger, observability, server, or Studio config from single files
- Debugging a file-based agent that does not show up, or a setting that does not take effect
- Converting a code-defined agent to the file convention, or the reverse

## When NOT to use

- Constructing agents with `new Agent({...})` in code (use `mastra-agents`)
- Tool schemas and execution options (use `mastra-tools`)
- Delegation hooks, message filtering, and rubric loops for subagents (use `mastra-multi-agent`)
- The `SKILL.md` package format and workspace skill discovery (use `mastra-agent-skills`)
- Runtime schedules created with `mastra.schedules.create()` (use `mastra-schedules`)
- Memory, storage, or workspace provider details (use `mastra-memory`, `mastra-storage`, `mastra-workspace-sandbox`)
- Apps that import the `mastra` instance through a framework or server adapter (use `mastra-framework-integration` or `mastra-server` and register in code)

---

## Required inputs

- The agent directory name (it becomes the default `id` and `name`)
- The model (a `provider/model` string, verified with `mastra-models`)
- The always-on prompt, and whether it needs code (`instructions.ts`) or not (`instructions.md`)
- Tools, skills, subagents, processors, scorers, and schedules the agent needs
- How the app runs: through `mastra dev`/`mastra build` (discovery works) or as a library (it does not)

---

## The framework: a directory is an agent

```text
src/mastra/
  storage.ts                 # project store (optional)
  agents/
    weather/
      config.ts              # required: model and runtime options
      instructions.md        # or instructions.ts: always-on prompt
      tools/get_weather.ts   # tool key: get_weather
      skills/units.md        # skill name: units
      memory.ts              # optional Memory instance
      workspace.ts           # optional; a default workspace exists
      workspace/             # seed files copied at build time
      processors/input/      # input processors
      processors/output/     # output processors
      scorers/relevance.ts   # scorer key: relevance
      schedules/daily.ts     # schedule id: daily (root agents only)
      subagents/
        researcher/          # its own config.ts, instructions.md, tools/ ...
  workflows/daily-report.ts  # project-level workflow (default export)
```

```typescript
// src/mastra/agents/weather/config.ts
import { agentConfig } from '@mastra/core/agent'

export default agentConfig({
  model: 'openai/gpt-6.1-sol',
})
```

```markdown
<!-- src/mastra/agents/weather/instructions.md -->
You are a helpful weather assistant. Answer questions about current conditions and forecasts.
```

`model` is the only required `agentConfig()` field. `agentConfig()` accepts `Agent` constructor options. A missing model or missing instructions fails the build.

### Precedence summary

| Domain | Winner |
|---|---|
| Instructions | Function `config.instructions`, then `instructions.ts`, then `instructions.md`, then static `config.instructions` |
| Tools, skills, scorers | Merge. `config.*` wins on key collisions. A function-valued `config.*` ignores discovered files. |
| Processors | `config` processors run first, then discovered files. A function-valued `config.*Processors` ignores discovered files. |
| Memory, workspace | `config.memory` over `memory.ts`. `config.workspace` over `workspace.ts`. |
| Subagents | `config.agents` entry wins over a same-id directory. A function-valued `config.agents` ignores discovered subagents. |
| Project files | Code-registered config in `new Mastra({...})` wins over `storage.ts`, `logger.ts`, `observability.ts`, `server.ts`, `studio.ts`, and file workflows. |

If `config.ts` exports `new Agent({...})`, Mastra uses it as-is and ignores `subagents/`, `processors/`, and `schedules/` with a warning.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the types for `agentConfig`, `agentInstructions`, and `defineSchedule` from `@mastra/core/agent`. Otherwise fetch `https://mastra.ai/reference/file-based-agents/config.md` and the sibling pages under `https://mastra.ai/reference/file-based-agents/`. Trust these over memory.
2. **Confirm discovery runs.** The app must start with `mastra dev` or `mastra build`. Server adapters and direct imports of `mastra` skip discovery.
3. **Create the directory** `src/mastra/agents/<name>/` with `config.ts` and `instructions.md`.
4. **Add tools** as one file per tool in `tools/`, each default-exporting `createTool(...)`. Filename equals tool key. No nested folders.
5. **Add skills** as flat `.md` files, `SKILL.md` directories, or modules exporting `createSkill(...)`. Each needs a `description`.
6. **Add subagents** under `subagents/<id>/`. Each `config.ts` needs a non-empty `description`. Nest at most three levels.
7. **Add memory, workspace, processors, scorers, schedules** only when needed. Schedules need storage and a long-running host.
8. **Run** `npx mastra dev`, open Studio, and confirm the agent, its tools, skills, and subagents appear. Read build warnings: they name precedence conflicts.

---

## Deep dive: schedules as files

```typescript
// src/mastra/agents/support/schedules/heartbeat.ts  -> id: heartbeat
import { defineSchedule } from '@mastra/core/agent'

export default defineSchedule({
  cron: '*/5 * * * *',
  prompt: 'Check system health and report any failures.',
})
```

```markdown
---
cron: '0 9 * * 1'
timezone: 'America/New_York'
---

Summarize the past week's tickets and post the digest to the team channel.
```

- Set exactly one of `prompt` or `handler`. A handler returns overrides (for example `{ prompt }`) or `null` to skip the fire.
- Quote the cron in Markdown frontmatter. A leading `*` is a YAML alias.
- The id is the path under `schedules/` without the extension. Renaming a file deletes one schedule and creates another.
- Root agents only. A `schedules/` directory under `subagents/` is a build error.
- Fire one on demand: `curl -X POST http://localhost:4111/api/schedules/<scheduleId>/run` (copy the encoded id from `GET /api/schedules`).

---

## Failure patterns

- **Agent missing from Studio.** The app imports `mastra` directly or runs through a server adapter. Start with `mastra dev`/`mastra build`, or register the agent in code.
- **Build fails naming the agent directory.** No `instructions.md`, `instructions.ts`, or `config.instructions`. Add one.
- **Build fails on a model.** `agentConfig()` has no `model`. Add it.
- **Tool not found.** The file is in a subfolder of `tools/`, lacks a default export, or is a `*.test.ts`. Use flat files named after the action.
- **Discovered tools or skills ignored.** `config.tools` or `config.skills` is a function. Use a static record or move everything into the function.
- **Subagent build error.** Missing `description`, an id that collides with a parent tool key, or a duplicate id. Fix the subagent `config.ts` or rename.
- **Subagent cannot use the parent's tools or memory.** Subagents are isolated by design. Share dependencies in code and assign them in each `config.ts`.
- **Agent has no memory.** Neither `memory.ts` nor `config.memory` exists. Add `memory.ts` exporting `new Memory()`.
- **Unwanted shell access.** File-based agents get a default workspace with `LocalFilesystem` and `LocalSandbox`. Set `workspace: undefined` in `config.ts` to disable it.
- **Schedules never fire.** In-memory storage, a serverless host, or a schedule under a subagent. Add `storage.ts`, use a long-running process, and put schedules on the root agent.
- **Edits not live in production.** `instructions.md` is inlined at build time. Rebuild and redeploy.

---

## Output format

A finished file-based agent delivery contains:

- `src/mastra/agents/<name>/config.ts` and `instructions.md` (or `instructions.ts`)
- One file per tool in `tools/`, and skills, subagents, or schedules as needed
- `src/mastra/storage.ts` when memory or schedules must persist
- Required env vars in `.env.example`
- Evidence: `npx mastra dev` starts with no precedence warnings you did not intend, and the agent answers in Studio

---

## Reference files

- [`references/api.md`](references/api.md) - Every file convention: exports, naming, precedence, and build-time behavior.
- [`references/examples.md`](references/examples.md) - Minimal agent, agent with tools, skills, and memory, research supervisor with subagents, scheduled support agent.
- [`references/checklist.md`](references/checklist.md) - Checklist for file-based agents.

**Live docs**

- https://mastra.ai/docs/develop
- https://mastra.ai/reference/file-based-agents/config
- https://mastra.ai/reference/file-based-agents/instructions
- https://mastra.ai/reference/file-based-agents/tools
- https://mastra.ai/reference/file-based-agents/skills
- https://mastra.ai/reference/file-based-agents/subagents
- https://mastra.ai/reference/file-based-agents/schedules
- https://mastra.ai/reference/file-based-agents/workspace
