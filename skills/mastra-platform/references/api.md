# Mastra Platform API reference

Distilled from `https://mastra.ai/docs/mastra-platform/*`, `https://mastra.ai/reference/cli/mastra`, and the official `mastra-ai/skills` platform reference. The platform changes often: check `mastra <command> --help` and `https://platform.mastra.ai/openapi.json` before relying on anything here.

## Contents

- Deploy commands
- Environment commands
- Database commands
- Auth commands
- Legacy commands
- Control-plane REST
- Observability endpoints
- Environment variables
- Regions
- Deploy lifecycle
- Alerts
- Workspaces

---

## Deploy commands

`mastra deploy [dir]` builds, preflights, zips `.mastra/output`, uploads, and follows the deploy to a terminal state.

| Flag | Notes |
|---|---|
| `--env <name>` | Default `production`. Auto-selects `.env.<name>` when `--env-file` is unset. Creates the environment after confirmation (type `staging` unless named `production`). |
| `--org <id>` | Or `MASTRA_ORG_ID`. |
| `--project <id\|slug\|name>` | Or `MASTRA_PROJECT_ID`. No match creates a project with that name. A match deploys into it and replaces what runs there. |
| `-y, --yes` | Accept defaults, including creating projects and environments. Required in CI. |
| `-c, --config <path>` | Default `.mastra-project.json`. |
| `--env-file <path>` | Relative to the project directory. Layered on stored variables and saved to the environment. |
| `--region <us\|eu\|code>` | Only when the CLI creates the environment. |
| `--workers dedicated\|in-process` | Background-task worker placement. `dedicated` needs `REDIS_URL`. |
| `--skip-build` | Deploy the existing `.mastra/output`. Warns when stale. |
| `--skip-preflight` | Escape hatch. Avoid. |
| `--debug` | Debug logs during build. |

Resolution order for org, project, environment: env vars, flags, `.mastra-project.json`, current org from credentials, interactive prompt. With `MASTRA_API_TOKEN` set, prompts are skipped and both `MASTRA_ORG_ID` and `MASTRA_PROJECT_ID` are required.

`mastra lint --preflight [--skip-build] [--env-file <file>] [--strict] [--json]` runs the deploy checks locally. It sees only local env files.

## Environment commands

All resolve the project from `--project`, then `MASTRA_PROJECT_ID`, then `.mastra-project.json`.

| Command | Notes |
|---|---|
| `mastra env list [--json]` | Name, region, active deploy, managed variable names. JSON omits secrets. |
| `mastra env create <name> [-t production\|staging\|preview] [-r <region>] [--json]` | Type defaults to `staging`. One `production` per project. |
| `mastra env delete <env> [-y]` | Removes its deploys and stored variables. |
| `mastra env restart <env>` | Applies changed variables without a deploy. Fails if never deployed. |
| `mastra env vars pull [<env>] [-o <file>] [-f]` | Default `.env`, mode `0600`. Managed values appear as name-only comments. |
| `mastra env deploys [<env>] [--json]` | Newest first. `(active)` marks the serving deploy. |
| `mastra env diagnosis [<deploy-id>] [--environment <env>] [--project <p>]` | Polls up to five minutes for fix suggestions. |

## Database commands

Creating and deleting requires the `admin` role (or a token with `databases:write`).

| Command | Notes |
|---|---|
| `mastra env db create [<env>] --kind turso\|neon\|postgres` | Environment-scoped by default. `--shared` for project scope. `--name`, `--region` (shared only, provider region ID such as `fra`), `--no-wait`, `--json`. Non-interactive runs need an env argument or `--shared` when several environments exist. |
| `mastra env db list [<env>] [--json]` | Kind, status, scope, injected variable names. |
| `mastra env db show <database> [--show-secrets] [--json]` | Secrets masked by default. |
| `mastra env db delete <database> [-y]` | Deletes the database and all data with the provider. |

| Kind | Engine | Network | Injected variables |
|---|---|---|---|
| `turso` | LibSQL | Public | `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` |
| `neon` | Serverless Postgres | Public | `DATABASE_URL` |
| `postgres` | Managed Postgres | Private (VPC) | `DATABASE_URL` |
| Redis (not every org) | Redis | Managed | `REDIS_URL` |

Neon and Postgres are mutually exclusive in one environment. Turso can sit beside either.

## Auth commands

Credentials live in `~/.mastra/credentials.json`. Do not read that file.

| Command | Notes |
|---|---|
| `mastra auth login` | Opens a browser. Human step. |
| `mastra auth logout` | Warns if `MASTRA_API_TOKEN` is still set. |
| `mastra auth whoami` | Email, user ID, active org. Safe to run. |
| `mastra auth orgs` / `mastra auth orgs switch` | Switch is interactive and blocked when `MASTRA_API_TOKEN` or `MASTRA_ORG_ID` is set. |
| `mastra auth tokens` | List tokens. |
| `mastra auth tokens create <name> [--permission databases:write]` | Prints the secret once. Human step. |
| `mastra auth tokens revoke <token-id>` | |

## Legacy commands

Deprecated, removed in the next major: `mastra server deploy`, `mastra studio deploy` (plus `list`, `status`, `logs`, `suggestions`), `mastra studio projects create`. Still present: `mastra server pause`, `mastra server restart`, `mastra server env list|set|unset|import|pull` (project-level variables on the legacy pipeline).

---

## Control-plane REST

