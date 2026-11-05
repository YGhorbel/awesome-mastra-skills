# Deploy targets

Every page under `https://mastra.ai/integrations/deploy/*`, plus the built-in options. Each guide deploys the Mastra server built by `mastra build` unless noted. If the app uses a server adapter or web framework, deploy it the way that framework normally deploys.

## Contents

- Comparison table
- Notes per target
- Choosing a target

---

## Comparison table

| Target | Shape | Package or tool | Entry / config | Key env vars | Caveats |
|---|---|---|---|---|---|
| Mastra server | VM, container, PaaS | `mastra` CLI | `node .mastra/output/index.mjs` or `mastra start` | `PORT` (default 4111) | You run the process manager, TLS, and reverse proxy. |
| Vercel | Serverless functions | `@mastra/deployer-vercel` | `new VercelDeployer({ studio?, maxDuration?, memory?, regions? })` | Provider keys in dashboard | Ephemeral FS. Raise `maxDuration` and `server.timeout` together. Flush observability manually. |
| Netlify | Functions or Edge | `@mastra/deployer-netlify` | `new NetlifyDeployer({ target: 'serverless' \| 'edge' })` + `netlify.toml` | Provider keys in dashboard | Ephemeral FS. Serverless 60 s default timeout. |
| Cloudflare | Workers | `@mastra/deployer-cloudflare`, `wrangler` | `new CloudflareDeployer({ name, vars, d1_databases, kv_namespaces, routes })` | `npx wrangler secret bulk .env` | Ephemeral FS. Bindings only inside `new Mastra({...})`. |
| AWS Lambda | Container image | Docker, AWS CLI, Lambda Web Adapter `0.9.1` | Dockerfile with `PORT=8080`, `AWS_LWA_READINESS_CHECK_PATH="/api"` | Provider keys, `TURSO_*` | Build with `DOCKER_BUILDKIT=0`, `--platform linux/arm64`. Timeout at least 1 minute (default 3 s). |
| Amazon Bedrock AgentCore | BYO TypeScript container | `@aws/agentcore` CLI, `bedrock-agentcore` | `BedrockAgentCoreApp` invocation handler calling `mastra.getAgentById()` | `agentcore.json` `environmentVariables` | Not the Mastra server. Read-only app dir: remove file storage. Regions limited. |
| Amazon EC2 | VM | Node 22.13+, nginx, PM2 or systemd | `node --env-file=".env" .mastra/output/index.mjs` | `.env` on the host | Open 4111 or proxy 80/443 to it. Use HTTPS. |
| Azure App Services | Managed Linux Node 22 LTS | GitHub Actions workflow | Zip only `.mastra/output` | App settings | Edit the generated workflow: drop `npm test` if unused, zip with `(cd .mastra/output && zip ../../release.zip -r .)`. Some tiers have ephemeral FS. |
| DigitalOcean App Platform | PaaS | Git connect | Build command `npm run build` | App env vars | Ephemeral FS. |
| DigitalOcean Droplets | VM | Ubuntu 24.04+, nginx, Let's Encrypt | `mastra start` | `.env` on the host | Proxy to port 4111. |
| Kubernetes | Pods behind a Service | `@mastra/redis-streams`, `@mastra/pg`, `@mastra/redis`, `ioredis` | `RedisStreamsPubSub` + `PostgresStore` + `RedisServerCache`, durable agents | `REDIS_URL`, `DATABASE_URL` | Beta. Start with one replica so the schema is created once. HPA needs CPU requests. |
| Kubernetes (Helm) | `mastra-projects` chart | Helm 3.8+, Kubernetes 1.27+ | `mastra build --studio` image, values with `existingSecret` | `DATABASE_URL`, `MASTRA_EE_LICENSE`, provider keys | Enterprise only. Private OCI registry. Exposure modes `loadBalancer`, `ingress`, `gateway`. |
| Neon | Neon Function (`fetch` handler) | Neon CLI, `@mastra/hono`, `hono`, `@neon/config` | `neon.ts` + Hono `MastraServer`, `neon deploy` | `DATABASE_URL` injected; `NEON_AI_GATEWAY_*` with `aiGateway: true` | Beta, `aws-us-east-2` only. Not `mastra build`. Idle isolates lose local state. |
| Render | Web service or Render Workflows | `@renderinc/sdk`, Render CLI 2.12+ | `task()` definitions calling Mastra agents | `OPENAI_API_KEY`, `RENDER_API_KEY` to trigger | Workflows give each task its own plan, timeout, and retries. |
| Inngest | Workflow runner | `@mastra/inngest`, `inngest@^4` | `init(inngest)`, `serve()` at `/inngest/api`, or `connect()` | `INNGEST_EVENT_KEY`, `INNGEST_SIGNING_KEY` | Never set `INNGEST_DEV` in production. Connect is beta and not for serverless. |
| Temporal | Workflow runner | `@mastra/temporal`, `@temporalio/*` | `init({ client, taskQueue })`, `MastraPlugin` worker | `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY` | Experimental. Worker must be long-lived. |
| Sandbox | Ephemeral preview | `@mastra/deployer-sandbox` + `@mastra/vercel`, `@mastra/e2b`, or `@mastra/daytona` | `new SandboxDeployer({ sandbox })` | `VERCEL_TOKEN`/`VERCEL_TEAM_ID`/`VERCEL_PROJECT_ID`, `E2B_API_KEY`, `DAYTONA_API_KEY` | Public URL, expires, not for production. `.env` is injected into the VM. |
| Mastra Platform | Managed | `mastra deploy` | `.mastra-project.json` | Stored per environment | See `mastra-platform`. |

