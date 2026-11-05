# Knowledge checklist

Run this before calling a Knowledge setup done.

## Scope design

- [ ] Every audience maps to a declared scope type
- [ ] `knowledgeMemoryScopes()` spread in (tenant renamed if needed)
- [ ] Patterns of one type do not overlap
- [ ] Every principal is a declared type bound by address prefix or `belongsTo`
- [ ] Role-only types (used as audiences) are declared, even as `{}`
- [ ] `description` set on types the model should understand
- [ ] Content lives in content scopes, not in role scopes

## Access

- [ ] Run scopes come only from server code (`MASTRA_SCOPES_KEY`, call `scopes`, agent `scopes`)
- [ ] `MASTRA_RESOURCE_ID_KEY` set alongside scopes in middleware
- [ ] Agent `scopes` functions return every `resource:` and `thread:` scope
- [ ] Users in several orgs get one resource ID per org
- [ ] `explainAccess()` tests cover allow and deny for each rule
- [ ] Host methods (`upsertPage`, `addNote`, `explainAccess`, `getStorage`) never exposed to agents or unauthenticated routes
- [ ] The user knows the alpha is not an isolation boundary

## Agents and content

- [ ] `tools` set deliberately (read-only for answer-only agents)
- [ ] `read.maxTokens` sized for the model
- [ ] Seed script uses `upsertPage()` and adds each note once
- [ ] `vector` and `embedder` configured before content is written, if search by meaning is needed
- [ ] Pinned pages are short, and `pinnedContext.maxTokens` fits the model
- [ ] Agents receiving pins have Memory
- [ ] Config-pinned template pages have a body written from the server

## Deployment

- [ ] Instance registered on `new Mastra({ knowledge })` with `KNOWLEDGE_ROUTES` if Studio browsing is wanted
- [ ] Auth configured and `MASTRA_KNOWLEDGE_PRINCIPALS_KEY` set in `authorize`
- [ ] Scope key renames followed by `renameScopeDeclaration()` immediately after deploy
- [ ] `onChange()` consumers re-read pages under each viewer's `readScopeFor()` scope
