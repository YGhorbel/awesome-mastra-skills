# Observational Memory API reference

Distilled from `https://mastra.ai/reference/memory/observational-memory.md` and `https://mastra.ai/docs/memory/observational-memory.md`. Verify against the installed version before relying on an option.

## Contents

- Enabling
- Top-level options
- `observation` options
- `reflection` options
- Hooks
- Extractor API
- ModelByInputTokens
- Recall tool (retrieval mode)
- Stream data parts
- Standalone ObservationalMemory class
- Supported storage and limits

---

## Enabling

`options.observationalMemory` on `new Memory({...})` accepts `true`, `false`, or a config object. In an object, `enabled` defaults to `true`; only `enabled: false` disables it.

---

## Top-level options

| Option | Type | Default | Notes |
|---|---|---|---|
| `model` | `'auto' \| string \| LanguageModel \| DynamicModel \| ModelByInputTokens \| ModelWithRetries[]` | `'auto'` | Both roles. Cannot combine with `observation.model` or `reflection.model`. `'default'` selects the legacy fixed default. |
| `autoModels` | `Record<string, string>` | built-in | Override the auto pick per provider ID. |
| `resolveModel` | `(modelId, { requestContext }) => MastraModelConfig` | none | Build the auto-picked model with your own credentials. |
| `canUseProvider` | `(providerId, { requestContext }) => boolean` | none | Replaces the `GOOGLE_GENERATIVE_AI_API_KEY` check for auto. |
| `scope` | `'thread' \| 'resource'` | `'thread'` | `'resource'` is deprecated and disables async buffering. |
| `activateAfterIdle` | `number \| string \| false \| 'auto' \| Record<string, ...>` | none | Applies to observations only. |
| `activateOnProviderChange` | `boolean` | `false` | Observations only. |
| `shareTokenBudget` | `boolean` | `false` | Total budget `messageTokens + observationTokens`. Requires `observation.bufferTokens: false`. |
| `temporalMarkers` | `boolean` | `false` | Inserts a gap marker before a user message 10+ minutes after the previous one. |
| `retrieval` | `boolean \| { vector?, scope?, instructions? }` | `false` | Registers the `recall` tool. Default tool scope `'resource'`. |
| `hooks` | `ObserveHooks` | none | Lifecycle and transform hooks. |
| `observation` | object | | See below. |
| `reflection` | object | | See below. |

Auto selection order: `google/gemini-2.5-flash` when `GOOGLE_GENERATIVE_AI_API_KEY` is set, then a low-cost model for the main model's provider, then the main model itself. Models tested by Mastra: `openai/gpt-6-luna`, `anthropic/claude-haiku-5-5`, `deepseek/deepseek-flash`. `resolveAutoModelId(mainModelId, { autoModels })` from `@mastra/memory` returns the pick for a settings UI.

---

## `observation` options

| Option | Default | Notes |
|---|---|---|
| `model` | falls back to `reflection.model`, else `'auto'` | Observer model. |
| `messageTokens` | `30_000` | Unobserved tokens that trigger observation. Estimated locally with `tokenx`. |
| `bufferTokens` | `0.2` | Fraction (0 to 1) of `messageTokens` or absolute count. Must resolve below `messageTokens`. `false` disables observation and reflection buffering. |
| `bufferActivation` | `0.8` | Ratio removed on activation, or tokens to keep when 1000 or more. |
| `blockAfter` | `1.2` | 1 to under 100 multiplies `messageTokens`; 100 or more is absolute and must exceed `messageTokens`. |
| `bufferOnIdle` | `false` | Buffer when a turn ends and the agent goes idle. |
| `observeOnContextOverflow` | `true` | On provider context overflow, activate, observe all pending, retry once. |
| `instruction` | none | Appended to the Observer system prompt. |
| `continuationHints` | `true` | `false` or `{ currentTask?, suggestedResponse? }`. Async buffered calls never produce hints. |
| `threadTitle` | `false` | Observer updates the thread title on topic change. |
| `extract` | `[]` | `Extractor[]` run during observation. |
| `manageWorkingMemory` | `false` | Adds `WorkingMemoryExtractor`, defaults `workingMemory.agentManaged: false` and `useStateSignals: true`. |
| `observeAttachments` | images and PDFs | `true`, `false`, `'auto'`, or a mimeType allowlist such as `['image/*']`. |
| `maxRetries` | `8` | OM retry ladder; provider retries are off. |
| `failurePolicy` | `'abort'` | `'continue'` keeps input pending and lets the turn proceed. |
| `previousObserverTokens` | `false` | Budget of prior observations sent to the Observer. `0` omits them. |
| `maxTokensPerBatch` | | Resource scope only (deprecated). |
| `modelSettings` | `temperature: 0.3`, `maxOutputTokens: 100_000` | Defaults apply only to known or default models. |
| `providerOptions` | none | For example Google thinking config. |

---

## `reflection` options

| Option | Default | Notes |
|---|---|---|
| `model` | falls back to `observation.model`, else `'auto'` | Reflector model. |
| `observationTokens` | `40_000` | Observation tokens that trigger reflection. |
| `bufferActivation` | `0.5` | Start background reflection at this fraction. |
| `blockAfter` | `1.2` | Synchronous reflection safety net. |
| `instruction` | none | Appended to the Reflector prompt. |
| `continuationHints` | `true` | Same shape as observation. |
| `extract` | `[]` | Extractors run during reflection. |
| `maxRetries` | `8` | |
| `failurePolicy` | `'abort'` | `'continue'` defers reflection to the next threshold. |
| `modelSettings` | `temperature: 0`, `maxOutputTokens: 100_000` | |
| `activateAfterIdle`, `activateOnProviderChange` | none | No effect through `new Memory(...)`; standalone class only. |

