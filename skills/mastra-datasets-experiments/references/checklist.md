# Datasets and experiments checklist

Run this before calling an eval loop done.

## Dataset

- [ ] Storage adapter provides the `datasets` domain
- [ ] Dataset has a stable `id` or is looked up by a known name
- [ ] `inputSchema` and `groundTruthSchema` reject malformed items
- [ ] Ground truth describes required meaning (`must`, `mustNot`), not exact wording
- [ ] Cases cover ordinary requests, missing information, wrong premises, and policy edges
- [ ] Every case was reviewed by a person against the source policy
- [ ] Small enough to read every result by hand
- [ ] No secrets or PII in `input`, `groundTruth`, or `externalId` (use `purgeItem()` to erase)
- [ ] Process exists to add production traces as new cases

## Experiments

- [ ] Target and scorers registered on the `Mastra` instance and referenced by ID
- [ ] Side-effecting tools mocked, `unmockedToolPolicy: 'deny'` where live calls are unsafe
- [ ] Baseline run named and kept
- [ ] Each candidate changes one variable, with the dataset `version` pinned
- [ ] Results read per item (outputs, scores, reasons), not only averages
- [ ] Scorer errors checked: a `null` score is no evidence
- [ ] Memory-enabled agents use a dedicated evaluation resource
- [ ] `maxConcurrency`, `itemTimeout`, `maxRetries` tuned to provider limits

## CI gating

- [ ] Hard requirements are `gates` (binary checks)
- [ ] Quality metrics have thresholds, with `{ max }` for lower-is-better scorers
- [ ] Script exits non-zero unless `verdict === 'passed'`, and on execution errors
- [ ] Eval job is a required check or a dependency of the deploy job
- [ ] Provider keys stored as CI secrets
- [ ] Vitest: reporter and setup file registered, test timeouts raised
