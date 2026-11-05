---
name: mastra-deployment
description: "Deploy a Mastra application to production: the standalone server from mastra build, deployers for Vercel, Netlify, and Cloudflare, Docker and VMs, Kubernetes, AWS Lambda, Bedrock AgentCore, Azure, DigitalOcean, Render, Neon, sandbox previews, split worker processes, and workflow runners such as Inngest and Temporal. Use this skill whenever the user wants to ship, host, containerize, or scale a Mastra project, pick a hosting target, fix a build or deploy failure, or run workflows on managed infrastructure. Triggers on mastra build, mastra start, .mastra/output, VercelDeployer, NetlifyDeployer, CloudflareDeployer, SandboxDeployer, @mastra/deployer-vercel, @mastra/deployer-netlify, @mastra/deployer-cloudflare, @mastra/deployer-sandbox, bundler externals, transpilePackages, drainTimeout, MASTRA_WORKERS, mastra worker build, @mastra/inngest, @mastra/temporal, Dockerfile, Helm. Also triggers when a deployed app loses data because LibSQLStore points at a local file, or when requests time out on serverless."
license: Apache-2.0
metadata:
  category: deploy-and-platform
  catalog_summary: "Server build, cloud deployers, containers, Kubernetes, sandbox previews, workers, Inngest and Temporal runners"
  display_order: 1
  docs: https://mastra.ai/docs/deployment/overview
---

# Mastra Deployment

Choose a hosting target for a Mastra application, build it correctly, and run it in production with persistent storage, sane timeouts, and authentication.

---

## When to use

- Picking where to host a Mastra app (VM, container, serverless, edge, Kubernetes)
- Running `mastra build` and serving `.mastra/output` with `mastra start` or Node
- Configuring `VercelDeployer`, `NetlifyDeployer`, `CloudflareDeployer`, or `SandboxDeployer`
- Writing a Dockerfile, Kubernetes manifests, or Helm values for Mastra
- Splitting orchestration, scheduler, and background-task workers into their own processes
- Running workflows on Inngest or Temporal
- Fixing build failures (heap size, bundling, monorepo packages) or serverless timeouts

## When NOT to use

- Deploying to the hosted Mastra Platform with `mastra deploy` (use `mastra-platform`)
- CLI flags and `mastra api` calls against a deployed server (use `mastra-cli-api`)
- Server routes, middleware, CORS, server adapters for Express or Hono (use `mastra-server`)
- Next.js, Astro, or other framework integration code (use `mastra-framework-integration`)
- Choosing and configuring a database adapter (use `mastra-storage`)
- Securing endpoints and Studio (use `mastra-auth`)
- Durable agents, crash recovery, background tasks semantics (use `mastra-harness`)
- Cron schedules on workflows (use `mastra-schedules`)
- Tracing exporters and flushing (use `mastra-observability`)

---

## Required inputs

- Hosting target, or the constraints that pick one (long-running streams, WebSockets, scale to zero, existing cloud)
- Storage in use and whether it is reachable from the target (remote URL, not `file:` on ephemeral disks)
- Expected request duration (agent streams and workflow runs often exceed default serverless limits)
- Package manager and repo layout (single package or monorepo path such as `apps/api`)
- Whether Studio should ship with the API, and how it will be protected
- Provider env vars the app needs at runtime (model keys, database URLs)

Ask for the target and storage first. Everything else follows from them.

---

## The framework: build once, pick an output shape

`mastra build` bundles `src/mastra/index.ts` into a self-contained Hono server. A deployer changes the output shape for a specific platform.

| Option | Output | Use when |
|---|---|---|
| Mastra server (no deployer) | `.mastra/output/index.mjs` | VMs, containers, PaaS, Kubernetes, long-running streams |
| `VercelDeployer` | `.vercel/output` (Build Output API) | Vercel serverless functions |
| `NetlifyDeployer` | `.netlify/v1` | Netlify Functions or Edge Functions |
| `CloudflareDeployer` | `wrangler.jsonc` pointing at `.mastra/output` | Cloudflare Workers |
| `SandboxDeployer` | Live sandbox URL | Previews, CI checks, agent-built apps |
| Server adapter or web framework | Your app's normal build | Mastra inside Express, Hono, Next.js, Astro |
| Mastra Platform | `mastra deploy` | Managed hosting (see `mastra-platform`) |

Runtimes: Node.js `v22.13.0` or later, Bun, Deno, Cloudflare.

Minimal build and run:

```bash
mastra build
mastra start
# or
node .mastra/output/index.mjs
```

Build-time options (`bundler`, `deployer`, `server`) must be direct properties of the object passed to `new Mastra()`:

```typescript
import { Mastra } from '@mastra/core/mastra'

export const mastra = new Mastra({
  bundler: {
    externals: ['sharp'],
  },
  server: {
    port: 4111,
  },
})
```

Do not hide them behind a factory call (`new Mastra(createMastraOptions())`) or a spread (`new Mastra({ ...options })`). The build cannot extract them and silently falls back to defaults.

