# Agent skills API reference

Distilled from `https://mastra.ai/docs/skills.md`, `https://mastra.ai/docs/sandbox/skills.md`, `https://mastra.ai/reference/agents/createSkill.md`, `https://mastra.ai/reference/agents/getSkill.md`, `https://mastra.ai/reference/agents/listSkills.md`, and `https://mastra.ai/reference/workspace/workspace-class.md`. Verify against the installed version before relying on an option.

## Contents

- createSkill()
- Agent `skills` option
- agent.getSkill()
- agent.listSkills()
- Validation helpers
- Workspace skills options
- SKILL.md format rules
- Skill tools

---

## `createSkill(config)`

Import: `import { createSkill } from '@mastra/core/skills'`

| Parameter | Type | Notes |
|---|---|---|
| `name` | `string` | Required. Valid slug (lowercase, hyphens). Identifier used to activate the skill. |
| `description` | `string` | Required. Shown in the system message. Write when to use it. |
| `instructions` | `string` | Markdown loaded into the conversation on activation. |
| `references` | `Record<string, string>` | Filename to content. Readable through `skill_read`. |
| `license` | `string` | SPDX identifier. |
| `compatibility` | `unknown` | Free-form, per the Agent Skills spec. |
| `user-invocable` | `boolean` | Whether end users can invoke it directly. Default undefined (agent decides). |
| `metadata` | `Record<string, unknown>` | Arbitrary metadata. |

Returns an `InlineSkill` (implements `Skill`, plus `__inline: true` and `__referenceContents`). Synthetic path: `inline/<name>`. Throws `Error` with field details on invalid input, for example `Invalid skill "": name: Skill name cannot be empty`.

---

## Agent `skills` option

```typescript
skills: SkillInput[] | (({ requestContext, tracingContext }) => SkillInput[] | Promise<SkillInput[]>)
```

- A `SkillInput` is a `createSkill()` result or a string path to a `SKILL.md` directory (read through `LocalSkillSource`).
- The resolver runs once per `RequestContext`. During execution it runs inside a `resolve-skills` span. On `listSkills()` and server metadata reads `tracingContext.currentSpan` is `undefined`.
- Agent-level skills merge with workspace skills. Agent-level wins on name conflicts.

---

## `agent.getSkill(skillName, options?)`

| Parameter | Type | Notes |
|---|---|---|
| `skillName` | `string` | Name to look up. |
| `options.requestContext` | `RequestContext` | Passed to dynamic resolvers. |

Returns `Promise<Skill | null>`.

```typescript
interface Skill {
  name: string
  description: string
  instructions: string
  path: string
  source:
    | { type: 'external'; packagePath: string }
    | { type: 'local'; projectPath: string }
    | { type: 'managed'; mastraPath: string }
  references: string[]
  scripts: string[]
  assets: string[]
  license?: string
  compatibility?: unknown
  'user-invocable'?: boolean
  metadata?: Record<string, unknown>
}
```

Source types: a path with a `node_modules` segment is `external`, a path under `.mastra/skills` is `managed`, everything else (including `createSkill()`) is `local`.

---

## `agent.listSkills(options?)`

| Parameter | Type | Notes |
|---|---|---|
| `options.requestContext` | `RequestContext` | Passed to dynamic resolvers. |

Returns `Promise<SkillMetadata[]>`:

```typescript
interface SkillMetadata {
  name: string
  description: string
  path: string
  license?: string
  compatibility?: unknown
  'user-invocable'?: boolean
  metadata?: Record<string, unknown>
}
```

Returns the merged set. On a name conflict only the agent-level skill appears.

---

## Validation helpers

Import from `@mastra/core/skills`.

| Function | Input | Returns |
|---|---|---|
| `validateSkillContent({ content, directoryName })` | Raw `SKILL.md` text and the target directory name | `{ valid, errors, warnings }`. Does not throw. Applies load-time rules, including name equals directory. |
| `validateSkillMetadata({ metadata, directoryName })` | Parsed frontmatter object | Same result shape. |

Warnings are non-blocking (for example very long instructions).

---

## Workspace skills options

Import: `import { Workspace, LocalFilesystem } from '@mastra/core/workspace'`

| Option | Type | Notes |
|---|---|---|
| `skills` | `string[] \| ((context: SkillsContext) => string[] \| Promise<string[]>)` | Paths where `SKILL.md` files live. Globs supported. Resolved per execution when a function. |
| `skillSource` | `SkillSource` | Custom backend for discovery and reads. Replaces the filesystem and local disk. No fallback. `CompositeVersionedSkillSource` and `VersionedSkillSource` serve published versions from a blob store. |

Path forms for `skills`:

| Path | Behavior |
|---|---|
| `skills` | Scan each immediate subdirectory for `SKILL.md` |
| `skills/code-review` | Load one directory |
| `skills/code-review/SKILL.md` | Load one file |
| `./**/skills` | Find matching directories, then discover under each |
| `./**/SKILL.md` | Find and load matching files |

Glob traversal stops four directory levels below the glob base. Paths use the workspace filesystem when configured, otherwise the process working directory.

Instance accessor: `workspace.skills` (`WorkspaceSkills | undefined`). With a resolver-backed filesystem use `workspace.skills.getScoped({ requestContext })`. `list()` returns every same-named skill. `get(name)` applies tie-breaking (local, then managed, then external) and throws on an unresolvable tie. Pass the full path to `get()` to bypass tie-breaking.

---

## `SKILL.md` format rules

- YAML frontmatter requires `name` and `description`.
- `name`: matches the directory name, at most 64 characters, lowercase letters, numbers, or hyphens, no leading or trailing hyphen, no consecutive hyphens.
- Optional fields read by Mastra: `license`, `compatibility`, `user-invocable`, `metadata`.
- Body: the instructions returned on activation.
- Supporting folders: `references/` (read and searched), `scripts/`, `assets/` (read, not indexed).

When BM25 or vector search is configured on the workspace, `SKILL.md` instructions and reference files are indexed automatically. Scripts and assets are not.

---

## Skill tools

Added automatically when an agent has skills.

| Tool | Input highlights | Does |
|---|---|---|
| `skill` | Name or exact path | Returns instructions plus lists of references, scripts, assets |
| `skill_read` | Skill and file path | Reads a file (or part of it) under the skill |
| `skill_search` | Query, optional skill names, `topK` | Searches instructions and references |