Base `https://platform.mastra.ai`. Headers: `Authorization: Bearer $MASTRA_API_TOKEN`, `x-organization-id: $MASTRA_ORG_ID`.

| Route | Purpose |
|---|---|
| `GET /v1/auth/orgs` | Organizations. Org API keys get an empty list. |
| `GET /v1/projects` | List projects (list-only). |
| `POST /v1/studio/projects` | Create a project: `{"name": "..."}`, 1 to 64 chars. Returns `project.id`. |
| `GET /v1/projects/{id}` | Details, including `workspacesEnabled`. |
| `GET /v1/projects/{projectId}/environments` | Environments with `instanceUrl`. Not in the public spec. |
| `POST /v1/projects/{projectId}/environments` | `{"name","type","region"}`. Not in the public spec. |
| `GET /v1/projects/{projectId}/environment-deploys` | Deploy list with `status`, `error`, `errorCode`. Not in the public spec. |
| `GET /v1/server/projects/{id}/environments/{envId}/bucket` | Workspace bucket name and `status`. |
| `POST /v1/server/projects/{id}/workspaces/enable` | Admin only, irreversible, 409 without an environment. Ask the user first. |
| `DELETE /v1/projects/{id}` | Soft delete. `POST /v1/projects/{id}/undelete` restores. |

Documented groups: Members (`/v1/org/members`), API tokens (`/v1/auth/tokens`), Studio (`/v1/studio`), Server (`/v1/server`: env, domains, runtime logs, redeploy, always-on, deploys), Gateway (`/v1/gateway`). Never create an organization on the user's behalf.

## Observability endpoints

| Region | Root |
|---|---|
| US | `https://observability.mastra.ai/api/observability` |
| EU | `https://observability.eu.mastra.ai/api/observability` |

Headers: `Authorization: Bearer $MASTRA_PLATFORM_ACCESS_TOKEN`, optional `X-Mastra-Project-Id`. Without the project header, queries cover every project the org token can see. Gateway keys (`mk_*`) are rejected.

- Feedback (unversioned): `GET /feedback`, `POST /feedback/aggregate|breakdown|timeseries|percentiles`.
- Metrics (unversioned): `GET /metrics`, `POST /metrics/aggregate|breakdown|timeseries|percentiles`, `GET /discovery/metric-names|metric-label-keys|metric-label-values`.
- Traces: use `mastra api trace ...` (see `mastra-cli-api`).

Retention: Starter 15 days, Teams 6 months, Enterprise custom.

---

## Environment variables

| Variable | Set by | Notes |
|---|---|---|
| `MASTRA_PROJECT_ID`, `MASTRA_ENVIRONMENT_ID`, `MASTRA_ENVIRONMENT_NAME`, `MASTRA_ENVIRONMENT_SLUG` | Platform | Reserved. |
| `MASTRA_PLATFORM_REGION` | Platform | `US` or `EU`. |
| `MASTRA_PLATFORM_ACCESS_TOKEN` | Platform (deploy), user (local `sk_` token) | Exporter and workspaces. |
| `MASTRA_PLATFORM_BUCKET_NAME` | Platform | When workspaces are enabled. |
| `MASTRA_WORKERS` | Platform | `false` on the main service when workers run separately. |
| `MASTRA_PLATFORM_OBSERVABILITY_ENDPOINT` | User | For example `https://observability.eu.mastra.ai`. |
| `MASTRA_PLATFORM_STUDIO_AUTH` | User | `disabled` to use your own Studio auth. |
| `MASTRA_PLATFORM_API_URL` | User | CLI override, default `https://platform.mastra.ai`. |
| `NPM_TOKEN` | User (stored) | Private registry installs; referenced literally as `${NPM_TOKEN}` in `.npmrc`. |

## Regions

| Zone | Codes (default first) | Observability |
|---|---|---|
| `us` | `pdx`, `iad`, `sfo` | US (Iowa) |
| `eu` | `ams` | EU (Amsterdam) |

Fixed at environment creation. Unrecognized codes fall back to `us`. Environment-scoped databases follow the environment region; `--region` is ignored for them.

## Deploy lifecycle

`queued` then (`building` for GitHub deploys) `uploading`, `starting`, `deploying`, `running`. Terminal failures: `failed`, `cancelled`, `crashed`, `stopped`. One build per project at a time; newer queued deploys cancel older ones. Builds over 15 minutes fail.

## Alerts

Organization-level, admins only. Triggers: Deploy failed, Service crashed, Service out of memory, Service unreachable (3 failed health checks), Usage threshold crossed (All projects scope only). Destinations: Slack, Discord, Microsoft Teams, email, HTTPS webhook, PagerDuty, incident.io. Webhooks are signed with `x-mastra-signature: t=<unix>,v1=<hex HMAC-SHA256 of "<t>.<raw body>">` and carry `x-mastra-idempotency-key`. Any `2xx` counts as delivered; `4xx` stops as Config error; `5xx` retries up to 6 attempts. Payload `type`: `deploy.failed`, `service.crashed`, `service.oom`, `service.unreachable`, `billing.usage_threshold`.

## Workspaces

`npm install @mastra/platform-workspace`. `PlatformFilesystem` is a long-lived handle to the environment bucket. Each `PlatformSandbox` owns one remote sandbox: `start()`, `executeCommand()`, `stop()` (keeps VM), `destroy()`, `clone({ id })`. Options such as `networkIsolation` and `sandboxId`: check the installed types. A static `PlatformSandbox` is shared by every request. The sandbox does not mount the bucket.
