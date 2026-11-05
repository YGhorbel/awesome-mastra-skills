---
name: mastra-agent-skills
description: "Give Mastra agents load-on-demand skills: inline skills with createSkill(), SKILL.md directories on disk, workspace-discovered skills, dynamic per-request skill sets, and programmatic access with getSkill() and listSkills(). Use this skill whenever the user wants a Mastra agent to follow reusable procedures without bloating its instructions, ship SKILL.md folders with an app, choose skills per user role or tenant, merge agent and workspace skills, or validate SKILL.md files before saving them. Triggers on Mastra skills, agent skills, createSkill, @mastra/core/skills, skills: [...], SKILL.md in a Mastra project, Workspace skills option, skillSource, skill_read, skill_search, agent.getSkill, agent.listSkills, validateSkillContent, Agent Skills specification. This is about skills inside a Mastra app, not about writing skills for Claude or other coding assistants."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Inline and filesystem skills for Mastra agents: createSkill, workspace skills, dynamic skill sets, getSkill and listSkills"
  display_order: 7
  docs: https://mastra.ai/docs/skills
---

# Mastra Agent Skills

Attach reusable, load-on-demand instructions to Mastra agents. The agent sees each skill's name and description, then loads the full instructions only when a request needs them.

---

## When to use

- Agent instructions are growing with procedures that only matter for some requests
- You want to package a procedure (review checklist, release steps, style guide) once and reuse it across agents
- Skills should come from `SKILL.md` folders in the repo, a package, or a blob store
- Different users, roles, or tenants should get different skill sets
- Application code needs to read or list an agent's skills
- An app writes `SKILL.md` files and must validate them first

## When NOT to use

- The guidance must apply on every turn (put it in `instructions`, see `mastra-agents`)
- The agent needs to execute code or call an API (write a tool, see `mastra-tools`)
- Skills declared as `skills/` files inside a file-based agent directory (use `mastra-file-based-agents`)
- Workspace filesystem, sandbox, and search setup beyond skills (use `mastra-workspace-sandbox`)
- Versioning and publishing skills from Studio (use `mastra-studio-editor`)
- Writing skills for Claude Code or another coding assistant (this skill covers Mastra runtime skills only)

---

## Required inputs

- The procedures to package, each with a one-line "use when" description
- Where skills live: inline in code, a directory on disk, or a shared workspace
- Whether the skill set varies per request (role, tenant, plan)
- Any supporting reference documents the skill should carry
- Whether workspace search (BM25 or vector) is configured, which improves `skill_search`

---

## The framework: three ways to supply skills

| Source | How | Scope |
|---|---|---|
| Inline | `createSkill({ name, description, instructions, references })` in the agent's `skills` array | One agent |
| Path | A string path to a `SKILL.md` directory in the agent's `skills` array | One agent |
| Workspace | `new Workspace({ skills: ['skills'] })`, discovered from the filesystem | Every agent using that workspace |

```typescript
import { Agent } from '@mastra/core/agent'
import { createSkill } from '@mastra/core/skills'

const codeReview = createSkill({
  name: 'code-review',
  description: 'Use when reviewing code changes.',
  instructions: `
    When reviewing code:
    1. Check for correctness and edge cases
    2. Verify style consistency
    3. Look for potential bugs
  `,
})

export const reviewer = new Agent({
  id: 'reviewer',
  name: 'Reviewer',
  model: 'openai/gpt-6.1-sol',
  instructions: 'You are a code review assistant.',
  skills: [codeReview, './skills/testing'],
})
```

### What the agent gets

Mastra lists each skill's name, description, path, and source type in the system message, and adds three tools:

| Tool | Does |
|---|---|
| `skill` | Loads a skill's instructions and lists its references, scripts, and assets |
| `skill_read` | Reads all or part of a file under the skill directory (or an inline `references` entry) |
| `skill_search` | Searches skill instructions and references (BM25 or vector when configured, text match otherwise) |

Loading is stateless. The instructions stay in the conversation as a tool result. The agent can call `skill` again after compaction.

### Precedence

