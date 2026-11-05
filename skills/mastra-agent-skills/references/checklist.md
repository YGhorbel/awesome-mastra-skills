# Agent skills checklist

Run this before shipping skills on a Mastra agent.

## Content

- [ ] Each skill covers one procedure or reference topic
- [ ] Each `description` says when to load the skill, not only what it contains
- [ ] Always-on rules stay in agent `instructions`, not in a skill
- [ ] Actions that run code or call APIs are tools, not skills
- [ ] `SKILL.md` bodies hold the workflow; long detail lives in `references/`

## Naming and format

- [ ] Names are lowercase slugs, at most 64 characters, no leading, trailing, or double hyphens
- [ ] Filesystem skill `name` matches its directory name
- [ ] Frontmatter has `name` and `description`
- [ ] No two same-named skills share the same source type

## Wiring

- [ ] Skills attached through the agent's `skills` option or a workspace `skills` path
- [ ] Agent-level overrides of workspace skills are intentional
- [ ] Paths resolve in the deployed layout (workspace filesystem root or process working directory)
- [ ] Dynamic resolvers are fast, have a default set, and guard `tracingContext?.currentSpan`
- [ ] Resolver-backed workspaces read skills with `workspace.skills.getScoped({ requestContext })`
- [ ] BM25 or vector search configured if the skill collection is large (see `mastra-workspace-sandbox`)

## Safety

- [ ] Any code path that writes `SKILL.md` calls `validateSkillContent()` first
- [ ] User-supplied skills are reviewed before they reach a shared workspace (skills are instructions to the model)

## Verification

- [ ] `await agent.listSkills()` returns the expected set for each role or tenant
- [ ] A Studio run shows a `skill` tool call for a request that needs the skill
- [ ] A request that does not need the skill does not load it
