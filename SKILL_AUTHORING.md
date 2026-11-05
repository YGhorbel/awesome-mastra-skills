# Skill Authoring Guide

Every skill in this repo follows one structure. A reader picks up any skill and knows where to find the trigger, the mental model, the workflow, and the exact APIs. Uniformity is the point.

This structure is adapted from the [RampStack skills](https://github.com/rampstackco/claude-skills) conventions and the [Agent Skills spec](https://agentskills.io), tuned for a fast-moving framework.

---

## File structure

```
skills/
  mastra-<feature>/
    SKILL.md                 (required)
    references/
      api.md                 (required: exact signatures, options, defaults)
      examples.md            (required: 2 to 4 complete, runnable examples)
      checklist.md           (recommended: build and production checklist)
      <deep-dive>.md         (optional: provider tables, migration notes, patterns)
    scripts/                 (optional: helper scripts, see mastra-models)
```

Folder names are lowercase, hyphenated, and always start with `mastra-`. The folder name equals the `name` field.

---

## Frontmatter

Only spec-allowed top-level keys: `name`, `description`, `license`, `metadata`. Catalog fields live under `metadata` so the skills validate with both the Agent Skills spec and the catalog generator.

```yaml
---
name: mastra-agents
description: "Two to four pushy, trigger-rich sentences. Max 1024 characters. No angle brackets."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "One line for the README catalog, under 140 characters, no trailing period"
  display_order: 1
  docs: https://mastra.ai/docs/agents/overview
---
```

| Field | Notes |
|---|---|
| `name` | Must match the folder name. |
| `description` | Sentence 1: what the skill does. Sentence 2: "Use this skill whenever the user..." Sentence 3: "Triggers on ..." with generous synonyms, class names, and package names (`@mastra/memory`, `createTool`). Sentence 4 (optional): implicit triggers. |
| `metadata.category` | One of the category ids below. |
| `metadata.catalog_summary` | Third column of the README catalog. |
| `metadata.display_order` | Position inside the category, smallest first. |
| `metadata.docs` | The primary live docs URL for this feature. |

### Categories

| id | Title |
|---|---|
| `getting-started` | Getting started |
| `agents` | Agents |
| `models` | Models |
| `workflows` | Workflows |
| `memory-and-knowledge` | Memory, RAG, and storage |
| `harness` | Harness: durable agents, schedules, signals |
| `sandbox-and-browser` | Workspaces, sandboxes, and browsers |
| `connections` | Connections: MCP, A2A, ACP, channels, integrations |
| `server-and-frontend` | Server, client, frontend, and auth |
| `quality` | Evals, observability, and Studio |
| `deploy-and-platform` | Deployment, Mastra Platform, and CLI |

---

## SKILL.md structure

Exactly these eight `##` sections, in this order. A header may add a colon suffix (`## The framework: 4 memory types`). Do not rename the canonical words.

1. `## When to use`
2. `## When NOT to use` (each bullet redirects to the right sibling skill by name)
3. `## Required inputs`
4. `## The framework` (the mental model and the core API surface, with one minimal code sample)
5. `## Workflow` (numbered steps, step 1 is always "Verify the API", see below)
6. `## Failure patterns` (concrete mistakes, each with the fix)
7. `## Output format` (what a finished deliverable contains: files, registration, tests)
8. `## Reference files` (links to `references/*.md`, then a **Live docs** sub-list of canonical URLs)

Optional `## Deep dive: <topic>` sections may sit between `## Workflow` and `## Failure patterns`. Use at most two. If you need more, move content into a reference file.

Start the body with `# <Title>` and one sentence of purpose, then `---`.

---

## The Mastra rule: verify before you write

Mastra ships often. Constructor options, method names, and model IDs change between releases. Training data is stale. Every skill's Workflow starts with this step, phrased for its feature:

> 1. **Verify the API.** If `node_modules/@mastra/` exists, read the embedded docs in `node_modules/@mastra/<package>/dist/docs/` and the installed types. Otherwise fetch the live page as Markdown by appending `.md` to its URL (for example `https://mastra.ai/docs/agents/overview.md`). Trust these over memory.

Code samples in skills must come from the current docs, not memory. Keep them minimal and correct:

- Models use the router string format: `'openai/gpt-6.1-sol'`, never `openai:<model>` and never a provider import, unless the docs page shows otherwise.
- Tools use `createTool({ id, description, inputSchema, outputSchema, execute })` with `execute(inputData, context)`.
- Agents use `new Agent({ id, name, instructions, model })` and are registered on `new Mastra({ agents: { ... } })`, then fetched with `mastra.getAgentById()`.
- Imports use subpaths exactly as the docs show (`@mastra/core/agent`, `@mastra/core/tools`, `@mastra/core/workflows`, `@mastra/memory`).
- Projects are ESM (`"type": "module"`) with ES2022 `tsconfig` settings.

---

## Length rules

- `SKILL.md`: aim for 150 to 250 lines. Hard cap 500.
- Reference files: aim under 400 lines. Add a table of contents when over 150 lines.
- A reader should scan a whole skill folder in 15 minutes.

---

## Voice and style

- Short, declarative sentences. Imperative for instructions ("Register the agent", not "You should register").
- No em dashes. Use commas, colons, parentheses, or periods.
- No hype words ("leverage", "seamless", "cutting-edge", "powerful").
- Every principle gets one concrete example, usually code.
- Address the reader as "you". Refer to the person being helped as "the user".

---

## Cross-linking

- Redirect by skill name in backticks: "use `mastra-memory`".
- Never duplicate another skill's content. Link to it.
- `mastra-guide` is the router. Every new skill gets a row in its routing table.

---

## Validation

Run before committing:

```bash
python3 scripts/validate_skills.py
python3 scripts/generate_catalog.py --write
```

The validator checks frontmatter keys, name and folder match, description length and characters, the eight sections in order, line caps, and that every `references/` link resolves. The catalog script regenerates the README table between the `CATALOG` markers.

---

## Source mapping

`MAPPING.md` lists the docs pages each skill was built from. When Mastra updates a docs page, find the affected skills there and refresh them.
