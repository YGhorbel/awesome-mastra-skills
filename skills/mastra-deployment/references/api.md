# Deployment API reference

Distilled from `https://mastra.ai/reference/deployer`, `reference/deployer/{vercel,netlify,cloudflare}`, `reference/configuration`, `reference/workers/overview`, `docs/deployment/*`, and `integrations/deploy/{inngest,temporal}`. Verify against the installed version before relying on an option.

## Contents

- Build output and CLI
- Build-time configuration (`bundler`, `server`)
- Environment variables
- VercelDeployer
- NetlifyDeployer
- CloudflareDeployer
- SandboxDeployer and sandbox client
- Custom `Deployer`
- Workers
- Inngest
- Temporal

---

## Build output and CLI

```text
.mastra/output/
  index.mjs        # Server entry point
  mastra.mjs       # Bundled Mastra configuration
  tools.mjs, tools/
  package.json, node_modules/, .npmrc (if present)
  <src/mastra/public contents>
  playground/      # Studio UI, only with --studio
```

| Command | Notes |
|---|---|
| `mastra build` | Bundles with Rollup, generates a Hono server, runs `npm install` in the output. `--studio` bundles Studio. Common flags: `--dir`, `--root`, `--tools`, `--debug`. |
| `mastra start` | Serves the build. Loads `.env.production` and `.env`. `--dir` (default `.mastra/output`), `--custom-args`. |
| `mastra worker build` | Worker bundle. `--output-dir` defaults to `.mastra/output` (overwrites the server bundle). |
| `mastra worker start [name]` | `name` sets `MASTRA_WORKERS`. `--dir`, `--env` (default `.env.production`, then `.env`). |

Build steps: locate entry file, discover `{mastraDir}/tools/**/*.{js,ts}`, analyze dependencies, bundle, generate `index.mjs`, install dependencies, copy `public` and `.npmrc`.

Built-in endpoints: `GET /health`, `GET /api/openapi.json` (if `server.build.openAPIDocs`), `GET /swagger-ui` (if `server.build.swaggerUI`). Run `mastra dev` and open `http://localhost:4111/swagger-ui` for the full list.

---

## Build-time configuration

Keep these as direct properties of the object passed to `new Mastra()`.

| Option | Type / default | Notes |
|---|---|---|
| `bundler.externals` | `boolean \| string[]`, default `true` | `true`: every `package.json` dependency is external. `false`: bundle everything. Array: only those external. |
| `bundler.sourcemap` | `boolean`, `false` | Also runs `mastra dev`/`start` with `--enable-source-maps`. |
| `bundler.minify` | `boolean`, `false` | Never applied to `mastra dev`. |
| `bundler.transpilePackages` | `string[]`, `[]` | Uncompiled TypeScript packages. Workspace packages are detected automatically. |
| `bundler.pnpmWorkspaceSettings` | `Record<string, JSONValue>`, `{}` | Only `allowBuilds`, `onlyBuiltDependencies`, `ignoredBuiltDependencies`, `minimumReleaseAge`, `minimumReleaseAgeExclude`, `trustPolicy`, `trustPolicyExclude`, `trustPolicyIgnoreAfter`, `blockExoticSubdeps`. |
| `deployer` | `IDeployer` | A deployer instance. |
| `server.port` | `number` | Replaces the removed `mastra dev --port`. |
| `server.timeout` | `number`, `180000` ms | Requests over it get `504`. Independent of platform limits. |
| `server.drainTimeout` | `number`, `5000` ms | HTTP drain then workflow drain on `SIGINT`/`SIGTERM`. `0` skips both. |
| `server.handleShutdownSignals` | `boolean`, `true` | Set `false` to manage signals yourself. |
| `server.apiPrefix` | `string`, `/api` | Custom `apiRoutes` under this prefix throw at startup. |

```typescript
await mastra.shutdown({ drainTimeout: 30_000 })
```

---

## Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `PORT` | Server, workers | Default `4111`. |
| `MASTRA_STUDIO_PATH` | Server | Studio build path, default `./playground`. |
| `MASTRA_SKIP_DOTENV` | Server | Skip loading `.env` files. |
| `NODE_OPTIONS` | Build | For example `--max-old-space-size=4096`. |
| `MASTRA_BUILD_SKIP_INSTALL` | Build | `true` or `1` skips lockfile update and output install (hermetic builds). |
| `MASTRA_SKIP_PEERDEP_CHECK` | Build, dev | `1` skips the peer dependency check. |
| `MASTRA_CONCURRENCY` | Build, dev | Caps parallel expensive tasks. |
| `MASTRA_WORKERS` | Every process in a split deploy | `false`, `orchestration`, `scheduler`, `backgroundTasks`, or a comma list. |
| `MASTRA_STEP_EXECUTION_URL` | Orchestration worker | API internal URL including `/api`. |
| `MASTRA_WORKER_AUTH_TOKEN` | Orchestration worker | Bearer token the API auth provider accepts. |

---

## VercelDeployer

`npm install @mastra/deployer-vercel@latest`, `import { VercelDeployer } from '@mastra/deployer-vercel'`

| Option | Notes |
|---|---|
| `studio?: boolean` | Default `false`. Serves Studio as static assets from the Edge CDN. |
| `maxDuration?: number` | Function timeout in seconds. Does not change `server.timeout`. |
| `memory?: number` | MB. |
| `regions?: string[]` | For example `['sfo1', 'iad1']`. |

Writes `.vercel/output/{config.json,functions/index.func/,static/}`. Options merge into `.vc-config.json`. Do not commit `.vercel/output`. With Studio, routes Studio owns (for example `/agents`) shadow custom routes at the same path.

## NetlifyDeployer

`npm install @mastra/deployer-netlify@latest`, `import { NetlifyDeployer } from '@mastra/deployer-netlify'`

| Option | Notes |
|---|---|
| `target?: 'serverless' \| 'edge'` | Default `'serverless'` (Node, 60 s default timeout). `'edge'` runs on Deno with a CPU limit, no fixed timeout. |

Writes `.netlify/v1/config.json` and `functions/api/` (or `edge-functions/`). Redirects `/*` to `/.netlify/functions/api/:splat`. Needs `netlify.toml` with `[build] command = "mastra build"`.

## CloudflareDeployer

`npm install @mastra/deployer-cloudflare@latest`, `import { CloudflareDeployer } from '@mastra/deployer-cloudflare'`

Accepts the same options as `wrangler.jsonc` (`name`, `routes`, `vars`, `d1_databases`, `kv_namespaces`, ...). v1 renamed `projectName` to `name`, `d1Databases` to `d1_databases`, `kvNamespaces` to `kv_namespaces`, and removed `workerNamespace`.

- `.env` values are not written to `wrangler.jsonc`. Upload secrets: `npx wrangler secret bulk .env`.
- `vars` is for non-sensitive values only.
- `import { env } from 'cloudflare:workers'` works. Use `env.X` only inside `new Mastra({...})`.

## SandboxDeployer and sandbox client

`npm install @mastra/deployer-sandbox` plus a provider (`@mastra/vercel`, `@mastra/e2b`, `@mastra/daytona`).

| API | Import | Notes |
|---|---|---|
| `new SandboxDeployer({ sandbox, alias? })` | `@mastra/deployer-sandbox` | `mastra build` deploys into the sandbox, prints API and Studio URLs, writes `.mastra/output/sandbox-deployment.json`. `alias: { edgeConfigId, key, token }` keeps a Vercel Edge Config item updated. |
| `deployToSandbox({ sandbox, dir, studio? })` | `@mastra/deployer-sandbox` | Deploys a prebuilt directory. Studio off unless `studio: true`. Returns `{ url, logs(), stop(), destroy() }`. |
| `getDeployment({ sandbox, port?, wake? })` | `@mastra/deployer-sandbox/client` | Server only. `wake: true` resumes and relaunches if unhealthy. Returns `status`, `url`, `expiresAt`, lifecycle methods. |
| `createSandboxHandler({ resolve, secret? })` | `@mastra/deployer-sandbox/client` | Route handler proxy that re-resolves on connection failure. |
| `createSandboxProxy({ key, secret? })` | `@mastra/deployer-sandbox/client` | Next.js middleware rewrite using the Edge Config alias. |

