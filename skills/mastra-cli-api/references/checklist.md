# CLI and `mastra api` checklist

Run through this before and after using the CLI against any server.

## Before calling

- [ ] Installed CLI version known (`mastra --version`); command exists (`--help`)
- [ ] Target confirmed: localhost, explicit `--url`, or linked platform project
- [ ] Region confirmed for hosted observability (US default, EU via `--url`)
- [ ] Auth comes from env vars or saved login, never from values pasted in chat
- [ ] Input shape checked with `--schema` for every mutating command

## While calling

- [ ] Exactly one inline JSON object per command, single-quoted
- [ ] Small pages (`perPage` 1 to 10, `page.limit` 25 or less) while exploring
- [ ] Output projected with `jq` before reading
- [ ] No unfiltered `--pretty` or `--verbose` during exploration
- [ ] `--timeout` raised for long workflow runs
- [ ] Mutations (`run`, `execute`, `create`, `update`, `delete`, `resume`, `cancel`) confirmed with the user when they touch production

## Queries

- [ ] Time range holds data and is within plan retention
- [ ] Same-span conditions inside one `spans.some` clause
- [ ] `span query` predicates not wrapped in `spans.some`
- [ ] Cursor passed back unchanged with the identical query
- [ ] `truncated` checked on aggregates
- [ ] Capabilities checked before relying on gated fields; `501` reported, not approximated
- [ ] Null cost and low coverage reported as unknown

## After calling

- [ ] Results summarized with IDs for follow-up
- [ ] Empty results described as "no stored data", not as failure
- [ ] Errors reported with `error.code` and the relevant `error.details`
