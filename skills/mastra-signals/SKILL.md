---
name: mastra-signals
description: "Send input into a Mastra agent thread at any time with signals: sendMessage, queueMessage, sendSignal, queueSignal, state signals with sendStateSignal, durable notifications with sendNotificationSignal and an inbox tool, thread streams with subscribeToThread, signal providers (SignalProvider, WebhookSignalProvider, TaskSignalProvider, RingSignals), and leases for running across processes. Use this skill whenever the user wants to message a running agent, steer or interrupt it mid-run, wake an idle thread from a webhook or CI event, keep browser or editor state in context, deliver prioritized notifications, stream a thread's output across runs, or coordinate threads across replicas. Triggers on signals, sendSignal, sendMessage, queueMessage, subscribeToThread, ifActive, ifIdle, wake, persist, accepted action, transient signal, state lane, cacheKey, notification inbox, deliveryPolicy, dedupeKey, coalesceKey, SignalProvider, poll, handleWebhook, task_write, RedisStreamsPubSub, thread lease."
license: Apache-2.0
metadata:
  category: harness
  catalog_summary: "Messages, typed and state signals, durable notifications, thread streams, signal providers, and cross-process leases"
  display_order: 3
  docs: https://mastra.ai/docs/signals/overview
---

# Mastra Signals

Send input to an agent's thread whenever it arrives, receive output through one long-lived thread subscription, and route external events through notifications and providers.

---

## When to use

- A user sends a message while the agent is still working
- A follow-up should wait until the current answer finishes
- A system event (CI result, background job, webhook) should add context or wake an idle thread
- Context that changes over time (browser page, editor state) should stay current without chat noise
- Events need a durable inbox, priorities, summaries, and retries
- A UI should stream a thread's output across many runs, with history on reconnect
- Polling or webhook sources should notify the threads that subscribed to them
- Several Mastra processes may receive input for the same thread

## When NOT to use

- A one-off request and response (use `mastra-agents` with `generate` or `stream`)
- Starting work on a cron (use `mastra-schedules`, which sends threaded fires as signals)
- Durable agents, background tasks, goals, and AgentController sessions (use `mastra-harness`)
- Chat platform adapters such as Slack or Discord (use `mastra-channels`)
- Thread storage, history, and working memory setup (use `mastra-memory`)
- Writing input or output processors in general (use `mastra-processors-guardrails`)
- Calling a running server from a browser in general (use `mastra-client-sdk`)

---

## Required inputs

- The thread target: `resourceId` and `threadId` (Memory configured for storage-backed delivery)
- What kind of input it is: user message, system context, changing state, or external event
- What should happen when the thread is active or idle (deliver, persist, discard, wake)
- For notifications: source, kind, priority, a stable `dedupeKey`, and a storage adapter with the notifications domain
- For providers: how external resources map to threads (`externalResourceId`)
- Deployment: single process, several processes on one host, or several hosts

---

## The framework: choose the input type

| Input | API | Model sees | Stored |
|---|---|---|---|
| User message now | `agent.sendMessage(msg, target)` | user input, or `<user ...attrs>` | With Memory |
| User follow-up after current answer | `agent.queueMessage()` | user input | With Memory |
| System context | `agent.sendSignal({ type: 'reactive', tagName, contents })` | `<system-reminder>` or custom tag | Unless `transient: true` |
| Queued system context | `agent.queueSignal()` | as above | |
| Changing named state | `agent.sendStateSignal({ id, mode, cacheKey, contents })` | `<state>` snapshot or delta | Always (never transient) |
| External event with inbox | `agent.sendNotificationSignal({ source, kind, summary, priority })` | `<notification>` or `<notification-summary>` | Durable record |

Subscribe first, then send:

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { LibSQLStore } from '@mastra/libsql'

const agent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  instructions: 'Help the user compare options.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ storage: new LibSQLStore({ id: 'signals-storage', url: 'file:./signals.db' }) }),
})

const thread = { resourceId: 'user_123', threadId: 'thread_456' }
const subscription = await agent.subscribeToThread({ ...thread, withRunStatus: true })

const result = agent.sendMessage('Compare that with the previous option.', thread)
const { action } = await result.accepted // 'wake' | 'deliver' | 'persist' | 'discard' | 'blocked'

for await (const chunk of subscription.stream) {
  console.log(chunk) // stays open across later runs; call subscription.unsubscribe() when done
}
```

### Delivery defaults

| Thread state | Default | Alternatives |
|---|---|---|
| Active | `ifActive: { behavior: 'deliver' }` | `persist`, `discard` |
| Idle | `ifIdle: { behavior: 'wake' }` | `persist`, `discard` |

`accepted` resolves at routing time, not when the run ends. `wake` carries `output`. `persist` exposes `persisted` to await the write. A paused run (pending approval) returns `blocked`.

Input arriving during a model request can cancel and retry that request while the model has only produced reasoning or nothing yet. Once text or a tool call streams, input waits for the next loop boundary.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Agent` signal method types. Otherwise fetch `https://mastra.ai/docs/signals/overview.md`, `https://mastra.ai/docs/signals/sending-signals.md`, and `https://mastra.ai/reference/agents/agent.md`. Signals need `@mastra/core@1.39.0` or later, providers 1.42.0. Trust these over memory.
2. **Configure Memory** on the agent with storage so signals persist and threads exist. `sendStateSignal` cannot create a missing thread.
3. **Open a thread subscription** before sending (`agent.subscribeToThread` in-process, `client.getAgent(id).subscribeToThread` remotely). Add `withInitialHistory` and `withRunStatus` as needed.
4. **Pick the input type** from the table. Use `sendSignal` with `type: 'reactive'` and an XML-safe `tagName` for system context.
5. **Set delivery behavior** only when the defaults are wrong. Await `accepted` to catch routing failures.
6. **For changing context**, send a `snapshot` first, then `delta` updates, each with a new `cacheKey`. Or compute it in a processor with `computeStateSignal()`.
7. **For external events**, use `sendNotificationSignal` with `dedupeKey` or `coalesceKey`, configure `notifications.deliveryPolicy` on the agent, and add `createNotificationInboxTool()`.
8. **For sources you watch**, register a `SignalProvider` subclass or `WebhookSignalProvider` in the agent's `signals` array. Persist subscriptions yourself if they must survive restarts.
9. **For several processes**, share storage and a PubSub backend with leases (`RedisStreamsPubSub` across hosts, `UnixSocketPubSub` on one host). On serverless, keep a `wake` alive with `waitUntil`.
10. **Test** active and idle paths, a reconnect, and a duplicate event.

