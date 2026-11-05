---
name: mastra-platform
description: "Deploy and operate Mastra applications on the hosted Mastra Platform: mastra deploy, projects and environments, regions, hosted Turso, Neon, and Postgres databases, the GitHub integration, Server and Studio hosting, platform workspaces, hosted observability with MastraPlatformExporter, Trace Intelligence, alerts, the control-plane REST API, and system environment variables. Use this skill whenever the user wants to ship to Mastra Platform, set up CI deploys with an API token, add a staging environment, attach a managed database, send traces to the platform from self-hosted infrastructure, configure alerts, or debug a failed platform deploy. Triggers on mastra deploy, .mastra-project.json, mastra env, mastra auth, MASTRA_API_TOKEN, MASTRA_PROJECT_ID, MASTRA_PLATFORM_ACCESS_TOKEN, MastraPlatformExporter, PlatformSandbox, @mastra/platform-workspace, projects.mastra.ai, mastra server deploy. Also triggers on preflight errors about file:./mastra.db."
license: Apache-2.0
metadata:
  category: deploy-and-platform
  catalog_summary: "mastra deploy, environments, regions, hosted databases, GitHub deploys, workspaces, hosted observability, alerts"
  display_order: 2
  docs: https://mastra.ai/docs/mastra-platform/overview
---

# Mastra Platform

Deploy a Mastra app to the hosted Mastra Platform, manage its environments and databases, and wire hosted observability, while leaving sign-in and secret creation to the human.

---

## When to use

- First deploy of a Mastra app with `mastra deploy`, or redeploys from CI
- Adding `staging` or `preview` environments, choosing the `us` or `eu` region
- Attaching a managed Turso, Neon, or Postgres database
- Linking a GitHub repository for push-to-deploy
- Using `PlatformFilesystem` and `PlatformSandbox` workspaces
- Sending traces to the platform with `MastraPlatformExporter`, including from self-hosted apps
- Configuring alerts, reading deploy status, diagnosing a failed deploy
- Moving off the deprecated `mastra server deploy` and `mastra studio deploy`

## When NOT to use

- Self-hosting on Vercel, Docker, Kubernetes, and other clouds (use `mastra-deployment`)
- Calling agents, workflows, or querying traces with `mastra api` (use `mastra-cli-api`)
- Platform Connect provider connections and `@mastra/connect` (use `mastra-tool-integrations`)
- Tracing configuration beyond the platform exporter (use `mastra-observability`)
- Storage adapter options (use `mastra-storage`)
- Workspace and sandbox APIs in depth (use `mastra-workspace-sandbox`)
- Studio features and auth inside Studio (use `mastra-studio-editor`, `mastra-auth`)
- Upgrading `@mastra/core` to reach a platform minimum version (use `mastra-migrations`)

---

## Required inputs

- Whether the user is signed in (`mastra auth whoami`) or has an API token set up for CI
- Organization and project to target, or confirmation to create a new project
- Target environment (`production` by default) and region (`us` or `eu`, fixed at creation)
- Model-provider keys and other runtime variables the app needs, and where they are stored
- Storage plan: managed database or an existing hosted one

Human steps stay human: signing up, creating an organization, `mastra auth login`, and creating API tokens. Never ask for secret values in chat, never print them, and never commit them. If a credential, org, or project is missing, stop and ask.

---

## The framework: organization, project, environment

```
Organization (team, members, API tokens, alerts)
  Project (.mastra-project.json links a directory to it)
    Environment: production | staging | preview
      URL, stored variables, deploy history, region
      Optional hosted database (environment- or project-scoped)
      Workspace: one bucket + on-demand sandboxes
```

Products on a project: **Observability** (always included), **Studio** (hosted UI, protected by platform auth), **Server** (production API).

One command builds, preflights, uploads, deploys, and streams logs:

```bash
mastra deploy
mastra deploy --env staging
mastra deploy --env production --region eu
```

The first deploy creates the project (named from `package.json`) and the `production` environment, and writes `.mastra-project.json`. Commit that file. It holds no secrets.

Project resolution order for deploys: `MASTRA_PROJECT_ID`, then `--project <name|slug|id>`, then `.mastra-project.json`.

Storage must survive the ephemeral filesystem. Guard any local path with an env var:

```ts
import { LibSQLStore } from '@mastra/libsql'

export const storage = new LibSQLStore({
  id: 'mastra-storage',
  // Uses the hosted database when deployed, a local file during development
  url: process.env.TURSO_DATABASE_URL ?? 'file:./mastra.db',
  authToken: process.env.TURSO_AUTH_TOKEN,
})
```

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/`. Fetch `https://mastra.ai/docs/mastra-platform/deploy.md` and check `mastra deploy --help`. For REST calls, check `https://platform.mastra.ai/openapi.json`. Trust these over memory.
2. **Check credentials.** Run `mastra auth whoami`. If there is no session and no `MASTRA_API_TOKEN`, ask the user to run `mastra auth login` in their own terminal. Do not read `~/.mastra/credentials.json`.
3. **Check the project link.** If `.mastra-project.json` exists, reuse it. Otherwise confirm with the user whether to create a new project or deploy into an existing one (`--project` replaces what runs there).
4. **Fix storage.** Guard local paths with env vars. Attach a managed database with `mastra env db create <env> --kind turso|neon|postgres` (admin role required).
5. **Check runtime variables.** List the keys the app reads. If they are not stored on the environment, ask the user to put them in a gitignored env file and deploy with `--env-file`. Never fill that file from your own shell.
6. **Run preflight.** `mastra lint --preflight` catches local storage paths and missing variables without deploying. It cannot see platform-stored variables.
7. **Deploy.** `mastra deploy --env <name> --yes` for non-interactive runs. Avoid `--skip-preflight`.
8. **Verify.** The CLI exits non-zero on failure and prints the Server URL on success. Hit `<url>/api/agents` and `<url>/health`, then run `mastra api --url <url> agent list` (see `mastra-cli-api`).
9. **Diagnose failures.** Run the `mastra env diagnosis <deploy-id>` command the CLI prints.
10. **Automate.** For CI, the user creates a token (`mastra auth tokens create ci-deploy`) and stores it as a CI secret with `MASTRA_ORG_ID` and `MASTRA_PROJECT_ID`. Or link GitHub for push-to-deploy.