Every built-in route lives under `/api`. Verify any deployment with `GET /api/agents` (JSON list of agents) or `GET /health`.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed deployer package docs. Otherwise fetch `https://mastra.ai/docs/deployment/overview.md` and the target page from `references/targets.md` with `.md` appended. Trust these over memory.
2. **Pick the target.** Use `references/targets.md`. Prefer a long-running server for streaming agents and long workflows. Use serverless only when request duration fits.
3. **Fix storage first.** Ephemeral filesystems (Vercel, Netlify, Cloudflare, Lambda, DigitalOcean App Platform, some Azure tiers) lose `file:` databases. Point storage at a remote database. Keep database files out of `src/mastra/public`.
4. **Add a deployer if the target needs one.** Install `@mastra/deployer-<target>@latest` and set `deployer:` on `new Mastra()`.
5. **Set timeouts.** Raise `server.timeout` (ms, default `180000`) alongside any platform limit such as Vercel `maxDuration` (seconds).
6. **Set graceful shutdown.** Size `server.drainTimeout` (default 5 s) to the platform's termination grace period. Use durable agents when turns must survive restarts.
7. **Build.** Run `mastra build` (add `--studio` to bundle Studio). For monorepos run the package's `build` script from the workspace tool.
8. **Configure env vars on the platform.** `mastra start` loads `.env.production` and `.env`. Most platforms need variables set in their dashboard. Cloudflare secrets go through `npx wrangler secret bulk .env`.
9. **Deploy and verify.** Hit `<url>/api/agents` and `<url>/health`. Then exercise one agent with `mastra api --url <url> agent list` (see `mastra-cli-api`).
10. **Secure it.** Enable server auth before exposing endpoints or Studio publicly (see `mastra-auth`).

---

## Deep dive: scaling and workers

One process runs everything by default: API, workflow orchestration, cron scheduler, and background tool calls. Scale out only when needed.

Multiple API replicas need shared infrastructure, or work started on one pod is invisible to the others:

- A distributed PubSub (`RedisStreamsPubSub`, `ValkeyStreamsPubSub`, or `GoogleCloudPubSub`)
- Shared storage (for example `PostgresStore`)
- A shared cache (`RedisServerCache`) for resumable streams
- Durable agents (`createDurableAgent`) for streams and approvals that cross pods

Split workers run the same build with different `MASTRA_WORKERS` values:

```bash
mastra build
mastra worker build --output-dir .mastra/worker
```

| Process | `MASTRA_WORKERS` | Replicas |
|---|---|---|
| API | `false` | Any |
| Orchestration | `orchestration` | Scale out; needs `MASTRA_STEP_EXECUTION_URL=http://api:4111/api` |
| Scheduler | `scheduler` | Exactly one |
| Background tasks | `backgroundTasks` | Scale out |

Always pass `--output-dir` to `mastra worker build`. Its default is `.mastra/output`, which overwrites the server bundle. Workers are beta. See `references/examples.md` for the Docker Compose layout.

---

## Failure patterns

- **Data vanishes after a deploy or cold start.** `LibSQLStore` uses `file:./mastra.db` on an ephemeral disk. Point it at a remote database (Turso, Postgres).
- **`504 Gateway Timeout` after 180 s on Vercel despite a high `maxDuration`.** `server.timeout` still applies. Raise both.
- **Build options ignored.** `bundler`, `deployer`, or `server` hidden in a spread or factory. Make them direct properties of `new Mastra({...})`.
- **`JavaScript heap out of memory` during build.** Run `NODE_OPTIONS="--max-old-space-size=4096" mastra build`.
- **Package fails to bundle.** Add it to `bundler.externals`. For uncompiled workspace packages, add to `bundler.transpilePackages`.
- **Monorepo deploy builds the wrong thing.** The platform root points at the repo root. Set it to the app directory (`apps/api`). Keep `.env` in that directory.
- **`Cannot find module '@libsql/linux-x64-gnu'` in a container.** Host-built `node_modules` was copied. Install dependencies inside the image and ignore `.mastra/output/node_modules`.
- **`/api` returns Not Found on a healthy server.** `/api` is only a prefix. Call `/api/agents`.
- **Sandbox deploy fails with an auth error.** `mastra build` does not load `.env`. Load it into the shell (`dotenv -e .env -- mastra build`) or export CI secrets.
- **Cloudflare binding is `undefined`.** It was read outside `new Mastra({...})`. Keep `env.X` usage inline in the constructor call.
- **Inngest route throws at startup.** A custom route under `/api`. Use `/inngest/api`, or move built-ins with `server.apiPrefix`.
- **Duplicate cron fires.** More than one scheduler, or the API also runs workers. Run one scheduler and set `MASTRA_WORKERS=false` on the API.
- **Traces missing on serverless.** The function exits before export. `await mastra.observability.flush()` before returning.
- **Temporal worker on Lambda or Vercel.** The worker must be long-lived. Use a container or VM.

---

## Output format

A finished deployment delivery contains:

- The `src/mastra/index.ts` change (deployer, `bundler`, `server.timeout`, `server.drainTimeout`) if needed
- A `build` script (`"build": "mastra build"`) and platform config (`netlify.toml`, `Dockerfile`, manifests, values file)
- Remote storage configured through env vars, with no `file:` URLs on ephemeral targets
- An `.env.example` listing every runtime variable (never commit `.env`)
- The verification result: `GET <url>/api/agents` returns JSON, `GET <url>/health` returns 200
- A note on how endpoints and Studio are protected

---

## Reference files

- [`references/api.md`](references/api.md) - Deployer constructors, bundler and server options, env vars, worker and runner APIs.
- [`references/targets.md`](references/targets.md) - Every deploy target with package, entry shape, env vars, and caveats.
- [`references/examples.md`](references/examples.md) - Docker server, Vercel with Studio, split workers with Compose, Inngest workflows, sandbox preview.
- [`references/checklist.md`](references/checklist.md) - Pre-production deployment checklist.

**Live docs**

- https://mastra.ai/docs/deployment/overview
- https://mastra.ai/docs/deployment/mastra-server
- https://mastra.ai/docs/deployment/monorepo
- https://mastra.ai/docs/deployment/cloud-providers
- https://mastra.ai/docs/deployment/web-framework
- https://mastra.ai/docs/deployment/sandbox
- https://mastra.ai/docs/deployment/workers
- https://mastra.ai/docs/deployment/workflow-runners
- https://mastra.ai/reference/deployer
- https://mastra.ai/reference/configuration
