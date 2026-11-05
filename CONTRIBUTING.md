# Contributing

Thanks for helping keep these Mastra skills accurate. Mastra changes often, so most useful contributions fix something that has drifted from the docs.

## What we welcome

- **Fixing outdated APIs.** A constructor option, method name, import path, or model ID no longer matches the docs.
- **Fixing contradictions.** If a skill follows a docs page that conflicts with another page, say which pages disagree and what the skill should do.
- **Improving examples.** Examples should be complete, runnable, and taken from the current docs.
- **Adding provider or integration rows.** Tables in `providers.md` files should match the integration pages.
- **Adding a new skill.** Only when a feature area has no skill yet. Check [MAPPING.md](MAPPING.md) first.

Please don't open a PR that only rewords prose or adds new APIs from memory. Every change needs a docs source.

## Before you start

1. Read [SKILL_AUTHORING.md](SKILL_AUTHORING.md). It defines the structure, frontmatter, voice, and length rules that every skill follows.
2. Find the skill you want to change, or its sources, in [MAPPING.md](MAPPING.md).
3. Read the current docs page. Fetch Markdown by appending `.md` to the mastra.ai URL, for example `https://mastra.ai/docs/agents/tools.md`. Full index: `https://mastra.ai/llms.txt`.

## Setup

You need Python 3 with PyYAML for the scripts. Node.js is only needed to run the model-lookup script.

```bash
python3 -m pip install pyyaml
```

There is no build step.

## Making a change

1. Create a branch from `master`:

   ```bash
   git checkout -b fix/mastra-memory-semantic-recall
   ```

2. Edit the skill. Keep the eight required `SKILL.md` sections in order.
3. Validate and regenerate the catalog:

   ```bash
   python3 scripts/validate_skills.py
   python3 scripts/generate_catalog.py --write
   ```

   The validator must report every skill as valid. Fix all errors. Warnings should be fixed or explained in the PR.
4. Check that the catalog is up to date:

   ```bash
   python3 scripts/generate_catalog.py --check
   ```

5. Open a pull request. Describe what changed and link the docs pages you checked.

## Rules for every skill

**Accuracy**
- Every code sample must match the current docs. Do not invent options, methods, imports, or model IDs.
- Use model IDs exactly as the docs show them. Prefer the `provider/model` router format.
- If docs pages conflict, follow the reference page and note the conflict in the skill.
- Keep the "Verify the API" first step in every workflow.

**Structure**
- Folder name, `name` field, and folder must match. Names start with `mastra-`.
- `SKILL.md` has exactly these sections in order: When to use, When NOT to use, Required inputs, The framework, Workflow, Failure patterns, Output format, Reference files.
- Required reference files: `references/api.md` and `references/examples.md`. `references/checklist.md` is recommended.
- `SKILL.md` aims for 150 to 250 lines, with a hard cap of 500. Reference files aim for under 400 lines.

**Frontmatter**
- Only `name`, `description`, `license`, `metadata`, and `allowed-tools` are allowed at the top level.
- `description` is 2 to 4 sentences, at most 1024 characters, with no angle brackets. Include trigger phrases.
- `metadata` holds `category`, `catalog_summary` (under 140 characters), `display_order`, and `docs`.

**Style**
- No em dashes. Use commas, colons, parentheses, or periods.
- Short, declarative sentences. Imperative for steps.
- No hype words such as "leverage", "seamless", or "powerful".
- No secrets, real API keys, or `.env` files, even as examples. Use placeholders.

**Cross-links**
- Refer to sibling skills by name, in backticks. Do not copy their content.
- Every linked file must exist. The validator checks this.

## Adding a new skill

1. Confirm the feature has docs and no existing skill covers it.
2. Add a row to [MAPPING.md](MAPPING.md) with its category, display order, and source pages.
3. Create `skills/<name>/` with `SKILL.md`, `references/api.md`, `references/examples.md`, and `references/checklist.md`.
4. Add the new skill to the "When NOT to use" lists of related skills, and to the routing table in `mastra-guide`.
5. Run the validator and the catalog generator.

## Updating after a Mastra release

Mastra publishes new versions often. When a docs page changes:

1. Find the affected skills in [MAPPING.md](MAPPING.md).
2. Update the skill and its references.
3. Update the docs snapshot date if your PR refreshes a skill against the live docs.

## Reporting problems

Open an issue with:
- The skill name and file
- The docs page that disagrees, with its URL
- What you expected and what the skill says

If the problem is in Mastra itself, report it to Mastra. This repo only covers how the skills describe Mastra.

## Licence

By contributing, you agree that your contributions are licensed under the [Apache-2.0](LICENSE) licence.
