# File-based agent checklist

Run this before calling a file-based agent done.

## Discovery

- [ ] The app starts with `mastra dev` and builds with `mastra build` (no server adapter or direct import path relies on discovery)
- [ ] The agent directory sits directly under `src/mastra/agents/`
- [ ] Directory name is a stable id (renaming changes the agent id, thread links, and schedule ids)

## Required files

- [ ] `config.ts` default-exports `agentConfig({ model })` with a verified model string
- [ ] Exactly one instructions source: `instructions.md`, `instructions.ts`, or `config.instructions`
- [ ] Provider env vars listed in `.env.example`

## Capabilities

- [ ] One flat file per tool in `tools/`, each default-exporting `createTool(...)`, named after the action
- [ ] Every skill has a `description` that says when to load it
- [ ] Every subagent `config.ts` has a non-empty `description`
- [ ] No subagent id collides with a parent tool key
- [ ] Subagents nest no deeper than three levels
- [ ] Shared dependencies are defined in code and assigned per agent (subagents inherit nothing)
- [ ] `memory.ts` present if the agent must remember conversations
- [ ] Default workspace kept only if the agent should have file and shell tools; otherwise `workspace: undefined`

## Precedence

- [ ] No unintended precedence warnings in the `mastra dev` output
- [ ] `config.tools`, `config.skills`, `config.scorers`, `config.agents`, and processor arrays are static when discovered files must merge

## Schedules

- [ ] Schedules live on root agents only
- [ ] Each schedule sets exactly one of `prompt` or `handler`
- [ ] Markdown crons are quoted and `timezone` is explicit
- [ ] `storage.ts` (or code-registered storage) is configured
- [ ] Host keeps the process alive, or an external cron calls the run endpoint

## Verification

- [ ] Agent, tools, skills, and subagents visible in Studio
- [ ] A test conversation exercises each tool and at least one delegation
- [ ] Production build redeployed after instruction edits (Markdown is inlined at build time)
