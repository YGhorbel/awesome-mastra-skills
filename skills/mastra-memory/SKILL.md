---
name: mastra-memory
description: "Add conversation memory to Mastra agents with the Memory class from @mastra/memory: threads and resources, message history, token-budgeted history, working memory (Markdown template or schema, thread or resource scope), multi-user threads, title generation, memory processors, and the memory APIs for listing, recalling, cloning, and deleting threads and messages. Use this skill whenever the user wants an agent to remember earlier turns or user facts, wires memory: { resource, thread } into generate or stream, builds a chat sidebar from stored threads, or debugs an agent that forgets. Triggers on Mastra memory, @mastra/memory, new Memory, lastMessages, messageHistory, workingMemory, threadId, resourceId, createThread, listThreads, recall(), cloneThread, copyThread, deleteMessages, generateTitle, readOnly, MessageHistory processor, updateWorkingMemory. Also triggers when a Mastra agent must hold a multi-turn conversation, even if the user does not say memory."
license: Apache-2.0
metadata:
  category: memory-and-knowledge
  catalog_summary: "Memory class, threads and resources, message history, working memory, multi-user threads, memory APIs"
  display_order: 1
  docs: https://mastra.ai/docs/memory/overview
---

# Mastra Memory

Give a Mastra agent a durable conversation: stored threads, recent history in context, and small persistent facts about the user.

---

## When to use

- An agent must answer follow-ups that depend on earlier turns
- Adding `memory: new Memory({...})` to an agent, or fixing an agent that forgets
- Choosing `resource` and `thread` identifiers for users, tenants, or shared rooms
- Capping history by message count or by token budget
- Storing user facts with working memory (Markdown template or schema)
- Several people talking to one agent in the same thread
- Listing, recalling, cloning, or deleting threads and messages for a chat UI
- Auto-generating thread titles

## When NOT to use

- Finding older messages by meaning with embeddings (use `mastra-semantic-recall`)
- Long-running threads that outgrow the context window (use `mastra-observational-memory`)
- Choosing or configuring the database adapter (use `mastra-storage`)
- Choosing a vector database (use `mastra-vector-stores`)
- Document retrieval over your own corpus (use `mastra-rag`)
- Cross-thread shared knowledge graphs (use `mastra-knowledge`)
- Guardrails and custom processors in general (use `mastra-processors-guardrails`)
- Defining the agent itself (use `mastra-agents`)

---

## Required inputs

- Who owns a conversation: the value for `resource` (user ID, org ID, or a shared room ID)
- How a conversation is identified: the value for `thread` (and whether the client creates it)
- How much history the model needs: a message count or a token budget
- Facts that must persist across threads (working memory) and their shape
- The storage adapter already configured, or the one to add (see `mastra-storage`)
- Whether the thread is single-user or shared by several people

Default to `lastMessages` history only. Add working memory only when the user names facts to keep.

---

## The framework: storage, Memory, identifiers

Memory has three parts. Storage persists it. A `Memory` instance on the agent decides what goes into context. Each call names a `resource` and a `thread`.

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { supportAgent } from './agents/support-agent'

export const mastra = new Mastra({
  agents: { supportAgent },
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
})
```

```typescript
// src/mastra/agents/support-agent.ts
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support agent',
  instructions: 'Answer customer support questions.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ options: { lastMessages: 20 } }),
})
```

```typescript
const agent = mastra.getAgentById('support-agent')
await agent.generate('Remember my favorite color is blue.', {
  memory: { resource: 'user-123', thread: 'conversation-123' },
})
```

| Layer | What it adds to context | Configure with |
|---|---|---|
| Message history | Last N messages, oldest first | `lastMessages` (default 10) or `messageHistory` |
| Working memory | System message with a template or JSON object | `workingMemory` |
| Semantic recall | Older messages similar to the new input | `semanticRecall` (see `mastra-semantic-recall`) |
| Observational memory | Dense observation log replacing old history | `observationalMemory` (see `mastra-observational-memory`) |

Identifier rules:

- `resource` is the owner. A thread's `resourceId` cannot change after creation, so never reuse a thread ID across owners.
- `thread` is one conversation. Reuse the same pair to continue it.
- `thread` may be an object `{ id, title, metadata }` to set title and metadata on first use.
- Instead of `memory`, you can pass `scopes: ['resource:user-123', 'thread:conversation-123']`. Sources must agree or the call throws.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/memory/dist/docs/` and the installed `Memory` types. Otherwise fetch `https://mastra.ai/docs/memory/overview.md` and `https://mastra.ai/reference/memory/memory-class.md`. Trust these over memory.
2. **Install.** `npm install @mastra/memory@latest` plus a storage adapter such as `@mastra/libsql@latest`.
3. **Configure storage.** Put it on `new Mastra({ storage })` so every agent shares it, or on `new Memory({ storage })` for an isolated agent. Memory throws without storage.
4. **Attach memory.** `memory: new Memory({ options })` on the agent. Pick `lastMessages` or a `messageHistory` token budget.
5. **Pass identifiers on every call.** `memory: { resource, thread }`. Derive `resource` from the authenticated user on the server, never from the request body.
6. **Send only the new message from clients.** Mastra loads stored history. Use `retainFullInput: true` only when you assemble input yourself.
7. **Add working memory if facts must persist.** Choose `template` (replace semantics) or `schema` (merge semantics), and `scope: 'resource'` (default) or `'thread'`.
8. **Add titles if there is a thread list.** `generateTitle: true`, optionally with a cheaper `model`.
9. **Read memory for the UI.** `await agent.getMemory()`, then `listThreads`, `getThreadById`, `recall`. Check authorization first: memory does no access control.
10. **Test.** Two calls on the same thread in Studio (`npx mastra dev`) or a script. Check the Memory tab and the trace's LLM span.

