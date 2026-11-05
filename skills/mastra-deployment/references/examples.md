# Deployment examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models`. Verify package versions before copying into an older project.

## Contents

1. Standalone server in a Docker container
2. Vercel with Studio and long requests
3. Split workers with Docker Compose
4. Inngest-backed workflow served from the Mastra server
5. Sandbox preview with an E2B sandbox

---

## 1. Standalone server in a Docker container

Build outside the image, install dependencies inside it so native modules match the target platform.

```bash
mastra build
```

```dockerfile
# Dockerfile
FROM node:22-alpine

ARG MASTRA_OUTPUT=.mastra/output

WORKDIR /app

COPY ${MASTRA_OUTPUT}/package.json ${MASTRA_OUTPUT}/.npmrc* ./
RUN npm install --omit=dev

COPY ${MASTRA_OUTPUT}/ .

EXPOSE 4111
CMD ["node", "index.mjs"]
```

```text
# .dockerignore
.mastra/output/node_modules
```

Give long agent turns time to finish on rolling deploys:

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core/mastra'

export const mastra = new Mastra({
  server: {
    drainTimeout: 240_000,
  },
})
```

Verify:

```bash
curl http://localhost:4111/health
curl http://localhost:4111/api/agents
```

---

## 2. Vercel with Studio and long requests

```bash
npm install @mastra/deployer-vercel@latest
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { VercelDeployer } from '@mastra/deployer-vercel'

export const mastra = new Mastra({
  deployer: new VercelDeployer({
    studio: true,
    maxDuration: 600, // seconds
  }),
  server: {
    timeout: 600_000, // milliseconds, keep at or below maxDuration
  },
})
```

```json
{
  "scripts": {
    "build": "mastra build"
  }
}
```

Use remote storage (Vercel functions have an ephemeral filesystem). Connect the repo in Vercel, set provider keys, deploy, then check `https://<your-project>.vercel.app/api/agents`. Studio is at `/`. Protect it before sharing the URL.

For a hand-written Vercel function, flush traces before returning:

```typescript
import type { VercelRequest, VercelResponse } from '@vercel/node'
import { mastra } from '../src/mastra'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const { message } = req.body
  const agent = mastra.getAgent('myAgent')
  const result = await agent.generate([{ role: 'user', content: message }])

  await mastra.observability.flush()

  return res.json(result)
}
```

---

## 3. Split workers with Docker Compose

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core/mastra'
import { RedisStreamsPubSub } from '@mastra/redis-streams'
import { PostgresStore } from '@mastra/pg'

export const mastra = new Mastra({
  storage: new PostgresStore({
    connectionString: process.env.DATABASE_URL!,
  }),
  pubsub: new RedisStreamsPubSub({
    url: process.env.REDIS_URL!,
  }),
})
```

```bash
mastra build
mastra worker build --output-dir .mastra/worker
```

Reuse the Dockerfile from example 1. It accepts either output directory through `MASTRA_OUTPUT`.

```yaml
# docker-compose.yml
x-worker: &worker
  build:
    context: .
    args:
      MASTRA_OUTPUT: .mastra/worker

x-mastra-environment: &shared-environment
  DATABASE_URL: postgres://mastra:${POSTGRES_PASSWORD}@postgres:5432/mastra
  REDIS_URL: redis://redis:6379

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: mastra
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: mastra
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U mastra']
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: .
      args:
        MASTRA_OUTPUT: .mastra/output
    ports:
      - '4111:4111'
    environment:
      <<: *shared-environment
      WORKER_TOKEN: ${WORKER_TOKEN}
      MASTRA_WORKERS: 'false'
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ['CMD', 'wget', '-qO-', 'http://localhost:4111/api/agents']
      interval: 5s
      timeout: 3s
      retries: 5

  orchestration-worker:
    <<: *worker
    environment:
      <<: *shared-environment
      MASTRA_WORKERS: orchestration
      MASTRA_STEP_EXECUTION_URL: http://api:4111/api
      MASTRA_WORKER_AUTH_TOKEN: ${WORKER_TOKEN}
    depends_on:
      api:
        condition: service_healthy

  scheduler-worker:
    <<: *worker
    environment:
      <<: *shared-environment
      MASTRA_WORKERS: scheduler
    depends_on:
      api:
        condition: service_healthy

  background-task-worker:
    <<: *worker
    environment:
      <<: *shared-environment
      MASTRA_WORKERS: backgroundTasks
    depends_on:
      api:
        condition: service_healthy