---

## Deep dive: notifications and providers

```typescript
const { record, decision } = await agent.sendNotificationSignal(
  {
    source: 'github',
    kind: 'ci-status',
    priority: 'high',
    summary: 'CI failed on main: 3 tests failed in the API suite.',
    payload: { repository: 'acme/app', branch: 'main', runId: '123456' },
    dedupeKey: 'github:acme/app:main:ci',
  },
  thread,
)
```

Built-in policy: `urgent` always delivers. `high` delivers when idle, summarizes then delivers later when active. `medium` delivers when idle, batches when active. `low` always batches. Override with `notifications.deliveryPolicy` on the agent (`decide`, then `sources`, then `priorities`, then `default`). Summaries and deferrals run through a dispatcher scheduled every minute by default (`new Mastra({ notifications: { dispatch } })`). Records fail after five delivery attempts.

Providers wrap this: subclass `SignalProvider` from `@mastra/core/signals`, set `id` and `pollInterval`, implement `poll(subscriptions)` or `handleWebhook(request)`, and call `this.notify(notification, { resourceId, threadId })`. `TaskSignalProvider` adds `task_write`, `task_update`, `task_complete`, and `task_check` with a `tasks` state lane.

---

## Failure patterns

- **Output missed at the start of a run.** You sent before subscribing. Subscribe first.
- **Treating `accepted` as completion.** It resolves on routing. Read the stream or `output` for results.
- **Two runs on one thread across replicas.** The default `EventEmitterPubSub` is in-process. Use a shared PubSub with leases and shared storage.
- **`GoogleCloudPubSub` duplicate runs.** It has no leases. Guarantee one process per thread elsewhere.
- **Signals lost after a crash.** Runtime queues are in memory. Use `persist`, state signals, or notifications for input that must survive.
- **State updates skipped.** Same `cacheKey` and mode returns `{ skipped: true, reason: 'unchanged' }`. Change the key when state changes.
- **State signal fails on a new thread.** `sendStateSignal` cannot create threads. Send a message first or create the thread.
- **`transient` with a state signal or `persist`.** State signals cannot be transient. `transient` plus persist discards the signal.
- **`sendNotificationSignal` throws.** Storage lacks the notifications domain. Use libSQL, Postgres, or MongoDB.
- **Model never sees `payload`.** Only `summary` and attributes reach the model. Put what matters in `summary`.
- **Duplicate notifications from polling.** Set a stable `dedupeKey`. Providers do not deduplicate before `notify()`.
- **Provider subscriptions vanish on restart.** The registry is in memory. Rehydrate in `start()`.
- **Public provider route without verification.** `requiresAuth: false` routes must check the webhook signature on the raw body.
- **Expecting `hideSignals` to secure data.** It only filters one subscriber's view.
- **Serverless function freezes mid-run.** Wrap `accepted.output.consumeStream()` in `waitUntil` on `wake`.

---

## Output format

A finished signals delivery contains:

- An agent with Memory and storage, registered on `Mastra`
- A thread subscription in the UI or server code, opened before input is sent
- Send calls using the right input type, with explicit `ifActive`/`ifIdle` only where needed
- For notifications: storage with the notifications domain, a delivery policy, dedupe keys, and the inbox tool
- For providers: the provider class, registration in `signals`, subscription persistence if needed, and shutdown via `stop()`
- For multiple processes: shared storage and `pubsub` on `Mastra`, consistent lease env vars

---

## Reference files

- [`references/api.md`](references/api.md) - Agent signal methods, accepted actions, subscription options, state signal fields, notification records and policies, inbox tool, provider API, thread events, PubSub topologies.
- [`references/examples.md`](references/examples.md) - Chat with mid-run steering, CI notifications with policy and inbox, browser state lane, polling provider, multi-process setup.
- [`references/checklist.md`](references/checklist.md) - Signals production checklist.

**Live docs**

- https://mastra.ai/docs/signals/overview
- https://mastra.ai/docs/signals/sending-signals
- https://mastra.ai/docs/signals/state-signals
- https://mastra.ai/docs/signals/notifications
- https://mastra.ai/docs/signals/thread-streams
- https://mastra.ai/docs/signals/signal-providers
- https://mastra.ai/docs/signals/running-across-processes
- https://mastra.ai/reference/signals/notifications
- https://mastra.ai/reference/signals/signal-provider
- https://mastra.ai/reference/signals/task-signal-provider
- https://mastra.ai/reference/signals/webhook-signal-provider
- https://mastra.ai/reference/signals/create-notification-inbox-tool
- https://mastra.ai/reference/signals/thread-events
