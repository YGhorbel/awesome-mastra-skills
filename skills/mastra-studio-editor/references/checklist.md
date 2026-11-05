# Studio and Editor checklist

Run this before handing Studio or Editor to a team.

## Studio

- [ ] All agents, workflows, tools, scorers, and MCP servers registered on `Mastra`
- [ ] Storage configured so threads, scores, datasets, and experiments persist
- [ ] Observability configured, with a metrics-capable store if the Metrics view matters
- [ ] `requestContextSchema` on agents that need request context, for the schema form
- [ ] `server.auth` set before any shared deployment
- [ ] RBAC roles mapped to real people, EE license checked for production SSO and RBAC
- [ ] Deployment mode chosen and env vars set (`MASTRA_STUDIO_PATH`, `MASTRA_STUDIO_BASE_PATH`)
- [ ] Studio behind HTTPS, with CORS configured when served separately
- [ ] Knowledge routes enabled only with auth and a principals mapping

## Editor

- [ ] `@mastra/editor` installed and `editor: new MastraEditor()` on `Mastra`
- [ ] Storage source chosen: database (draft and publish) or `source: 'code'` (pull requests)
- [ ] Each agent has an explicit `editor` field
- [ ] Studio-owned fields removed from code, and a first version published
- [ ] Model editing only with a static array and stable entry `id`s
- [ ] Tool providers limited with `allowedToolkits` or `allowedTools` where needed
- [ ] Provider API keys in env vars
- [ ] Shared policy text moved into prompt blocks
- [ ] Production reads published versions, staging may read drafts
- [ ] Draft changes run through an experiment before publishing (see `mastra-datasets-experiments`)
- [ ] Someone owns publishing, and rollback means restoring an older version
