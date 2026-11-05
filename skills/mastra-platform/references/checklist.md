# Mastra Platform checklist

Run this before calling a platform deploy done.

## Access

- [ ] `mastra auth whoami` succeeds, or CI has `MASTRA_API_TOKEN`, `MASTRA_ORG_ID`, `MASTRA_PROJECT_ID`
- [ ] The user, not the agent, signed in and created every token
- [ ] No secret printed, logged, pasted in chat, or committed
- [ ] Control-plane credentials kept out of the app's env files
- [ ] Target project confirmed with the user before deploying into an existing one

## Project setup

- [ ] `@mastra/core` at `1.44` or later; deploy uses `mastra deploy`, not the legacy split commands
- [ ] `.mastra-project.json` committed
- [ ] Environment and region chosen deliberately (region cannot change later)
- [ ] Storage URLs guarded by env vars; `mastra lint --preflight` passes
- [ ] Managed database attached at the right scope, and only one of Neon or Postgres per environment
- [ ] Private npm packages use a token-free `.npmrc` with `${NPM_TOKEN}` and a stored `NPM_TOKEN`

## Variables

- [ ] Every runtime key the app reads is stored on the target environment
- [ ] Env file reviewed for personal or development-only secrets before deploy
- [ ] No stored variable shadows a system variable name
- [ ] Changed variables applied with `mastra env restart <env>` or a redeploy

## Runtime

- [ ] Deploy status is `running` (`mastra env deploys <env>`)
- [ ] `<url>/health` and `<url>/api/agents` respond
- [ ] One agent call succeeds via `mastra api --url <url> agent run ...`
- [ ] API routes protected with `server.auth`; Studio uses platform auth or a configured provider
- [ ] Long turns use durable agents if they must survive a deploy
- [ ] Idle behavior understood (Persistent Server add-on if the app needs long-lived connections)

## Operations

- [ ] `MastraPlatformExporter` configured with a stable `serviceName`; traces visible
- [ ] Alerts cover Deploy failed and Service unreachable for production
- [ ] Webhook alert receivers verify `x-mastra-signature` and dedupe on `x-mastra-idempotency-key`
- [ ] CI deploy or GitHub integration in place