Provider identity: Vercel `sandboxName` (also needs `ports: [4111]`, `timeout` within plan limit, 45 min on Pro), E2B `id` (pass `template: 'base'`), Daytona `id` (`public: true` for tokenless URLs). Credentials: `E2B_API_KEY`, `DAYTONA_API_KEY`, `VERCEL_TOKEN`, `VERCEL_TEAM_ID`, `VERCEL_PROJECT_ID`. The deployer injects `.env`, `.env.production`, `.env.local` into the sandbox. `secret` is sent as `x-mastra-sandbox-secret`.

## Custom Deployer

```typescript
import { Deployer } from '@mastra/deployer'

class CustomDeployer extends Deployer {
  constructor() {
    super({ name: 'custom-deployer' })
  }

  async deploy(outputDirectory: string): Promise<void> {
    await this.prepare(outputDirectory)
    await this._bundle('server.ts', 'mastra.ts', {
      projectRoot: process.cwd(),
      outputDirectory,
    })
    // Custom deployment logic
  }
}
```

Methods: `getEnvFiles()` (existing files among `.env`, `.env.local`, `.env.production`, later wins), `prepare(dir)`, `writePackageJson(dir, deps, resolutions?)`, `_bundle(serverFile, mastraEntryFile, options, toolsPaths?, bundleLocation?)`.

---

## Workers

Beta. Types: `orchestration` (topic `workflows`, group `mastra-orchestration`, pull-capable PubSub required), `scheduler` (single instance only, polls storage), `backgroundTasks` (topic `background-tasks`, group `background-task-workers`, scales out).

- Distributed PubSub: `RedisStreamsPubSub` (`@mastra/redis-streams`), `ValkeyStreamsPubSub`, `GoogleCloudPubSub` (`@mastra/google-cloud-pubsub`).
- Storage with the `schedules` domain: `@mastra/pg`, `@mastra/libsql`, `@mastra/mysql`, `@mastra/mongodb`, `@mastra/spanner`, `@mastra/convex`. Others support orchestration and background tasks only.
- Worker processes expose `GET /health` on `PORT` (503 while starting, 200 when ready). Keep that port private.
- Server adapters must call `mastra.startWorkers()` after the server listens.
- Setting `MASTRA_WORKERS` to any value moves workflows with `schedule` to the evented engine. Set it on every process.
- Redis or Valkey must use `maxmemory-policy noeviction`.

## Inngest

`npm install @mastra/inngest@latest inngest` (needs `inngest@^4`, Dev Server `v1.18.0`+).

| API | Notes |
|---|---|
| `init(inngest)` | Returns `{ createWorkflow, createStep }`. Workflow options add `concurrency`, `rateLimit`, `throttle`, `debounce`, `priority`, `retries` (default `0`), `cron`, `inputData`, `initialState`. |
| `serve({ mastra, inngest, functions? })` | Hono handler. Mount as a custom route at `/inngest/api` with `method: 'ALL'`. |
| `createServe(adapter)({ mastra, inngest })` | For Express, Fastify, Koa, Next.js adapters from `inngest/<framework>`. |
| `connect({ mastra, inngest, instanceId?, maxWorkerConcurrency?, functions?, registerOptions? })` | From `@mastra/inngest/connect`. Outbound worker connection. Not for serverless. |

Function IDs: `workflow.${workflowId}`, cron functions `workflow.${workflowId}.cron`. Env: `INNGEST_DEV` (never in production), `INNGEST_EVENT_KEY`, `INNGEST_SIGNING_KEY`.

## Temporal

Experimental, not production ready. `npm install @mastra/temporal@latest @temporalio/client @temporalio/worker @temporalio/envconfig`

| API | Notes |
|---|---|
| `init({ client, taskQueue, startToCloseTimeout?, retry? })` | Returns `{ createWorkflow, createStep }`. `startToCloseTimeout` default `1 minute`. Omitting `retry` means unlimited attempts. Keep options statically analyzable. |
| `new MastraPlugin(import.meta.resolve('./index.ts'))` | From `@mastra/temporal/worker`. Pass in `Worker.create({ plugins })`. Do not pass `activities`. |

Workflow ids must be static string literals. Use `z.coerce.date()` for dates. Env: `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY`.