---

## Notes per target

**Vercel.** Default build runs `npm run build`, so add `"build": "mastra build"`. With `studio: true`, Studio serves from `/` and the API stays at `/api/*`.

**Netlify.** Verify at `https://<slug>.netlify.app/api/agents`. The `.netlify/functions` prefix is not needed thanks to the redirect.

**Cloudflare.** `wrangler.jsonc` points into `.mastra/output`, so run `mastra build` before `wrangler deploy`. Protocol imports like `cloudflare:workers` are preserved during build.

**AWS Lambda.** Enable a Function URL. For production, restrict CORS, use IAM roles, and store secrets in Secrets Manager or Parameter Store.

**Bedrock AgentCore.** `npx @aws/agentcore create --name MastraOnAgentCore --no-agent`, then `add agent --type byo --build Container --language TypeScript`. The agent uses `createAmazonBedrock` from `@ai-sdk/amazon-bedrock` with `fromNodeProviderChain()`. Deploy with `npx @aws/agentcore deploy`; invoke with `npx @aws/agentcore invoke "<prompt>"`.

**Kubernetes.** Add `disableInit: true` on `PostgresStore` and run schema init as a one-off Job for stricter setups. Reconnect clients with `durableAgent.observe(runId)`.

**Helm.** Do not copy host `node_modules` into the image. Push a new tag per build (default `IfNotPresent`). Workers need `mastra-server.workers.splitDeployment: true`; the chart pins the scheduler to one replica.

**Neon.** Function slug (the `functions` key) cannot change after the first deploy. `neon dev` serves at `http://localhost:8787/api/agents`.

**Render Workflows.** `render workflows dev -- "npm run dev:workflows"` locally; create the service with `render workflows create`. Trigger from code with `new Render().workflows.startTask('<slug>/<task>', [args])`.

---

## Choosing a target

| Need | Pick |
|---|---|
| Long streams, WebSockets, background work | Mastra server on a VM, container, or Kubernetes |
| Zero ops, already on Vercel or Netlify, short requests | Vercel or Netlify deployer |
| Edge latency | Cloudflare, or Netlify `target: 'edge'` |
| AWS-native agent runtime | Bedrock AgentCore; Lambda for the full server |
| Horizontal scale with shared state | Kubernetes guide (Redis + Postgres + durable agents) |
| Managed workflow retries and memoization | Inngest |
| PR previews, CI smoke tests | Sandbox deployer |
| Hosted Studio, environments, managed databases | Mastra Platform (`mastra-platform`) |
