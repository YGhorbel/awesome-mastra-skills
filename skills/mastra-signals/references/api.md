# Signals API reference

Distilled from `https://mastra.ai/reference/agents/agent.md` (signal methods), `https://mastra.ai/reference/signals/*.md`, and the signals docs. Verify against the installed version.

## Contents

- Agent signal methods
- Delivery options and accepted actions
- subscribeToThread()
- sendStateSignal() fields
- sendNotificationSignal() and records
- Delivery policy and dispatch
- createNotificationInboxTool()
- SignalProvider
- WebhookSignalProvider and TaskSignalProvider
- Thread events
- Cross-process topology

---

## Agent signal methods

| Method | Purpose | Returns |
|---|---|---|
| `sendMessage(message, options)` | User input now | `{ accepted, signal, persisted? }` |
| `queueMessage(message, options)` | User input after the active run | same, plus optional `queueOwnerId` |
| `sendSignal(signal, options)` | Typed system context | same |
| `queueSignal(signal, options)` | Queued typed context | same |
| `sendStateSignal(state, options)` | Named state lane | same, or `{ skipped: true, reason: 'unchanged' }` |
| `sendNotificationSignal(notification, options)` | Durable inbox record | `{ record, decision, runId?, signal?, persisted?, accepted? }` |
| `subscribeToThread(options)` | Output across runs | `AgentThreadSubscription` |
| `subscribeThreadEvents(scope, listener)` | Queue counts | unsubscribe function |
| `cancelQueuedMessages({ resourceId?, threadId, signalIds \| queueOwnerId })` | Cancel pending input | `{ cancelledSignalIds }` |
| `abortThreadStream({ resourceId, threadId, clearPendingSignals? })` | Abort the active run | `boolean` |

`message`: `string`, parts array, or `{ contents, attributes?, metadata?, providerOptions? }`. Attributes render as `<user name="Jane">`.

`signal`: `{ type: 'user' | 'state' | 'reactive' | 'notification', tagName?, contents, attributes?, metadata?, providerOptions?, transient? }`. Legacy `user-message` and `system-reminder` still accepted. `reactive` defaults to tag `system-reminder`. Tag and attribute names must be XML-safe.

---

## Delivery options and accepted actions

| Option | Values |
|---|---|
| `resourceId`, `threadId` | Thread target |
| `runId` | Target a known run (sendMessage) |
| `ifActive.behavior` | `deliver` (default), `persist`, `discard` |
| `ifActive.attributes` | Merged when accepted while active |
| `ifIdle.behavior` | `wake` (default), `persist`, `discard` |
| `ifIdle.streamOptions` | Execution options for the woken run |
| `ifIdle.attributes` | Merged when accepted while idle |
| `ifIdle.requireClaimedOwner` | Only wake an advertised owner process |

| `accepted.action` | Meaning |
|---|---|
| `wake` | This process started a run. Has `runId` and `output`. |
| `deliver` | Sent into a run, or another process took it. Has `runId`. |
| `persist` | Stored without running. Await `persisted`. |
| `discard` | Dropped |
| `blocked` | A paused run owns the thread |

`accepted` rejects only when the signal cannot be routed at all.

---

## subscribeToThread()

| Option | Notes |
|---|---|
| `resourceId`, `threadId` | Target |
| `withInitialHistory` | `true` or `{ perPage }` (default 40). First chunk `thread-history` with `{ messages, hasMore, activeRunId }`. |
| `withRunStatus` | Adds `thread-run-status` chunks: `success`, `failed`, `aborted`, `suspended` |
| `hideSignals` | `true`, `false`, or array of types. In-process only. Not a security boundary. |

Subscription members: `stream`, `activeRunId()`, `abort({ clearPendingSignals? })`, `unsubscribe()`.

Client SDK: `client.getAgent(id).subscribeToThread({ resourceId, threadId })` then `subscription.processDataStream({ onChunk, reconnect: true })`. Approvals via `client.getAgent().sendToolApproval()`.

---

## sendStateSignal() fields

| Field | Notes |
|---|---|
| `id` | Lane name (`browser`, `editor`) |
| `mode` | `snapshot` (default) or `delta` |
| `cacheKey` | Skips unchanged updates for the lane and mode |
| `contents` | Text the model reads |
| `value` | Structured snapshot, not shown to the model |
| `delta` | Structured change for `delta` mode |
| `attributes`, `metadata` | |
| `tagName` | Default `state` |

Processor form: `computeStateSignal(args)` on a processor with `stateId`. Args include `activeStateSignals`, `lastSnapshot`, `deltasSinceSnapshot`, `contextWindow.hasSnapshot`. Return `undefined` when unchanged. Import types from `@mastra/core/processors`.

Built-in lanes: `browser`, `goal`, `tasks`, and `working-memory` (with `useStateSignals: true`).

---

## sendNotificationSignal() and records

Input: `source`, `kind`, `summary`, `priority` (`low | medium | high | urgent`, default medium), `payload`, `dedupeKey`, `coalesceKey`, `attributes`, `metadata`. Options: `resourceId`, `threadId`, `ifIdle.streamOptions`. Accepts one notification or an array.

Record status: `pending`, `delivered`, `seen`, `dismissed`, `archived`, `discarded`, `failed`.

