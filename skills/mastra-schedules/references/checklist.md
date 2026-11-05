# Schedule checklist

Run this before calling a schedule done.

## Definition

- [ ] Storage has the schedules domain (libSQL, Postgres, MySQL, MongoDB, Convex, Spanner)
- [ ] Cron validated by creating or constructing the schedule
- [ ] `timezone` set explicitly
- [ ] Stable `id` for schedules code must find again
- [ ] Threaded schedules have both `threadId` and `resourceId`
- [ ] `ifActive` and `ifIdle` chosen deliberately for threaded fires
- [ ] Declarative array entries have unique, stable `id` values

## Behavior

- [ ] Targets tolerate a skipped occurrence (no replay)
- [ ] Targets tolerate a duplicate fire (idempotent writes)
- [ ] `prepare` returns `null` to skip, an object to override, or `undefined`
- [ ] Hook logic branches on `agentId` when several agents are scheduled
- [ ] Threaded outcome handling watches the thread run, not only `onFinish`

## Deployment

- [ ] Scheduler actually runs: built server, `mastra.startWorkers()`, or one `scheduler` worker
- [ ] Exactly one scheduler instance
- [ ] Serverless hosts use Inngest cron instead
- [ ] `MASTRA_WORKERS` set on every process in a split deployment, with libSQL or Postgres for evented runs
- [ ] `schedules:write` permission granted only to operators

## Operations

- [ ] Studio `/workflows/schedules` checked after first deploy
- [ ] Runbook for pause, investigate, resume
- [ ] Logs for `Claimed schedule occurrence` and `Published schedule occurrence` monitored
