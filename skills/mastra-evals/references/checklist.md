# Evals checklist

Run this before calling an eval setup done.

## Scorer design

- [ ] Each quality dimension has one scorer, with a one-line definition of what it measures
- [ ] Deterministic properties use Quick Checks or code scorers, not an LLM judge
- [ ] Lower-is-better scorers (hallucination, toxicity, bias) are labeled, and thresholds use `{ max }`
- [ ] Custom scorers have a stable kebab-case `id` and a clear `description`
- [ ] Agent scorers use `type: 'agent'`
- [ ] Judge prompts anchor the 0 to 1 scale with endpoints and a middle value
- [ ] Judge prompts do not dictate output format in `generateScore`
- [ ] Judge model differs from the agent model, ideally another provider, and stays fixed across comparisons
- [ ] Runs a scorer does not apply to return `notScorable()` instead of 0
- [ ] Large conversations are trimmed with `filterRun()` or `prepareRun`
- [ ] Each custom scorer has a unit test with `scorer.run()` or `createAgentTestRun()`

## Wiring

- [ ] `@mastra/evals` installed and imports use the documented subpaths
- [ ] `storage` configured on the `Mastra` instance
- [ ] Every scorer used by `runEvals` (including checks) registered under `scorers`
- [ ] `runEvals` targets resolved with `mastra.getAgent()` or `mastra.getWorkflow()`
- [ ] Memory-enabled agents get a thread through `targetOptions.memory` or multi-turn `inputs`

## Live scoring

- [ ] `sampling.rate` set deliberately (1 for cheap checks, lower for LLM judges)
- [ ] Eligibility `filter` used for segment targeting instead of code branches
- [ ] Trace sampling understood: a dropped trace means no live score
- [ ] Judge cost per scored run estimated against budget

## Review

- [ ] Scores reviewed with reasons in Studio, not only averages
- [ ] Judge reasoning spot-checked, including passing cases
- [ ] Stable checks promoted to CI gates (see `mastra-datasets-experiments`)
