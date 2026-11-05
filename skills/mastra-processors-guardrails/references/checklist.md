# Guardrail checklist

Run this before calling processors done.

## Coverage

- [ ] Each rule maps to a processor, a direction, and a strategy
- [ ] User-facing agents have prompt injection detection on input
- [ ] PII and secrets are handled on input, output, and tool results where relevant
- [ ] Output moderation and system prompt scrubbing are on for public agents
- [ ] Token limits keep the context inside the model window
- [ ] Spend caps exist for agents that loop or serve many users

## Order and performance

- [ ] Cheap non-LLM checks (`UnicodeNormalizer`, `RegexFilterProcessor`) run first
- [ ] LLM guardrails use a small, fast model
- [ ] `lastMessageOnly: true` on detectors for long threads
- [ ] `BatchPartsProcessor` (or `bufferSize`) precedes heavy stream processors
- [ ] Independent block-only checks run in a parallel processor workflow
- [ ] `.map()` after `.parallel()` selects the `redact` branch when one exists
- [ ] `TokenLimiter` sits last among input processors

## Failure behavior

- [ ] `errorStrategy: 'strict'` on must-block guardrails
- [ ] `maxProcessorRetries` set wherever `abort(..., { retry: true })` is used
- [ ] Every caller handles `result.tripwire` or `tripwire` chunks with a safe message
- [ ] `onViolation` sends alerts or audit logs
- [ ] Default error processors kept, or replaced on purpose by `id`

## Custom processors

- [ ] Stable, unique `id`
- [ ] Reads text from `content.parts`
- [ ] `processOutputStream` returns `part` to pass chunks through
- [ ] `processDataParts = true` only when `data-*` chunks must be inspected
- [ ] No side effects that break on retries or replaced requests

## Verification

- [ ] Benign inputs pass unchanged
- [ ] Adversarial inputs (injection, PII, abuse) are blocked or redacted
- [ ] Added latency per request measured
- [ ] Processor spans reviewed in a trace (see `mastra-observability`)