---

## Deep dive: working memory

Working memory is a block the agent rewrites through an `updateWorkingMemory` tool. It is injected as a system message on every call.

```typescript
import { Memory } from '@mastra/memory'
import { z } from 'zod'

export const memory = new Memory({
  options: {
    lastMessages: 20,
    workingMemory: {
      enabled: true,
      scope: 'resource', // default: shared by all threads of the resource
      schema: z.object({
        name: z.string().optional(),
        timezone: z.string().optional(),
        preferences: z.object({ tone: z.string().optional() }).optional(),
      }),
    },
  },
})
```

| Mode | Semantics | Use when |
|---|---|---|
| `template` (Markdown) | Agent sends the whole block each update | Free-form profile or scratchpad |
| `schema` (zod, JSON Schema) | Deep merge; `null` deletes; arrays replace | Typed fields read by code |

Set `template` or `schema`, never both. Resource scope needs an adapter with the `mastra_resources` table: libSQL, PostgreSQL, OracleDB, Upstash, MongoDB. Seed it with `createThread({ metadata: { workingMemory } })` or `memory.updateWorkingMemory({...})`. Pass `memory.options.readOnly: true` on a call to show it without the update tool.

---

## Deep dive: multi-user threads

A thread has one `resourceId`, so every participant must pass the same one. Key it on the room or document (`doc_42`), not the user. Wrap each user message in a tag that names the speaker, and explain the tag in the instructions:

```typescript
await collabAgent.generate(
  [{ role: 'user', content: '<turn author_id="u_alice" author_name="Alice" functional_role="editor">\nShip Friday.\n</turn>' }],
  { memory: { thread: 'doc_42', resource: 'doc_42' } },
)
```

Build the tag on the server from the authenticated user. For long threads, prefer observational memory. Otherwise use thread-scoped working memory with a participants list. Running both adds cost without much benefit.

---

## Failure patterns

- **Agent forgets everything.** No storage on Mastra or Memory, or `resource`/`thread` missing or changing per call. Configure storage and pass a stable pair.
- **Error when querying a thread.** The same thread ID was used with two resources. Thread ownership is fixed; generate IDs per owner, or move a thread with `updateThreadResourceId()` from a trusted context.
- **Client sends the full history every turn.** Duplicates and ordering bugs. Send only the new message.
- **`lastMessages` set very high to fit long chats.** The sliding window breaks the prompt cache and bloats context. Use `messageHistory: { maxTokens }` or `mastra-observational-memory`.
- **`lastMessages` counts turns.** It counts every stored message, including tool calls, tool results, and signals.
- **Working memory never updates.** The agent does not call the tool. Tell it in `instructions` when to update which field.
- **Both `template` and `schema` set.** Not supported. Pick one.
- **Resource-scoped working memory on an unsupported adapter.** Use a listed adapter or `scope: 'thread'`.
- **Exposing `listThreads` or `recall` directly to clients.** No access control. Check the caller owns the `resourceId` first.
- **Shared Studio and app database diverge.** Relative `file:./mastra.db` resolves per process. Use an absolute path.
- **Large attachments fail to save on DynamoDB, Convex, or D1.** Record limits (400 KB, 1 MiB). Upload attachments in an input processor and store URLs.
- **Closing storage right after a run in tests.** Background work is lost. `await memory.settled()` before `store.close()`.

---

## Output format

A finished memory delivery contains:

- Storage configured in `src/mastra/index.ts` (or on the `Memory` with a reason)
- The agent file with `memory: new Memory({ options })`, history policy chosen deliberately
- Call sites passing `memory: { resource, thread }`, with `resource` taken from auth
- Working memory template or schema, plus instructions on when to update it, if used
- UI or API code for threads using `listThreads`/`recall` behind an ownership check
- Evidence: two-turn test or Studio session showing recall on the same thread

---

## Reference files

- [`references/api.md`](references/api.md) - Memory constructor options, per-call options, thread and message methods, `MastraDBMessage`.
- [`references/examples.md`](references/examples.md) - Basic chat memory, token-budgeted history with titles, schema working memory, thread management for a UI.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for agent memory.

**Live docs**

- https://mastra.ai/docs/memory/overview
- https://mastra.ai/docs/memory/message-history
- https://mastra.ai/docs/memory/working-memory
- https://mastra.ai/docs/memory/multi-user-threads
- https://mastra.ai/docs/memory/memory-processors
- https://mastra.ai/reference/memory/memory-class
- https://mastra.ai/reference/memory/recall
- https://mastra.ai/reference/memory/listThreads