---

## Deep dive: credentials and variables

Two credential families. Do not mix them.

| Variable | Used by | Purpose |
|---|---|---|
| `MASTRA_API_TOKEN` | CLI, control-plane REST | Headless deploys. Wins over a saved login. Requires `MASTRA_ORG_ID` and `MASTRA_PROJECT_ID`. |
| `MASTRA_ORG_ID`, `MASTRA_PROJECT_ID` | CLI | Org and project selection. |
| `MASTRA_PLATFORM_ACCESS_TOKEN` | App runtime | Observability export and workspaces. Injected on deploy. Not a deploy credential. |

Keep `MASTRA_API_TOKEN` and `MASTRA_ORG_ID` in the shell or CI secrets, not in the app's `.env`. Deploy uploads the selected env file as-is.

Variable precedence on deploy (last wins): variables stored on the environment, then managed database variables, then platform system variables (`MASTRA_ENVIRONMENT_NAME`, `MASTRA_PLATFORM_REGION`, and others). A local env file is layered on top of stored variables and saved to the environment. Apply dashboard changes without redeploying with `mastra env restart <env>`.

---

## Failure patterns

- **Preflight blocks `file:./mastra.db`.** Guard the URL with `process.env.TURSO_DATABASE_URL ?? 'file:./mastra.db'` and attach a database.
- **`Build contains a host-local storage URL`.** The path is hard-coded. Add the env var guard; the inline fix cannot help.
- **Deploy succeeds but agent calls fail.** Provider key missing on the environment. Ask the user to add it to a gitignored env file and redeploy with `--env-file`.
- **CI job hangs.** Missing `--yes`. Headless mode also needs `MASTRA_API_TOKEN`, `MASTRA_ORG_ID`, and `MASTRA_PROJECT_ID`.
- **`MASTRA_CORE_TOO_OLD`.** The environment pipeline needs `@mastra/core >= 1.44`. Upgrade, then use `mastra deploy`.
- **401.** Wrong credential type. `MASTRA_PLATFORM_ACCESS_TOKEN` cannot replace `MASTRA_API_TOKEN`.
- **403.** Role too low (viewer creating projects, non-admin creating databases or enabling workspaces).
- **Neon and Postgres attached to one environment.** Both inject `DATABASE_URL`. Use one.
- **Shared and environment-scoped database of the same provider.** Variable name conflict. Delete the shared one first (this destroys its data).
- **Stored variable ignored at runtime.** It collides with a system variable name. Rename it.
- **Server never idles.** Persistent DB connections, timers, pings, or Socket Mode chat bots keep it awake. Close idle clients or use the Persistent Server add-on.
- **Streaming turns cut off during a deploy.** The platform does not guarantee extra drain time. Use durable agents or handle interrupted streams in the client.
- **Traces missing from an EU project.** EU data lives at `https://observability.eu.mastra.ai`. Set `MASTRA_PLATFORM_OBSERVABILITY_ENDPOINT` or query with `--url`.

---

## Output format

A finished platform delivery contains:

- `.mastra-project.json` committed, with no secrets in the repo
- Storage guarded by env vars, and the attached database listed (`mastra env db list`)
- The list of runtime variable names the app needs and where each is stored
- A CI workflow using `mastra deploy --yes` with secrets, or a linked GitHub repo
- Observability configured (`MastraPlatformExporter`) with a stable `serviceName`
- Verification: deploy status `running`, `<url>/api/agents` returns JSON, one agent call succeeds

---

## Reference files

- [`references/api.md`](references/api.md) - CLI commands and flags, REST routes, env vars, regions, database kinds, alert triggers.
- [`references/examples.md`](references/examples.md) - First deploy, CI deploy, staging with its own database, hosted observability, workspaces.
- [`references/checklist.md`](references/checklist.md) - Platform deploy checklist.

**Live docs**

- https://mastra.ai/docs/mastra-platform/overview
- https://mastra.ai/docs/mastra-platform/deploy
- https://mastra.ai/docs/mastra-platform/configuration
- https://mastra.ai/docs/mastra-platform/environments
- https://mastra.ai/docs/mastra-platform/regions
- https://mastra.ai/docs/mastra-platform/database
- https://mastra.ai/docs/mastra-platform/github
- https://mastra.ai/docs/mastra-platform/server
- https://mastra.ai/docs/mastra-platform/studio
- https://mastra.ai/docs/mastra-platform/workspaces
- https://mastra.ai/docs/mastra-platform/observability
- https://mastra.ai/docs/mastra-platform/trace-intelligence
- https://mastra.ai/docs/mastra-platform/alerts
- https://mastra.ai/docs/mastra-platform/api
- https://mastra.ai/docs/mastra-platform/system-environment-variables