Merging only within the same thread, source, kind, agent, and resource while pending. Merge keeps latest `summary` and `payload`, merges `attributes` and `metadata`, increments `coalescedCount`.

Storage domain `notifications`: libSQL, PostgreSQL, MongoDB. Missing domain throws.

Model output shapes:

```xml
<notification source="github" kind="ci-status" priority="high" status="delivered">...</notification>
<notification-summary pending="10">github: 3, email: 5, slack: 2</notification-summary>
```

---

## Delivery policy and dispatch

Agent option `notifications.deliveryPolicy`:

```typescript
{
  default?: Action | Decision
  priorities?: Partial<Record<Priority, Action | Decision>>
  sources?: Record<string, Action | Decision>
  decide?: ({ record, threadState: 'active' | 'idle', now }) => Action | Decision | undefined
}
```

Actions: `deliver`, `queue`, `defer`, `summarize`, `persist`, `discard`. Decision: `{ action, deliverAt?, summaryAt?, reason?, streamOptions?, hold? }`.

Evaluation order: `decide`, `sources`, `priorities`, `default`, built-in.

| Priority | Idle | Active |
|---|---|---|
| urgent | deliver | deliver |
| high | deliver | summary now, deliver when idle |
| medium | deliver | batch into summary |
| low | batch | batch |

Mastra option `notifications.dispatch`: `enabled` (true), `cron` (`*/1 * * * *`), `batchSize` (100). Created lazily on first deferral or summary. `MAX_NOTIFICATION_DELIVERY_ATTEMPTS` is 5.

---

## createNotificationInboxTool()

```typescript
import { createNotificationInboxTool } from '@mastra/core/notifications'
const tool = createNotificationInboxTool({ storage: await storage.getStore('notifications') })
```

Tool id `notification-inbox`. Input: `action` (`list | read | markSeen | dismiss | archive | search`), `threadId`, `id`, `status`, `priority`, `source`, `query`, `limit`. `read` delivers full contents as notification signals. `list` defaults to pending, delivered, and failed, and marks them seen.

---

## SignalProvider

Import `SignalProvider` and types from `@mastra/core/signals`.

| Member | Notes |
|---|---|
| `id` (readonly), `name`, `pollInterval` | Subclass sets `id` |
| `connect(agent)` | Call `super.connect(agent)` first when overriding |
| `start()` / `stop()` | `start` not awaited by the agent. `stop` is sync, clears registry. Call it on shutdown. |
| `subscribe(target, externalResourceId, metadata?)` | Protected |
| `unsubscribe()`, `unsubscribeAll(target)` | Protected |
| `getSubscriptions()`, `getSubscriptionsForResource(id)`, `getSubscriptionsForThread(target)`, `hasSubscription()`, `subscriptionCount` | |
| `poll(subscriptions)` | Called every `pollInterval`, never overlapping, errors logged |
| `startPolling()`, `stopPolling()` | |
| `handleWebhook(request)` | Returns `{ status?, body? }` |
| `getRoutes()` | `ApiRoute[]` auto-mounted when the agent registers. Paths cannot start with `/api`. |
| `getInputProcessors()`, `getOutputProcessors()`, `getTools()` | Contributed to the agent |
| `notify(notification, target)` | Wraps `sendNotificationSignal`. Throws when not connected. |

`SignalProviderTarget`: `{ resourceId, threadId, agentId?, ifIdle? }`. `SignalSubscription`: `{ id, providerId, threadId, resourceId, externalResourceId, subscribedAt, metadata }`. Type guard `isSignalProvider(obj)`.

---

## WebhookSignalProvider and TaskSignalProvider

`new WebhookSignalProvider({ id?, name?, extractResourceId?, buildNotification? })`. Defaults: id `webhook-signals`, reads `payload.resource` or `payload.externalResourceId`, sends `webhook-event` at medium priority. Methods: `subscribeThread(target, externalResourceId, metadata?)`, `unsubscribeThread()`, `handleWebhook({ body, headers })`. Static: `WebhookSignalProvider.signals.subscribe(id)` and `.unsubscribe(id)` return reactive signal inputs.

`new TaskSignalProvider()` takes no arguments. Id `task-signals`. Adds `task_write`, `task_update`, `task_complete`, `task_check` and `TaskStateProcessor`. Needs a memory-backed thread.

`RingSignals` from `@mastra/ring-signals` connects Ring doorbells (webhooks, `ring_snapshot` and `ring_clip` tools). See the channels integrations.

---

## Thread events

`agent.subscribeThreadEvents({ resourceId, threadId, queueOwnerId? }, listener)` emits `{ type: 'queue-count-changed', count }` for local `queueMessage`/`queueSignal` entries. Baseline event on subscribe.

---

## Cross-process topology

| Deployment | PubSub | Leases |
|---|---|---|
| One process | `EventEmitterPubSub` (default) | yes |
| One host, several processes | `UnixSocketPubSub` | yes |
| Several hosts | `RedisStreamsPubSub` (`@mastra/redis-streams`), `ValkeyStreamsPubSub` | yes |
| Google Cloud | `GoogleCloudPubSub` | no |

Lease env vars: `MASTRA_AGENT_THREAD_LEASE_TTL_MS` (15000), `MASTRA_AGENT_THREAD_LEASE_RENEW_INTERVAL_MS` (a third of TTL). Delivery is at-least-once. Use the same `keyPrefix` on coordinating instances.
