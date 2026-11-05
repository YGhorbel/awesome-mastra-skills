# Signals examples

All examples follow the current docs. They assume the agent and `thread` from the SKILL.md framework section unless shown otherwise.

## Contents

1. Chat with mid-run input and queued follow-ups
2. CI notifications with a policy and inbox
3. Browser state lane
4. Polling signal provider
5. Webhook provider
6. Multiple processes and serverless

---

## 1. Chat with mid-run input and queued follow-ups

```typescript
const thread = { resourceId: 'user_123', threadId: 'thread_456' }

const subscription = await agent.subscribeToThread({
  ...thread,
  withInitialHistory: true,
  withRunStatus: true,
})

// Render history and live output
void (async () => {
  for await (const chunk of subscription.stream) {
    if (chunk.type === 'thread-history') render(chunk.payload.messages)
    else handle(chunk)
  }
})()

// Delivered into the active run, or wakes an idle thread
await agent.sendMessage('Compare that with the previous option.', thread).accepted

// Waits for the current answer, then runs
await agent.queueMessage('Also check whether the tests need updates.', thread).accepted

// System context from your app
await agent.sendSignal(
  { type: 'reactive', tagName: 'ci-result', contents: 'CI failed on main: 3 tests failed.' },
  thread,
).accepted

// Stop the run and drop queued input
subscription.abort({ clearPendingSignals: true })
```

Shared threads: pass `{ contents, attributes: { name: 'Jane', sentFrom: 'slack' } }` to `sendMessage`.

---

## 2. CI notifications with a policy and inbox

```typescript
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { LibSQLStore } from '@mastra/libsql'
import { Memory } from '@mastra/memory'
import { createNotificationInboxTool } from '@mastra/core/notifications'

const storage = new LibSQLStore({ id: 'mastra', url: 'file:./mastra.db' })
const notificationsStorage = await storage.getStore('notifications')

const ciAgent = new Agent({
  id: 'ci-agent',
  name: 'CI Agent',
  instructions: 'Triage CI failures and explain what broke. Read the inbox after a notification summary.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ storage }),
  tools: {
    notificationInbox: createNotificationInboxTool({ storage: notificationsStorage }),
  },
  notifications: {
    deliveryPolicy: {
      sources: { github: 'summarize' },
      priorities: { urgent: 'deliver', low: 'discard' },
    },
  },
})

export const mastra = new Mastra({
  agents: { ciAgent },
  storage,
  notifications: { dispatch: { enabled: true, cron: '*/1 * * * *', batchSize: 100 } },
})

const agent = mastra.getAgent('ciAgent')
const thread = { resourceId: 'user_123', threadId: 'thread_456' }
const subscription = await agent.subscribeToThread(thread)

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
console.log(record.status, decision.action)

for await (const chunk of subscription.stream) {
  console.log(chunk)
  if (chunk.type === 'finish') break
}
```

---

## 3. Browser state lane

```typescript
// Thread must already exist (send a message first, or create it through Memory)
const result = await agent.sendStateSignal(
  {
    id: 'browser',
    mode: 'snapshot',
    cacheKey: 'browser:https://example.com:3-tabs',
    contents: 'Browser is open. Active tab URL: https://example.com. 3 open tabs.',
    value: { activeUrl: 'https://example.com', tabCount: 3, open: true },
  },
  { resourceId: 'user_123', threadId: 'thread_456' },
)

if ('skipped' in result && result.skipped) {
  // same cacheKey and mode already current
}

// Later, a small change
await agent.sendStateSignal(
  {
    id: 'browser',
    mode: 'delta',
    cacheKey: 'browser:https://example.com/docs:3-tabs',
    contents: 'Active tab changed to https://example.com/docs.',
    delta: { activeUrl: 'https://example.com/docs' },
  },
  { resourceId: 'user_123', threadId: 'thread_456' },
)
```

Send a fresh snapshot when the earlier one may have left the context window.

---

## 4. Polling signal provider

```typescript
import { SignalProvider } from '@mastra/core/signals'
import type { SignalProviderTarget, SignalSubscription } from '@mastra/core/signals'
import { Agent } from '@mastra/core/agent'

type BuildStatus = { id: string; status: 'passed' | 'failed' }

async function fetchBuildStatus(pipeline: string): Promise<BuildStatus> {
  // call your CI service
  return { id: 'build_123', status: 'failed' }
}

export class CiSignals extends SignalProvider<'ci-signals'> {
  readonly id = 'ci-signals' as const
  readonly pollInterval = 30_000

  watch(target: SignalProviderTarget, pipeline: string) {
    return this.subscribe(target, pipeline)
  }

  unwatch(target: SignalProviderTarget, pipeline: string) {
    return this.unsubscribe(target, pipeline)
  }

  async poll(subscriptions: SignalSubscription[]) {
    for (const sub of subscriptions) {
      const build = await fetchBuildStatus(sub.externalResourceId)
      if (build.status !== 'failed') continue
      await this.notify(
        {
          source: this.id,
          kind: 'ci-status',
          priority: 'high',
          summary: `Build failed for ${sub.externalResourceId}`,
          payload: build,
          dedupeKey: `${this.id}:${sub.externalResourceId}:${build.id}`,
        },
        { resourceId: sub.resourceId, threadId: sub.threadId },
      )
    }
  }
}

export const ciSignals = new CiSignals()

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  instructions: 'Help the user triage CI updates.',
  model: 'openai/gpt-6.1-sol',
  signals: [ciSignals],
})

ciSignals.watch({ resourceId: 'user_123', threadId: 'thread_456' }, 'acme-app-main')
```

Register `supportAgent` on a `Mastra` instance with notifications storage. Call `ciSignals.stop()` on shutdown.

---

## 5. Webhook provider

```typescript
import { Agent } from '@mastra/core/agent'
import { WebhookSignalProvider } from '@mastra/core/signals'

const webhooks = new WebhookSignalProvider({
  extractResourceId: payload => (payload as { repository: string }).repository,
  buildNotification: (payload, sub) => ({
    source: 'ci',
    kind: 'build-status',
    priority: 'medium',
    summary: `Build ${(payload as { status: string }).status} for ${sub.externalResourceId}`,
  }),
})

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  instructions: 'Help the user triage updates.',
  model: 'openai/gpt-6.1-sol',
  signals: [webhooks],
})

webhooks.subscribeThread({ resourceId: 'user_123', threadId: 'thread_456' }, 'acme/app')

// In your verified webhook route:
// await webhooks.handleWebhook({ body, headers })
```

Verify the source signature against the raw body before calling `handleWebhook`.

---

## 6. Multiple processes and serverless

```typescript
import { Mastra } from '@mastra/core'
import { PostgresStore } from '@mastra/pg'
import { RedisStreamsPubSub } from '@mastra/redis-streams'

export const mastra = new Mastra({
  agents: { agent },
  storage: new PostgresStore({ id: 'mastra-storage', connectionString: process.env.DATABASE_URL }),
  pubsub: new RedisStreamsPubSub({ url: process.env.REDIS_URL, keyPrefix: 'mastra:my-app' }),
})
```

Serverless handler that may win the thread lease:

```typescript
const result = agent.sendSignal(signal, { resourceId, threadId })

ctx.waitUntil(
  result.accepted.then(async accepted => {
    if (accepted.action === 'wake') {
      await accepted.output.consumeStream()
    }
  }),
)
```
