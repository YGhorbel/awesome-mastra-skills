# Migration examples

All code comes from the official migration guides. Run each in a clean branch with a passing baseline.

## Contents

1. Full 0.x to v1 upgrade run
2. Telemetry to observability
3. Keeping 0.x memory behavior
4. `.network()` to a supervisor agent
5. Imports, IDs, and plural getters in one file

---

## 1. Full 0.x to v1 upgrade run

```bash
git switch -c upgrade-mastra-v1
npm list @mastra/core mastra
npx tsc --noEmit && npm test

# Update everything together (add every other @mastra/* package you use)
npm install @mastra/core@latest @mastra/loggers@latest @mastra/memory@latest mastra@latest

# Mechanical changes
npx @mastra/codemod@latest v1
git add -A && git commit -m "Run Mastra v1 codemods"

# Inventory what codemods do not cover
grep -rn "telemetry:\|threadId:\|resourceId:\|format:\|offset:\|keepSeparator" src

# Database
npx mastra migrate

# Verify
npx tsc --noEmit
npm test
npm run dev
```

Node.js must be `22.13.0` or later. If you are on an old 0.x, update to the latest 0.x first.

---

## 2. Telemetry to observability

Before (0.x):

```typescript
import { Mastra } from '@mastra/core'

export const mastra = new Mastra({
  telemetry: {
    serviceName: 'my-app',
    enabled: true,
    sampling: {
      type: 'always_on',
    },
    export: {
      type: 'otlp',
      endpoint: 'http://localhost:4318',
    },
  },
})
```

After (v1):

```bash
npm install @mastra/observability
```

```typescript
import { Mastra } from '@mastra/core'
import {
  Observability,
  MastraStorageExporter,
  MastraPlatformExporter,
  SensitiveDataFilter,
} from '@mastra/observability'

export const mastra = new Mastra({
  observability: new Observability({
    configs: {
      default: {
        serviceName: 'mastra',
        exporters: [
          new MastraStorageExporter(), // Persists observability events to Mastra Storage
          new MastraPlatformExporter(), // Sends observability events to Mastra platform (if MASTRA_PLATFORM_ACCESS_TOKEN is set)
        ],
        spanOutputProcessors: [
          new SensitiveDataFilter(), // Redacts sensitive data like passwords, tokens, keys
        ],
      },
    },
  }),
})
```

For OTLP, install `@mastra/otel-exporter` and `@opentelemetry/exporter-trace-otlp-proto` (see `mastra-observability`). Confirm traces in Studio before merging. Old Mastra Cloud tokens do not work on the platform; the user creates a new one with `mastra auth tokens create`.

---

## 3. Keeping 0.x memory behavior

v1 defaults: `lastMessages` 10, semantic recall off, title generation off, scope `resource`. If the app depended on the old behavior, set it explicitly:

```diff
const memory = new Memory({
    storage,
    vector,
    embedder,
+   options: {
+     lastMessages: 40, // Was default before
+     semanticRecall: {
+       topK: 2,
+       messageRange: 2,
+       scope: 'thread',
+     }, // Was enabled by default before
+     generateTitle: true, // Was enabled by default before
+   },
  });
```

And move call options into `memory`:

```diff
await agent.stream('Hello', {
-   threadId: 'thread-123',
-   resourceId: 'user-456',
+   memory: {
+     thread: 'thread-123',
+     resource: 'user-456',
+   },
  });
```

---

## 4. `.network()` to a supervisor agent

Before:

```typescript
const result = await routingAgent.network('Research AI in education')

for await (const chunk of result) {
  if (chunk.type === 'network-execution-event-step-finish') {
    console.log(chunk.payload.result)
  }
}
```

After:

```typescript
const stream = await supervisorAgent.stream('Research AI in education', {
  maxSteps: 10,
})

for await (const chunk of stream.textStream) {
  process.stdout.write(chunk)
}
```

Then rewrite the supervisor's instructions to list each subagent and when to use it, and give every subagent a `description` (see `mastra-multi-agent`).

---

## 5. Imports, IDs, and plural getters in one file

```diff
- import { Mastra, Agent, Workflow, createTool } from '@mastra/core';
+ import { Mastra, type Config } from '@mastra/core';
+ import { Agent } from '@mastra/core/agent';
+ import { Workflow } from '@mastra/core/workflows';
+ import { createTool } from '@mastra/core/tools';
```

```diff
  const mastra = new Mastra({
    storage: new LibSQLStore({
+     id: 'mastra-storage',
      url: ':memory:',
    }),
  });
```

```diff
- const agents = mastra.getAgents();
+ const agents = mastra.listAgents();
- const workflows = mastra.getWorkflows();
+ const workflows = mastra.listWorkflows();
```

Codemods for these: `v1/mastra-core-imports` and `v1/mastra-plural-apis`. The `id` additions are manual.
