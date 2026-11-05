---
name: mastra-observational-memory
description: "Enable and tune Observational Memory (OM) in Mastra: background Observer and Reflector agents compress old messages into a dense observation log that replaces raw history, keeping the context window small and the prompt prefix cacheable. Use this skill whenever the user has long-running agent threads, tool-heavy sessions that blow the context window, rising token cost from history, prompt cache misses, or asks whether to use OM, message history, or semantic recall. Triggers on observationalMemory, Observational Memory, OM, Observer, Reflector, observation.messageTokens, reflection.observationTokens, bufferTokens, blockAfter, activateAfterIdle, shareTokenBudget, retrieval recall tool, Extractor, manageWorkingMemory, ModelByInputTokens, skillResultRedactor, memory.settled, OM_DEBUG, data-om-status. Also triggers for coding agents, browser agents, or support agents whose conversations run for hours."
license: Apache-2.0
metadata:
  category: memory-and-knowledge
  catalog_summary: "Observational memory: Observer and Reflector, thresholds, buffering, retrieval, models, limits, OM vs history vs recall"
  display_order: 3
  docs: https://mastra.ai/docs/memory/observational-memory
---

# Mastra Observational Memory

Keep long agent conversations coherent and cheap by replacing old raw messages with a compressed, append-only observation log.

---

## When to use

- Threads run long enough to approach the model's context window
- Tool results are large (browser snapshots, file reads) and old ones are noise
- Prompt caching matters and a sliding `lastMessages` window keeps breaking it
- Working memory is being abused to hold growing summaries or event logs
- Several users share a thread and per-user facts must survive history eviction
- Choosing between OM, message history, and semantic recall
- Debugging OM thresholds, buffering, retries, or the `recall` tool

## When NOT to use

- Short, single-session chats that fit in `lastMessages` (use `mastra-memory`)
- Threads, resources, working memory basics, memory APIs (use `mastra-memory`)
- Searching raw past messages by embedding similarity without OM (use `mastra-semantic-recall`)
- Storage adapter setup (use `mastra-storage`); OM supports only some adapters
- Shared facts across all threads of a user as a graph (use `mastra-knowledge`)
- One-off summaries of a finished thread (use `memory.summarizeThread()` in `mastra-memory`)

---

## Required inputs

- The storage adapter: must be `@mastra/libsql`, `@mastra/pg`, `@mastra/mongodb`, `@mastra/mysql`, `@mastra/convex`, or `@mastra/oracledb`
- Whether every call can pass a stable `thread` (required in the default thread scope)
- The Observer/Reflector model, or `'auto'`, and which provider keys exist
- Whether the agent relies on prompt caching (sets idle activation)
- Whether the agent needs exact wording later (retrieval mode)
- Values to extract into structured metadata, if any

---

## The framework: observe, reflect, retain

Three tiers live in context:

1. **Recent messages**: raw history for the current task.
2. **Observations**: dated notes the Observer writes when unobserved messages pass `observation.messageTokens` (default 30,000). Typical compression is 5x to 40x.
3. **Reflections**: when observations pass `reflection.observationTokens` (default 40,000), the Reflector rewrites the whole log into a smaller one.

```typescript
import { Agent } from '@mastra/core/agent'
import { LibSQLStore } from '@mastra/libsql'
import { Memory } from '@mastra/memory'

const memory = new Memory({
  storage: new LibSQLStore({ id: 'memory-storage', url: 'file:./memory.db' }),
  options: {
    observationalMemory: {
      model: 'openai/gpt-6-luna',
    },
  },
})

export const agent = new Agent({
  id: 'memory-agent',
  name: 'Memory Agent',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-6-luna',
  memory,
})

await agent.generate('Remember that my favorite color is blue.', {
  memory: { resource: 'user-123', thread: 'conversation-123' },
})
```

`observationalMemory: true` uses `model: 'auto'`. Async buffering is on by default: the Observer pre-computes chunks every ~6k tokens (`bufferTokens: 0.2`), and at 30k they activate instantly, leaving ~6k tokens of raw history (`bufferActivation: 0.8`). Raw history oscillates between about 6k and 30k tokens; the log stays near 40k.

### Choosing a memory layer

| Need | Use |
|---|---|
| Verbatim record of a short conversation | Message history (`lastMessages`) |
| Small, structured user facts | Working memory |
| Long-running threads, stable cacheable prompt | Observational memory |
| Find exact old wording by meaning | Semantic recall, or OM with `retrieval: { vector: true }` |

The docs state OM replaces both working memory and message history for long event logs, with greater accuracy and lower cost than semantic recall.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/memory/dist/docs/` and the installed types. Otherwise fetch `https://mastra.ai/docs/memory/observational-memory.md` and `https://mastra.ai/reference/memory/observational-memory.md`. Trust these over memory. OM was added in `@mastra/memory@1.1.0`.
2. **Confirm storage.** Use one of the six supported adapters, set on Mastra or on `Memory`.
3. **Enable OM.** `observationalMemory: true`, or an object with `model`. Remove `lastMessages` reliance: it does nothing under OM.
4. **Pick models.** Keep `'auto'`, or pin a fast model with a 128K+ window. Use `observation.model` and `reflection.model` to split roles (never with a top-level `model`).
5. **Pass a thread on every call.** Thread scope throws without one. Send only the new message from clients.
6. **Tune for caching.** Set `activateAfterIdle: 'auto'`, and `activateOnProviderChange: true` if the agent switches models.
7. **Add retrieval if exact details matter.** `retrieval: true` registers a `recall` tool; `{ vector: true }` adds semantic search using the Memory's vector store and embedder.
8. **Add extractors or working memory management.** `observation.extract: [new Extractor({...})]`, or `observation.manageWorkingMemory: true`.
9. **Decide failure policy.** Default `failurePolicy: 'abort'`. Use `'continue'` on both stages if a turn must survive an Observer outage.
10. **Shut down cleanly.** `await memory.settled()` before closing storage. Run every process against the same storage and PubSub backend with leases.
11. **Observe it.** Studio's Memory tab shows token bars and the active log. Debug with `OM_DEBUG=1` (writes `om-debug.log`).

