# Signals checklist

Run this before calling a signals integration done.

## Basics

- [ ] Agent has Memory with storage, and is registered on `Mastra`
- [ ] Thread subscription opened before input is sent
- [ ] `accepted` awaited where routing failures matter
- [ ] Each input uses the right type (message, queued message, reactive signal, state, notification)
- [ ] `tagName` and attribute names are XML-safe
- [ ] Forwarded third-party text treated as untrusted (signals are not an injection defense)
- [ ] `ifActive` and `ifIdle` overridden only where defaults are wrong

## State signals

- [ ] Lane starts with a snapshot, later updates change `cacheKey`
- [ ] Frequent changes batched or summarized before sending
- [ ] Fresh snapshot sent when `contextWindow.hasSnapshot` is false
- [ ] Target thread exists before the first state signal

## Notifications

- [ ] Storage has the notifications domain (libSQL, Postgres, MongoDB)
- [ ] Every event has a stable `dedupeKey` or `coalesceKey`
- [ ] Important facts are in `summary`, not only `payload`
- [ ] Delivery policy reviewed, `decide()` side-effect free
- [ ] Inbox tool added so the agent can read summarized records
- [ ] Dispatcher enabled if anything is deferred or summarized
- [ ] `failed` records monitored

## Providers

- [ ] Subscriptions persisted and rehydrated in `start()` if they must survive restarts
- [ ] Webhook signatures verified on the raw body
- [ ] Provider routes avoid the `/api` prefix and set auth deliberately
- [ ] `stop()` called on shutdown

## Multiple processes

- [ ] Shared storage and a PubSub backend with leases on every instance
- [ ] Same `keyPrefix` across coordinating instances, different per environment
- [ ] Lease env vars consistent across instances
- [ ] Handlers idempotent (delivery is at-least-once)
- [ ] Serverless `wake` kept alive with `waitUntil`