- Agent-level skills (inline or path) beat workspace skills with the same name.
- Among same-named filesystem skills: local project paths, then `.mastra/skills` (managed), then `node_modules` (external).
- Two same-named skills with the same top source type throw an error. Rename one.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the types exported from `@mastra/core/skills`. Otherwise fetch `https://mastra.ai/docs/skills.md`, `https://mastra.ai/docs/sandbox/skills.md`, and `https://mastra.ai/reference/agents/createSkill.md`. Trust these over memory.
2. **Separate always-on from on-demand.** Keep identity and standing rules in `instructions`. Move conditional procedures into skills.
3. **Write the description first.** State when to load the skill ("Use when preparing a release"), not just what it contains.
4. **Choose the source.** Inline for code-owned skills and libraries. Path or workspace for `SKILL.md` folders that non-developers edit.
5. **Name correctly.** Lowercase letters, numbers, and hyphens, at most 64 characters, no leading, trailing, or double hyphens. For filesystem skills the name must match the directory.
6. **Make it dynamic if needed.** Pass `skills: ({ requestContext }) => [...]` on the agent, or a function for workspace `skills` paths.
7. **Validate stored skills.** Run `validateSkillContent()` before writing any `SKILL.md` your app generates.
8. **Test** in Studio: ask a question that should trigger the skill and confirm a `skill` tool call in the trace. Check `await agent.listSkills()` returns what you expect.

---

## Deep dive: filesystem and workspace skills

A `SKILL.md` directory follows the Agent Skills specification:

```markdown
---
name: code-review
description: Reviews code for bugs and readability issues
---

# Code review

Check the code for bugs, missing error handling, and unclear naming.
```

```plaintext
code-review/
  SKILL.md
  references/style-guide.md
  scripts/lint.ts
  assets/review-template.md
```

Frontmatter requires `name` and `description`. Mastra also reads `license`, `compatibility`, `user-invocable`, and `metadata`.

```typescript
import { LocalFilesystem, Workspace } from '@mastra/core/workspace'

export const workspace = new Workspace({
  filesystem: new LocalFilesystem({ basePath: './workspace' }),
  skills: ['skills'], // discovers ./workspace/skills/*/SKILL.md
})
```

Path forms: `skills` (scan subdirectories), `skills/code-review` (one directory), `skills/code-review/SKILL.md` (one file), `./**/skills` and `./**/SKILL.md` (globs, at most four levels below the glob base). Without a filesystem, paths resolve against the process working directory. A custom `skillSource` replaces both and never falls back.

---

## Failure patterns

- **Skill never loaded.** The description says what, not when. Rewrite it as a trigger ("Use when ...").
- **`createSkill()` throws `Invalid skill`.** Empty or non-slug `name`, or missing `description`. Fix the fields.
- **Filesystem skill rejected.** Frontmatter `name` does not match the directory name. Rename one.
- **"Can't choose between skills" error.** Two same-named skills share the top source type. Rename or move one.
- **Wrong skill wins.** An agent-level skill with the same name overrides the workspace one. That is by design. Rename if both are needed.
- **Skills missing in production.** Paths are relative to the working directory or workspace root and the deploy layout differs. Use paths under the workspace filesystem or inline skills.
- **Slow or traced-out resolver.** The dynamic `skills` function also runs on `listSkills()` and server metadata reads without a span. Keep it fast and guard `tracingContext?.currentSpan`.
- **Resolver-backed workspace returns no skills.** Direct `workspace.skills.list()` uses an empty request context. Use `workspace.skills.getScoped({ requestContext })`.
- **Everything in `SKILL.md`.** Long bodies cost tokens on every load. Move detail to `references/` and let the agent use `skill_read`.

---

## Output format

A finished skills delivery contains:

- Inline skills in `src/mastra/skills/<name>.ts` exporting `createSkill(...)`, or `SKILL.md` directories under the workspace or project skills path
- The agent (or workspace) wired with `skills`
- A dynamic resolver with a fallback set when skills vary per request
- `validateSkillContent()` at any boundary that writes `SKILL.md`
- Evidence: a trace showing a `skill` tool call, or a test on `agent.getSkill()`/`listSkills()`

---

## Reference files

- [`references/api.md`](references/api.md) - `createSkill()`, the `skills` agent option, `getSkill()`, `listSkills()`, validation helpers, workspace `skills` and `skillSource`, `SKILL.md` format rules.
- [`references/examples.md`](references/examples.md) - Inline skill with references, role-based dynamic skills, workspace skills shared by agents, validating uploaded skills.
- [`references/checklist.md`](references/checklist.md) - Checklist for shipping agent skills.

**Live docs**

- https://mastra.ai/docs/skills
- https://mastra.ai/docs/sandbox/skills
- https://mastra.ai/reference/agents/createSkill
- https://mastra.ai/reference/agents/getSkill
- https://mastra.ai/reference/agents/listSkills
- https://mastra.ai/reference/workspace/workspace-class
- https://agentskills.io/specification
