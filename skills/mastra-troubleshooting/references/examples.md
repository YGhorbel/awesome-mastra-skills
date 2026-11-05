# Troubleshooting examples

Worked fixes built from current docs. Each starts with the error, names the cause, and shows the fix.

## Contents

1. `Cannot use import statement outside a module`
2. Outdated tool signature after copying an old example
3. Agent forgets the conversation
4. `Memory requires a storage provider to function`
5. Handling client errors with retries

---

## 1. `Cannot use import statement outside a module`

Cause: the project is CommonJS or the compiler targets CommonJS.

Fix `package.json`: add `"type": "module"` and the Mastra scripts.

```json
{
  "type": "module",
  "scripts": {
    "dev": "mastra dev",
    "build": "mastra build"
  }
}
```

Fix `tsconfig.json`:

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

Confirm with `npx tsc --showConfig`, then `npm run dev`.

---

## 2. Outdated tool signature after copying an old example

Error: `Property 'location' does not exist`, or `requestContext` is undefined inside `execute`.

Cause: the example uses the pre-v1 single-object signature.

```diff
createTool({
    id: 'weather-tool',
-   execute: async ({ context, requestContext, mastra }) => {
-     const location = context.location;
-     const userTier = requestContext.get('userTier');
-     return getWeather(location, userTier);
-   },
+   execute: async (inputData, context) => {
+     const location = inputData.location;
+     const userTier = context?.requestContext?.get('userTier');
+     return getWeather(location, userTier);
+   },
  });
```

Suspending tools moved too:

```diff
-   execute: async ({ context, suspend, resumeData }) => {
-     if (!resumeData) {
-       return await suspend({ message: 'Waiting for approval' });
-     }
+   execute: async (inputData, context) => {
+     if (!context?.agent?.resumeData) {
+       return await context?.agent?.suspend({
+         message: 'Waiting for approval',
+       });
+     }
```

For a whole codebase, run the v1 codemods (see `mastra-migrations`):

```bash
npx @mastra/codemod@latest v1/runtime-context .
```

---

## 3. Agent forgets the conversation

Symptom: every call starts fresh.

Cause: `threadId` and `resourceId` were removed from `generate()`/`stream()` options in v1, so they are ignored.

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

Keep `thread` stable for one conversation and `resource` stable for one user. Also confirm the agent has `memory` configured and that storage exists (example 4).

If the agent instead recalls facts from other conversations, the v1 default scope is `resource`. Restore per-thread isolation:

```diff
const memory = new Memory({
    storage,
    vector,
    embedder,
    options: {
      workingMemory: {
        enabled: true,
+       scope: 'thread',
        template: `# User Profile...`,
      },
      semanticRecall: {
        topK: 3,
+       scope: 'thread',
      },
    },
  });
```

---

## 4. `Memory requires a storage provider to function`

Cause: neither the `Memory` instance nor the `Mastra` instance has storage.

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { memoryAgent } from './agents/memory-agent'

export const mastra = new Mastra({
  agents: { memoryAgent },
  storage: new LibSQLStore({
    id: 'mastra-storage',
    url: 'file:./mastra.db',
  }),
})
```

```typescript
// src/mastra/agents/memory-agent.ts
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'

export const memoryAgent = new Agent({
  id: 'memory-agent',
  name: 'Memory Agent',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    options: {
      lastMessages: 20,
    },
  }),
})
```

The agent's memory uses the Mastra instance storage. Before deploying to a serverless or platform target, switch the `file:` URL to a remote database.

---

## 5. Handling client errors with retries

Symptom: a frontend throws on transient network errors, or hangs on retries.

```typescript
import { MastraClient } from '@mastra/client-js'

const mastraClient = new MastraClient({
  baseUrl: 'http://localhost:4111',
  retries: 3,
  backoffMs: 300,
  maxBackoffMs: 5000,
})

try {
  const agent = mastraClient.getAgent('agent-id')
  const response = await agent.generate('Hello')
} catch (error) {
  console.error('An error occurred:', error.message)
}
```

If every call fails, check the server first:

```bash
curl -fsS http://localhost:4111/health
npx mastra api agent list
```

A 401 means the server has auth enabled; pass auth through `headers` (see `mastra-client-sdk` and `mastra-auth`).
