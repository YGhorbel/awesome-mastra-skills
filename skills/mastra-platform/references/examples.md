# Mastra Platform examples

All examples follow the current docs. Secrets come from the user: they sign in, create tokens, and fill env files themselves.

## Contents

1. First deploy from a signed-in terminal
2. Headless deploy from GitHub Actions
3. Staging environment with its own database
4. Hosted observability for a self-hosted app
5. Platform workspace for agent files and commands

---

## 1. First deploy from a signed-in terminal

Check the session. If it fails, ask the user to run `mastra auth login` in their own terminal.

```bash
mastra auth whoami
```

Guard storage so preflight passes:

```ts
// src/mastra/storage.ts
import { LibSQLStore } from '@mastra/libsql'

export const storage = new LibSQLStore({
  id: 'mastra-storage',
  // Uses the hosted database when deployed, a local file during development
  url: process.env.TURSO_DATABASE_URL ?? 'file:./mastra.db',
  authToken: process.env.TURSO_AUTH_TOKEN,
})
```

```ts
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { storage } from './storage'

export const mastra = new Mastra({
  storage,
})
```

Run preflight, then deploy. Accept the inline offer to create a managed Turso database, or create it explicitly once the environment exists:

```bash
mastra lint --preflight
mastra deploy --project "my-new-project" --yes
mastra env db create production --kind turso
```

The user puts provider keys in a gitignored `.env.production`. Deploy again so the keys are stored on the environment:

```bash
mastra deploy --env-file .env.production --yes
```

Commit `.mastra-project.json`. Verify at the printed URL plus `/api/agents`.

---

## 2. Headless deploy from GitHub Actions

The user runs `mastra auth tokens create ci-deploy` locally and saves the value as the `MASTRA_API_TOKEN` secret, plus `MASTRA_ORG_ID` and `MASTRA_PROJECT_ID` from `.mastra-project.json`.

```yaml
# .github/workflows/deploy.yml
name: Deploy to Mastra platform
on:
  push:
    branches: [main]
    paths: ['src/mastra/**']
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - name: Install dependencies
        run: npm install
      - name: Deploy to Mastra platform
        run: npx mastra deploy --yes
        env:
          MASTRA_API_TOKEN: ${{ secrets.MASTRA_API_TOKEN }}
          MASTRA_ORG_ID: ${{ secrets.MASTRA_ORG_ID }}
          MASTRA_PROJECT_ID: ${{ secrets.MASTRA_PROJECT_ID }}
```

For GitLab, set the same three CI/CD variables and run `npx mastra deploy --yes`. For a repo on GitHub, linking it in the dashboard gives push-to-deploy without a workflow file.

---

## 3. Staging environment with its own database

```bash
mastra env create staging --type staging --region eu
mastra env db create staging --kind turso
mastra deploy --env staging --env-file .env.staging --yes
mastra env deploys staging
```

Production and staging now read separate databases. To see the variables staging runs with (managed values appear as name-only comments):

```bash
mastra env vars pull staging --output .env.staging.pulled
```

If a deploy fails:

```bash
mastra env diagnosis --environment staging
```

For Postgres instead of Turso, use `--kind neon` (public) or `--kind postgres` (private network) and read `DATABASE_URL`:

```ts
import { PostgresStore } from '@mastra/pg'

export const storage = new PostgresStore({
  connectionString: process.env.DATABASE_URL!,
})
```

---

## 4. Hosted observability for a self-hosted app

`mastra init` (existing project) or `npm create mastra@latest` (new project) can provision this and write the variables. Manual setup: the user creates an access token in the dashboard and adds it to `.env`:

```bash
MASTRA_PLATFORM_ACCESS_TOKEN=<your-platform-access-token>
MASTRA_PROJECT_ID=<your-project-id>
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core/mastra'
import { MastraPlatformExporter, MastraStorageExporter, Observability } from '@mastra/observability'

export const mastra = new Mastra({
  observability: new Observability({
    configs: {
      default: {
        serviceName: 'my-service',
        exporters: [new MastraPlatformExporter(), new MastraStorageExporter()],
      },
    },
  }),
})
```

`MastraStorageExporter` is optional; it keeps a copy for local Studio. For an EU project, set `MASTRA_PLATFORM_OBSERVABILITY_ENDPOINT=https://observability.eu.mastra.ai`. Check data arrives:

```bash
npx mastra api trace list '{"page":0,"perPage":5}'
```

---

## 5. Platform workspace for agent files and commands

```bash
npm install @mastra/platform-workspace
```

```typescript
// src/mastra/workspace.ts
import { Workspace } from '@mastra/core/workspace'
import { PlatformFilesystem, PlatformSandbox } from '@mastra/platform-workspace'

export const workspace = new Workspace({
  filesystem: new PlatformFilesystem(),
  sandbox: new PlatformSandbox(),
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { workspace } from './workspace'

export const mastra = new Mastra({
  workspace,
})
```

Isolate a task in its own sandbox:

```typescript
import { PlatformSandbox } from '@mastra/platform-workspace'

export async function runInFreshSandbox(command: string) {
  const sandbox = new PlatformSandbox()
  await sandbox.start()
  try {
    return await sandbox.executeCommand(command)
  } finally {
    await sandbox.destroy()
  }
}
```

On the platform, all four variables are injected. Locally, the user adds `MASTRA_PLATFORM_ACCESS_TOKEN` (an `sk_` org token), `MASTRA_PROJECT_ID`, `MASTRA_ENVIRONMENT_ID`, and `MASTRA_PLATFORM_BUCKET_NAME` from the Workspaces tab, preferably for a staging environment.
