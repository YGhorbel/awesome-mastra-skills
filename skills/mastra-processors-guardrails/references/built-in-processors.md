# Built-in processors

All import from `@mastra/core/processors`. Distilled from `https://mastra.ai/docs/agents/guardrails.md`, `https://mastra.ai/docs/agents/processors.md`, and `https://mastra.ai/reference/processors/*`. Check each reference page for the full option list before using an option not shown here.

## Contents

- Overview table
- LLM-based guardrails (shared options)
- PromptInjectionDetector
- PIIDetector
- ModerationProcessor
- SystemPromptScrubber
- LanguageDetector
- Non-LLM guardrails
- Limits and cost
- Utility processors
- Error processors

---

## Overview

| Processor | Direction | LLM | Strategies |
|---|---|---|---|
| `UnicodeNormalizer` | Input | No | n/a (always NFKC) |
| `RegexFilterProcessor` | Input, output, or both (`phase`) | No | `block`, `redact`, `warn` |
| `PromptInjectionDetector` | Input | Yes | `block`, `warn`, `filter`, `rewrite` |
| `LanguageDetector` | Input | Yes | `detect`, `translate`, `block`, `warn` |
| `PIIDetector` | Hybrid | Yes | `block`, `warn`, `filter`, `redact` |
| `ModerationProcessor` | Hybrid | Yes | `block`, `warn`, `filter` |
| `SystemPromptScrubber` | Output | Yes | `block`, `warn`, `filter`, `redact` |
| `ClassifierProcessor` | Hybrid | Yes | your `onResult` logic (see `mastra-classifier`) |
| `TokenLimiter` / `TokenLimiterProcessor` | Prompt, input, output | No | `truncate`, `abort` |
| `TokenCostControl` | Input (per step) | No | `block`, `warn` |
| `ToolCallFilter` | Input | No | n/a |
| `BatchPartsProcessor` | Output | No | n/a |
| `ResponseCache` | Input (request and response hooks) | No | n/a (beta) |
| `ToolSearchProcessor` | Input | No | n/a (see `mastra-tools`) |
| `ModelSelectionProcessor` | Input | Yes | Routes the run to a cheaper model |

`block` calls `abort()`, stops the request, and skips later processors. Most other strategies let the request continue.

---

## LLM-based guardrails: shared options

| Option | Notes |
|---|---|
| `model` | Model config for the internal detection agent. Use a small, fast model. |
| `errorStrategy` | `'warn'` (default, fail-open: log and continue) or `'strict'` (fail-closed: tripwire). `ClassifierProcessor` differs, see `mastra-classifier`. |
| `threshold` | 0 to 1 confidence. Content is flagged above it. |
| `instructions` | Custom detection instructions. |
| `lastMessageOnly` | Check only the newest message. Avoids one LLM call per earlier message. |
| `providerOptions` | Options for the internal agent, for example `{ openai: { reasoningEffort: 'low' } }`. |

---

## `PromptInjectionDetector`

```typescript
new PromptInjectionDetector({
  model: 'openrouter/openai/gpt-oss-safeguard-20b',
  threshold: 0.8,
  strategy: 'rewrite',
  errorStrategy: 'strict',
  detectionTypes: ['injection', 'jailbreak', 'system-override'],
})
```

Extra options: `detectionTypes`, `includeScores`, `onDetection(event)`. `rewrite` tries to neutralize the injection.

## `PIIDetector`

```typescript
new PIIDetector({
  model: 'openrouter/openai/gpt-oss-safeguard-20b',
  threshold: 0.6,
  strategy: 'redact',
  redactionMethod: 'mask',
  detectionTypes: ['email', 'phone', 'credit-card'],
  instructions: 'Detect and mask personally identifiable information.',
})
```

Extra options: `detectionTypes`, `redactionMethod` (`'mask' | 'hash' | 'remove' | 'placeholder'`), `preserveFormat` (keeps shapes like `***-**-1234`), `includeDetections`, `onDetection(event)`.

## `ModerationProcessor`

```typescript
new ModerationProcessor({
  model: 'openrouter/openai/gpt-oss-safeguard-20b',
  threshold: 0.7,
  strategy: 'block',
  categories: ['hate', 'harassment', 'violence'],
})
```

Extra options: `categories` (defaults to OpenAI categories), `includeScores`, `chunkWindow` (context chunks for stream moderation, when `bufferSize` is 0), `bufferSize` (hold streamed text and moderate per sentence or N characters; far fewer LLM calls).

## `SystemPromptScrubber`

```typescript
new SystemPromptScrubber({
  model: 'openrouter/openai/gpt-oss-safeguard-20b',
  strategy: 'redact',
  customPatterns: ['system prompt', 'internal instructions'],
  includeDetections: true,
  redactionMethod: 'placeholder',
  placeholderText: '[REDACTED]',
})
```

Extra options: `customPatterns` (regex strings), `redactionMethod` (`'mask' | 'placeholder' | 'remove'`), `placeholderText`, `bufferSize`. Over HTTP, the Mastra server also redacts system prompts, tool definitions, and API keys from stream chunks by default (see `mastra-server`).