---

## Hooks

`observationalMemory.hooks`:

| Hook | Kind | Receives | Return |
|---|---|---|---|
| `onObservationStart`, `onReflectionStart` | Lifecycle | `threadId`, `resourceId`, `trigger` (`'manual' \| 'turn-sync' \| 'async-buffer'`) | ignored |
| `onObservationEnd`, `onReflectionEnd` | Lifecycle | plus `usage`, `providerMetadata`, `error` | ignored |
| `beforeObservation` | Transform | `{ messages, ...context }` | `{ messages }` or void. Empty array skips the Observer call. |
| `afterObservation` | Transform | `{ observations, ...context }` | `{ observations }` or void |
| `beforeReflection` | Transform | `{ observations, ...context }` | `{ observations }` or void |
| `afterReflection` | Transform | `{ observations, ...context }` | `{ observations }` or void |

Lifecycle hooks are non-blocking unless `hookExecution: 'await'`. Transform hooks are always awaited. `skillResultRedactor({ toolNames? })` from `@mastra/memory/hooks` is a ready-made `beforeObservation` hook for `skill`, `skill_search`, `skill_read` results.

---

## Extractor API

```typescript
import { Extractor } from '@mastra/memory'
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | `string` | required | Slugified into `slug`; must be unique. |
| `instructions` | `string \| (context) => string` | | What to extract. |
| `schema` | `ZodType \| (context) => ZodType` | none | With schema: follow-up structured call. Without: inline string. |
| `includePreviousExtraction` | `boolean` | `true` | Show the last value on later runs. |
| `metadataKeyPath` | `string \| false` | `'extracted.<slug>'` | `false` skips persistence. |
| `onExtracted` | `(context) => T \| void \| Promise` | none | Return a value to replace; throw to record a failure. Context includes `current`, `threadId`, `resourceId`, `sendSignal`. |

Values persist under thread OM metadata `om.extracted`. Built-ins: `current-task`, `suggested-response`, `thread-title`.

---

## ModelByInputTokens

```typescript
import { ModelByInputTokens } from '@mastra/memory'

new ModelByInputTokens({ upTo: { 10_000: 'google/gemini-2.5-flash', 1_000_000: 'openai/gpt-6.1-sol' } })
```

Keys are inclusive upper bounds. Inputs above the largest key throw; during an OM run that becomes a TripWire with empty text. Methods: `resolve(inputTokens)`, `getThresholds()`. Added in `@mastra/memory@1.10.0`.

---

## Recall tool (retrieval mode)

Registered automatically when `retrieval` is truthy. Instructions are injected from the first turn.

| Param | Notes |
|---|---|
| `mode` | `'messages'` (default), `'threads'`, `'search'` (needs `vector: true`), `'observations'` |
| `cursor` | Message ID from an observation group range |
| `threadId` | Another thread, or `'current'` |
| `anchor` | `'start'` (default) or `'end'` |
| `page`, `limit` | Limit 1 to 20; defaults 20 messages, 5 groups, 10 search excerpts |
| `detail` | `'low'` (default) or `'high'` |
| `partType`, `toolName`, `partIndex`, `charOffset`, `viewAttachment` | Narrow and page single parts |
| `query` | Search text for `mode: 'search'` |
| `groupId`, `direction` | Observation paging around a search hit |
| `before`, `after` | ISO date filters for threads or search |

`retrieval: { scope: 'thread' }` restricts the tool to the current thread. `retrieval: { instructions }` appends guidance after built-in instructions.

---

## Stream data parts

| Type | When |
|---|---|
| `data-om-status` | Once per step, token windows and buffer state |
| `data-om-observation-start` / `-end` / `-failed` | Synchronous cycle |
| `data-om-buffering-start` / `-end` / `-failed` | Background cycle |
| `data-om-activation` | Buffered content activated (`triggeredBy`: `'threshold' \| 'ttl' \| 'provider_change'`) |
| `data-om-thread-update` | Title changed (`observation.threadTitle`) |

The `-end` parts carry `operationType`, `extractedValues`, and `extractionFailures`. Types are exported from `@mastra/memory/processors`.

---

## Standalone ObservationalMemory class

```typescript
import { ObservationalMemory, ObservationalMemoryProcessor } from '@mastra/memory/processors'
```

Accepts all options above plus `storage` (a `MemoryStorage`, for example `storage.stores.memory!`), `memory`, `onDebugEvent`, `obscureThreadIds`. Attach with `new ObservationalMemoryProcessor(om, memory)` in both `inputProcessors` and `outputProcessors`. `om.observe({ threadId, resourceId, force: true })` observes regardless of threshold.

---

## Supported storage and limits

- Storage: `@mastra/pg`, `@mastra/libsql`, `@mastra/mysql`, `@mastra/mongodb`, `@mastra/convex`, `@mastra/oracledb`.
- The `observational_memory` table has no timestamp anchor and cannot be pruned by retention.
- `cloneThread()` copies the current OM generation and remaps message IDs.
- Debugging: `OM_DEBUG=1` writes `om-debug.log`; also `getStatus()` and `onDebugEvent`.
