# Classifier checklist

Run this before calling a classifier done.

## Fit

- [ ] The decision has a small, known set of outcomes
- [ ] A data object with many fields is not what is needed (that is structured output)
- [ ] Code exists for every outcome, the threshold, and a refusal

## Model

- [ ] `model` is a decision model from a provider's `decisionModel()`, not a `'provider/model'` string
- [ ] The provider supports every question type used
- [ ] Provider API key (for example `TYPESAFE_AI_API_KEY`) is in `.env.example`

## Questions

- [ ] Each question asks for one judgment
- [ ] Choice criteria are mutually exclusive
- [ ] Open sets include an `other` key or level
- [ ] Score questions have enough levels for intermediate values
- [ ] Facts go in `state`; `instructions` stay stable
- [ ] Questions are an object literal in the constructor so types are inferred
- [ ] Boolean thresholds treat `probability` as P(true)

## Data

- [ ] `state` holds only what the decision needs
- [ ] Sensitive fields are redacted, or the provider meets data-handling rules
- [ ] `hideInput`/`hideOutput` set in tracing options if state or answers are sensitive

## Wiring

- [ ] Shared classifiers registered in `new Mastra({ classifiers })`
- [ ] String references carry the question type argument
- [ ] Workflow `.branch()` conditions after `.classifier()` are mutually exclusive and cover refusals
- [ ] Each `ClassifierProcessor` has a unique `id`
- [ ] `errorStrategy: 'strict'` on safety gates; fail-open only where acceptable
- [ ] `onDecision` writes are fast or queued
- [ ] `ModelSelectionProcessor` keeps the capable model as default and only downgrades

## Verification

- [ ] Changing one state field moves one answer
- [ ] Refusal and provider failure paths tested
- [ ] `CLASSIFIER_EVALUATION` spans and token usage reviewed in Studio
- [ ] For model routing: cost per completed task measured with and without the processor
