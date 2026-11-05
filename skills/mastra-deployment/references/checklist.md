# Deployment checklist

Run this before calling a deployment done.

## Build

- [ ] Node.js `22.13.0` or later in build and runtime images
- [ ] `"build": "mastra build"` script exists in the deployed package
- [ ] `bundler`, `deployer`, and `server` are direct properties of `new Mastra({...})`
- [ ] Problem packages listed in `bundler.externals`; uncompiled packages in `bundler.transpilePackages`
- [ ] All `@mastra/*` packages and `mastra` on matching versions
- [ ] No database files in `src/mastra/public`
- [ ] Container images install dependencies in-image; host `node_modules` ignored
- [ ] `mastra build` succeeds locally (raise `NODE_OPTIONS` heap if needed)

## Runtime

- [ ] Storage points at a remote database on any ephemeral filesystem
- [ ] `server.timeout` covers the longest request; platform limit (for example `maxDuration`) is at least as high
- [ ] `server.drainTimeout` fits the platform's termination grace period
- [ ] Every runtime env var set on the platform, and listed in `.env.example`
- [ ] Cloudflare secrets uploaded with `wrangler secret bulk`, not `vars`
- [ ] Monorepo deploy root set to the app directory

## Scale

- [ ] Multiple replicas use shared storage, distributed PubSub, and a shared cache
- [ ] Turns that must survive restarts use durable agents (see `mastra-harness`)
- [ ] Split workers: API has `MASTRA_WORKERS=false`, exactly one scheduler, `MASTRA_STEP_EXECUTION_URL` set
- [ ] Redis or Valkey `maxmemory-policy` is `noeviction`
- [ ] First rollout starts with one replica so the schema is created once

## Security

- [ ] Server auth enabled before endpoints are public (see `mastra-auth`)
- [ ] Studio deployed only behind auth, VPN, or not at all
- [ ] HTTPS in front of the server (reverse proxy or platform TLS)
- [ ] Worker health ports private; worker token configured
- [ ] Sandbox previews hold no production secrets

## Verification

- [ ] `GET <url>/health` returns 200
- [ ] `GET <url>/api/agents` returns the expected agents
- [ ] One agent call succeeds end to end (`mastra api --url <url> agent run ...`)
- [ ] Traces arrive in the observability backend (flush on serverless)
