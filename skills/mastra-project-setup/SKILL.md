---
name: mastra-project-setup
description: "Create and configure a Mastra project: scaffold with create-mastra (default starter, templates, empty scaffold, Mastra Gateway), install manually with @mastra/core, mastra, zod, and TypeScript, set up package.json scripts and an ES2022 bundler tsconfig, lay out src/mastra, write the central new Mastra({...}) instance with agents, workflows, tools, storage, logger, server, and bundler options, load env files, and run mastra dev with Studio on localhost:4111. Use this skill whenever the user starts a new Mastra project, asks how a Mastra project is structured, wires something into src/mastra/index.ts, hits module resolution or CommonJS errors, cannot start mastra dev or Studio, or wants to use a template. Triggers on create-mastra, npm create mastra, mastra init, mastra dev, mastra build, mastra start, Studio, src/mastra/index.ts, new Mastra, @mastra/core, Mastra class, tsconfig moduleResolution bundler, .env, templates, project structure. Also triggers on set up Mastra or start a Mastra app from scratch."
license: Apache-2.0
metadata:
  category: getting-started
  catalog_summary: "create-mastra and manual install, tsconfig and ESM, src/mastra layout, the Mastra class config, env files, mastra dev and Studio"
  display_order: 2
  docs: https://mastra.ai/docs
---

# Mastra Project Setup

Get a working Mastra project on disk, configured correctly, and running in Studio. Covers the CLI scaffold, a manual install, the folder layout, the central `Mastra` instance, and the local dev loop.

---

## When to use

- Starting a new standalone Mastra project (CLI or manual)
- Choosing between the default starter, a template, and an empty scaffold
- Writing or fixing `package.json` scripts and `tsconfig.json`
- Organizing `src/mastra/` and registering primitives in `src/mastra/index.ts`
- Configuring top-level `new Mastra({...})` options: storage, logger, server, bundler, gateways
- Setting up `.env` files and model provider keys
- Running `mastra dev`, opening Studio, and reaching the local API
- Diagnosing "module not found", CommonJS, or "Studio won't start" problems

## When NOT to use

- Adding Mastra to an existing Next.js, Vite, Express, Hono, SvelteKit, or Astro app (use `mastra-framework-integration`)
- Writing agents (use `mastra-agents`), tools (use `mastra-tools`), or workflows (use `mastra-workflows`)
- File-based agents under `src/mastra/agents/<name>/` (use `mastra-file-based-agents`)
- Picking a model ID or provider env var (use `mastra-models`)
- Choosing a storage adapter in depth (use `mastra-storage`)
- Server routes, middleware, and request context (use `mastra-server`)
- `mastra build` for a host, deployers, and `mastra deploy` (use `mastra-deployment` and `mastra-cli-api`)
- Studio features beyond opening it (use `mastra-studio-editor`)
- Upgrading an old project (use `mastra-migrations`)
- Deciding what to build first (use `mastra-guide` or `mastra-build-playbook`)

---

## Required inputs

- New project or existing app (existing apps go to `mastra-framework-integration`)
- Package manager (npm, pnpm, Yarn, Bun) and Node.js version
- Model provider and API key, or the Mastra Gateway
- Whether the user wants a full starter, a specific template, or an empty scaffold
- Whether data must persist (storage) from day one

---

## The framework: scaffold, configure, run

### Option A: CLI scaffold

```bash
npx create-mastra@latest my-mastra-project --llm anthropic   # default starter, no prompts
npx create-mastra@latest my-mastra-project --template agent-harness
npx create-mastra@latest my-empty-project --empty            # no agents, no provider
```

The default starter is an agent harness with workspace tools, memory, task tracking, web access, schedules, storage, and observability. `--llm` accepts `openai`, `anthropic`, `google`, `xai`, or `mastra`. The CLI also installs Mastra skills for detected coding assistants and makes an initial Git commit (`--no-skills`, `--no-git` to skip).

### Option B: manual install

```bash
mkdir my-first-agent && cd my-first-agent && npm init -y
npm install -D typescript @types/node mastra@latest
npm install @mastra/core@latest zod@^4
```

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true,
    "types": ["node"],
    "noEmit": true,
    "outDir": "dist"
  },
  "include": ["src/**/*"]
}
```

Add `"scripts": { "dev": "mastra dev", "build": "mastra build" }` and `"type": "module"` to `package.json`.

### The central instance

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { PinoLogger } from '@mastra/loggers'
import { weatherAgent } from './agents/weather-agent'
import { weatherWorkflow } from './workflows/weather-workflow'

export const mastra = new Mastra({
  agents: { weatherAgent },
  workflows: { weatherWorkflow },
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
  logger: new PinoLogger({ name: 'Mastra', level: 'info' }),
})
```

Create one `Mastra` instance and export it as `mastra`. Registration gives each primitive shared storage, logging, tracing, Studio visibility, and HTTP endpoints.

### Layout