volumes:
  pgdata:
```

Configure the API auth provider to accept `WORKER_TOKEN` (see `mastra-auth`). Scale only the scalable roles:

```bash
docker compose up -d --scale orchestration-worker=3
docker compose up -d --scale background-task-worker=2
```

---

## 4. Inngest-backed workflow served from the Mastra server

```bash
npm install @mastra/inngest@latest inngest
```

```typescript
// src/mastra/inngest.ts
import { Inngest } from 'inngest'

export const inngest = new Inngest({
  id: 'mastra',
})
```

```typescript
// src/mastra/workflows/index.ts
import { z } from 'zod'
import { inngest } from '../inngest'
import { init } from '@mastra/inngest'

const { createWorkflow, createStep } = init(inngest)

const incrementStep = createStep({
  id: 'increment',
  inputSchema: z.object({ value: z.number() }),
  outputSchema: z.object({ value: z.number() }),
  execute: async ({ inputData }) => {
    return { value: inputData.value + 1 }
  },
})

const workflow = createWorkflow({
  id: 'increment-workflow',
  inputSchema: z.object({ value: z.number() }),
  outputSchema: z.object({ value: z.number() }),
  retries: 3,
}).then(incrementStep)

workflow.commit()

export { workflow as incrementWorkflow }
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { serve } from '@mastra/inngest'
import { PinoLogger } from '@mastra/loggers'
import { incrementWorkflow } from './workflows'
import { inngest } from './inngest'

export const mastra = new Mastra({
  workflows: { incrementWorkflow },
  server: {
    host: '0.0.0.0',
    apiRoutes: [
      {
        path: '/inngest/api',
        method: 'ALL',
        createHandler: async ({ mastra }) => {
          return serve({ mastra, inngest })
        },
      },
    ],
  },
  logger: new PinoLogger({ name: 'Mastra', level: 'info' }),
})
```

Local run: `INNGEST_DEV=1 npx mastra dev`, then `npx inngest-cli@latest dev -u http://localhost:4111/inngest/api` and open `http://localhost:8288`. In production set `INNGEST_EVENT_KEY` and `INNGEST_SIGNING_KEY`, and set the app URL in the Inngest dashboard to `<origin>/inngest/api`.

---

## 5. Sandbox preview with an E2B sandbox

```bash
npm install @mastra/deployer-sandbox @mastra/e2b
npm install --save-dev dotenv-cli
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core/mastra'
import { SandboxDeployer } from '@mastra/deployer-sandbox'
import { E2BSandbox } from '@mastra/e2b'

export const mastra = new Mastra({
  deployer: new SandboxDeployer({
    sandbox: new E2BSandbox({
      id: 'my-preview',
      template: 'base',
      timeout: 3_600_000, // 1 hour
    }),
  }),
})
```

```json
{
  "scripts": {
    "deploy": "dotenv -e .env -- mastra build"
  }
}
```

`npm run deploy` prints the API and Studio URLs and writes `.mastra/output/sandbox-deployment.json`. The URL is public and the VM receives your `.env` values, so enable server auth for anything beyond a throwaway preview. Check it with a real endpoint:

```bash
curl -s -X POST https://4111-<sandbox-id>.e2b.app/api/agents/weatherAgent/generate \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Weather in London"}]}' | jq -r '.text'
```