---

## Deep dive: thresholds, buffering, and activation

| Setting | Default | Meaning |
|---|---|---|
| `observation.messageTokens` | `30_000` | Unobserved tokens that trigger observation |
| `observation.bufferTokens` | `0.2` | Buffer interval (fraction of `messageTokens` or absolute). `false` disables all async buffering |
| `observation.bufferActivation` | `0.8` | Fraction removed on activation (ratio) or tokens kept (1000 or more) |
| `observation.blockAfter` | `1.2` | Synchronous observation when buffering falls behind. `1` observes at the threshold |
| `reflection.observationTokens` | `40_000` | Observation tokens that trigger reflection |
| `reflection.bufferActivation` | `0.5` | Start background reflection at this fraction |
| `reflection.blockAfter` | `1.2` | Synchronous reflection safety net |
| `activateAfterIdle` | none | Activate buffered observations after idle time: ms, `'5m'`, `'auto'`, or `{ default: 'auto', anthropic: '1h' }` |
| `activateOnProviderChange` | `false` | Activate when the actor model changes |
| `shareTokenBudget` | `false` | Pool both budgets. Requires `observation.bufferTokens: false` |
| `observation.observeOnContextOverflow` | `true` | On provider overflow, observe pending messages and retry once. Keep it on |

With `'auto'`, idle TTL follows the provider: 5 minutes for Anthropic and OpenRouter, 1 hour for DeepSeek, 24 hours for Gemini, 2 hours for Groq, 1 hour or 5 minutes for OpenAI depending on model and `promptCacheRetention`. A per-message Anthropic `cacheControl.ttl` is not read; mirror it in the object form.

Through `new Memory(...)`, only the top-level `activateAfterIdle` and `activateOnProviderChange` apply. The nested `observation.*` and `reflection.*` variants apply only with the standalone `ObservationalMemory` class.

---

## Failure patterns

- **"threadId required" error.** Thread scope needs a thread on every call. Pass `memory: { resource, thread }`.
- **Unsupported adapter.** OM fails on adapters outside libSQL, PostgreSQL, MongoDB, MySQL, Convex, OracleDB. Switch, or route the `memory` domain with `mastra-storage` composite storage.
- **Tuning `lastMessages` with OM on.** Ignored: OM replaces history and the MessageHistory processor is skipped. Tune `observation.messageTokens`.
- **Huge first turn on an old thread.** All stored messages load until the first observation completes. Expect a one-time cost.
- **`shareTokenBudget: true` fails on first use.** Async buffering is on. Set `observation.bufferTokens: false`. Some invalid options validate on first memory operation, not at construction.
- **Lost observations in tests or scripts.** Background buffering was cut off. `await memory.settled()` before `store.close()`.
- **Multi-process deployment double-observes.** The mutex is per process. Share one PubSub backend with leases and one storage across processes.
- **`scope: 'resource'`.** Deprecated: worse caching, mixed context, slow. Use thread scope plus `retrieval: true` and resource-scoped working memory.
- **`ModelByInputTokens` throws on big inputs.** Input exceeded the largest `upTo` tier; OM aborts via TripWire and returns empty text. Cover the full range.
- **Reflections stay above threshold.** Detail-preserving Reflector model. Pick a condensing model such as `deepseek/deepseek-flash` for `reflection.model`.
- **Text-only Observer rejects images.** Set `observation.observeAttachments: false` or `'auto'`.
- **Skill instructions re-observed on every use.** Add `hooks: { beforeObservation: skillResultRedactor() }` from `@mastra/memory/hooks`.
- **Treating `afterObservation` as a redaction boundary.** It rewrites only observation text, not extractor results. Redact in `beforeObservation`.

---

## Output format

A finished OM delivery contains:

- `Memory` with `observationalMemory` and a supported storage adapter
- Model choice (`'auto'` or pinned) with provider keys in `.env.example`
- Call sites that always pass `resource` and `thread`
- Idle activation and failure policy chosen deliberately
- `memory.settled()` in shutdown paths and tests
- Evidence: Studio Memory tab or `data-om-*` stream parts showing an observation cycle

---

## Reference files

- [`references/api.md`](references/api.md) - Every `observationalMemory` option with defaults, Extractor API, recall tool parameters, stream data parts, standalone class.
- [`references/examples.md`](references/examples.md) - Defaults, cache-friendly tuning, retrieval with resource working memory, extractors with hooks, tiered models.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for OM.

**Live docs**

- https://mastra.ai/docs/memory/observational-memory
- https://mastra.ai/reference/memory/observational-memory
- https://mastra.ai/docs/memory/overview
- https://mastra.ai/reference/memory/settled
- https://mastra.ai/docs/memory/multi-user-threads