## `LanguageDetector`

```typescript
new LanguageDetector({
  model: 'openrouter/openai/gpt-oss-safeguard-20b',
  targetLanguages: ['English', 'en'],
  strategy: 'translate',
  threshold: 0.8,
})
```

Extra options: `preserveOriginal` (keep original in metadata), `minTextLength`, `includeDetectionDetails`. `translationQuality` is deprecated and has no effect. On model failure with `'warn'`, it assumes a target language.

---

## Non-LLM guardrails

### `UnicodeNormalizer`

Options: `stripControlChars`, `preserveEmojis`, `collapseWhitespace`, `trim`. Always normalizes to NFKC.

### `RegexFilterProcessor`

```typescript
new RegexFilterProcessor({
  presets: ['pii', 'secrets'],
  strategy: 'block',
})

new RegexFilterProcessor({
  rules: [{ name: 'internal-id', pattern: /INTERNAL-\d{6}/g, replacement: '[INTERNAL_ID]' }],
  strategy: 'redact',
})
```

| Option | Notes |
|---|---|
| `presets` | `'pii'` (emails, phones, SSNs, cards), `'secrets'` (API keys, bearer tokens, AWS keys), `'urls'` |
| `rules` | `{ name, pattern: RegExp, replacement? }[]`. Replacement defaults to `[REDACTED]`. |
| `strategy` | `'block' \| 'redact' \| 'warn'` |
| `phase` | `'input' \| 'output' \| 'all'` (default `'all'`) |
| `includeRedactedValues` | Include removed text in reports. Default `false`. |
| `streamCarryoverSize` | Characters held between chunks so split matches are redacted whole. Raise for long custom patterns. |

---

## Limits and cost

### `TokenLimiter` / `TokenLimiterProcessor`

`new TokenLimiter(127000)` or `new TokenLimiterProcessor({ limit, strategy, countMode, trimMode })`.

| Option | Notes |
|---|---|
| `limit` | Token budget. |
| `strategy` | `'truncate'` (stop emitting) or `'abort'`. Truncate emits a transient `data-token-limit-reached` part. |
| `countMode` | `'cumulative'` or `'part'`. |
| `trimMode` | `'best-fit'` (default, trims provider prompt, may leave gaps), `'contiguous'` (keeps a continuous suffix), `'memory-only'` (trims stored history in `processInput`). |

Prompt trimming is transient. Tool calls and results are kept or removed together. Place it last among input processors so the final context fits.

### `TokenCostControl`

```typescript
new TokenCostControl({ maxCost: 5.0, scope: 'thread', window: '24h' })
```

| Option | Notes |
|---|---|
| `maxCost` | Number, or `(requestContext) => number`. |
| `scope` | `'run' \| 'resource' (default) \| 'thread' \| 'user' \| 'organization' \| 'session'` |
| `window` | `'1h' \| '6h' \| '24h' \| '7d' (default) \| '30d' \| '365d'`. Ignored for `'run'`. |
| `strategy` | `'block'` (default) or `'warn'`. |
| `message` | Template with `{usage}` and `{limit}`. |
| `warnAtPercent` | Soft threshold, for example 80. |
| `includeBreakdown` | Per provider/model breakdown in violations. |

Requires observability storage with `getMetricAggregate`. Checks are approximate (see `mastra-observability`).

---

## Utility processors

- **`ToolCallFilter`**: removes tool calls and results from the LLM input (memory keeps them). Options: `exclude` (tool names), `filterAfterToolSteps` (also filter inside the loop, keeping N recent tool steps), `preserveModelOutput` (keep compact `toModelOutput` history).
- **`BatchPartsProcessor`**: options `batchSize`, `maxWaitTime` (ms), `emitOnNonText`. Put it before heavy stream processors.
- **`ResponseCache`** (beta): `new ResponseCache({ cache, ttl, scope, key, bust, agentId })`. `cache` is a `MastraServerCache` (`InMemoryServerCache` from `@mastra/core/cache`, `RedisServerCache` from `@mastra/redis`). `ttl` defaults to 300 seconds. Scope defaults to the resource id. Per-call overrides: `requestContext: ResponseCache.context({ key, scope, bust })` or `ResponseCache.applyContext(ctx, {...})`. Failed and tripwired runs are not cached. Cache hits replay tool calls without running them.
- **`createBackgroundWorkSignalProcessor()`**: keeps the caller's signal access for background tool calls (see `mastra-harness`).
- Others with their own reference pages: `ModelSelectionProcessor`, `FileUploadProcessor`, `AgentsMDInjector`, `SkillSearchProcessor`, `CyberRefusalHandler`, and memory processors (see `mastra-memory`).

---

## Error processors

Defaults on every agent: `ProviderHistoryCompat`, `PrefillErrorHandler`, `UnsupportedFileHandler`, `StreamErrorRetryProcessor`. See `references/api.md` for ordering and overrides. Set `errorProcessorDefaults: false` to run only your own.