```text
src/mastra/
  agents/       weather-agent.ts
  tools/        weather-tool.ts
  workflows/    weather-workflow.ts
  scorers/      (optional)
  mcp/          (optional custom MCP servers)
  public/       (copied into .mastra/output on build)
  index.ts      the Mastra instance
.env.example
package.json
tsconfig.json
```

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Mastra` types. Otherwise fetch `https://mastra.ai/reference/cli/create-mastra.md`, `https://mastra.ai/reference/manual-install.md`, and `https://mastra.ai/reference/configuration.md`. Trust these over memory.
2. **Pick the path.** Human at a terminal: `create-mastra`. Coding agent without an interactive TTY: pass flags (`--llm`, `--template`, `--empty`) or do the manual install. Existing app: stop and use `mastra-framework-integration` (or `mastra init` inside the app).
3. **Configure the project.** ESM (`"type": "module"`), the tsconfig above, and `dev`/`build` scripts.
4. **Set env vars.** Put provider keys in `.env` and the names in `.env.example`. Look up names with `mastra-models`.
5. **Add one primitive.** A tool and an agent are enough to prove the setup (see examples).
6. **Register it** in `src/mastra/index.ts`. Add `storage` now if memory, workflows that suspend, or traces must persist.
7. **Run.** `npm run dev`, then open `http://localhost:4111` (Studio) and `http://localhost:4111/api` (REST). For scripts and CI, call `mastra.getAgentById(...).generate(...)` directly instead of starting Studio.
8. **Validate.** `npx tsc --noEmit` and `npx mastra lint`. Then `npm run build`.

---

## Deep dive: Mastra class options

| Option | Purpose |
|---|---|
| `agents`, `workflows`, `tools` | Registries keyed by name. Fetch with `getAgentById`, `getWorkflow`, `getTool`. |
| `storage` | One `MastraCompositeStore` for memory, workflow snapshots, traces. |
| `vectors` | Vector stores for RAG and semantic recall. |
| `memory` | Named memory instances for stored agents. |
| `logger` | `PinoLogger` from `@mastra/loggers`, or `false`. Default console logger (INFO in dev, WARN in prod). |
| `observability` | Tracing config (see `mastra-observability`). |
| `server` | `port` (4111), `host` (`localhost`), `timeout` (180000), `cors`, `apiRoutes`, `middleware`, `auth`, `studioBase`. |
| `bundler` | `externals` (default `true`), `sourcemap`, `minify`, `transpilePackages`. |
| `gateways` | Custom or Azure model gateways (see `mastra-models`). |
| `scorers`, `classifiers`, `processors`, `mcpServers`, `deployer`, `pubsub`, `workspace` | Feature-specific registries. See the owning skill. |
| `recovery` | `{ workflows: 'auto' \| 'off', durableAgents, workflowConcurrency }`. |
| `idGenerator`, `environment` | Custom IDs; environment tag for observability. |

`PORT` and `MASTRA_HOST` env vars override `server.port` and `server.host`. Full list in [`references/api.md`](references/api.md).

---

## Failure patterns

- **CommonJS settings (`"module": "commonjs"`, `"moduleResolution": "node"`).** Imports fail to resolve. Use `ES2022` plus `bundler`.
- **Running `create-mastra` interactively from an agent.** Prompts hang. Pass the project name and `--llm`, `--template`, or `--empty`, or install manually.
- **Combining `--empty` with `--template`, or `--llm` with a template.** The CLI rejects it. `--llm` and `--llm-api-key` apply to the default starter only.
- **Project name with capitals or an existing directory.** Rejected before files are written. Use a lowercase, new directory name.
- **Several `new Mastra()` instances.** Registries and storage split. Export one `mastra` from `src/mastra/index.ts`.
- **Primitive defined but not registered.** It is missing from Studio and the API. Add it to the right registry.
- **Plain object instead of `createTool()`.** Tools silently do nothing. Always use `createTool`.
- **Installing `@ai-sdk/*` packages for the model.** Not needed. Use router strings like `'openai/gpt-6.1-sol'`.
- **`.env` not loaded in a custom script.** `mastra dev` loads `.env.development`, `.env.local`, and `.env`. Plain Node scripts need your own loader or `--env-file`.
- **Port 4111 taken.** Studio fails to start. Free the port or set `PORT`.
- **Committing `.env` or `mastra.db`.** Add both to `.gitignore`; commit `.env.example`.
- **File-based agents missing when the app imports `mastra` directly.** Discovery only runs under `mastra dev` and `mastra build`.

---

## Output format

A finished setup contains:

- `package.json` with `"type": "module"`, `dev` and `build` scripts, and `@mastra/core`, `mastra`, `zod` installed
- `tsconfig.json` with ES2022 and `bundler` resolution
- `src/mastra/index.ts` exporting one `mastra` instance with every primitive registered
- At least one working agent or workflow
- `.env.example` listing every required variable, and `.gitignore` covering `.env`, `.mastra`, and local DB files
- Evidence: `mastra dev` running with Studio on `http://localhost:4111`, or a script call that returns a response, plus a clean `tsc --noEmit`

---

## Reference files

- [`references/api.md`](references/api.md) - `create-mastra` flags, `mastra` CLI dev commands and env vars, every `Mastra` constructor option with defaults, instance accessors, server and bundler options.
- [`references/examples.md`](references/examples.md) - Manual install end to end, production-leaning `index.ts`, template setup, empty scaffold plus first agent.
- [`references/checklist.md`](references/checklist.md) - New project checklist.

**Live docs**

- https://mastra.ai/docs
- https://mastra.ai/docs/develop
- https://mastra.ai/reference/cli/create-mastra
- https://mastra.ai/reference/manual-install
- https://mastra.ai/reference/project-structure
- https://mastra.ai/reference/configuration
- https://mastra.ai/reference/core/mastra-class
- https://mastra.ai/reference/templates/overview
- https://mastra.ai/reference/cli/mastra
