# Workspace examples

All examples follow the current docs at `https://mastra.ai/docs/sandbox/*`. Verify provider options against the installed package before copying.

## Contents

1. Isolated local coding agent with tool policies
2. S3 bucket mounted into an E2B sandbox
3. One Daytona sandbox per user, with network limits and cleanup
4. Searchable knowledge base with auto-indexing

---

## 1. Isolated local coding agent with tool policies

```typescript
// src/mastra/workspace.ts
import { LocalFilesystem, LocalSandbox, Workspace, WORKSPACE_TOOLS } from '@mastra/core/workspace'

// Absolute path: relative paths resolve differently under `mastra dev` and `mastra start`
const projectPath = process.env.WORKSPACE_PATH!

export const workspace = new Workspace({
  id: 'coding-workspace',
  filesystem: new LocalFilesystem({ basePath: projectPath }),
  sandbox: new LocalSandbox({
    workingDirectory: projectPath,
    isolation: 'bwrap', // 'seatbelt' on macOS. Check LocalSandbox.detectIsolation()
    nativeSandbox: {
      allowNetwork: false,
    },
    env: { NODE_ENV: 'development' }, // only PATH is passed by default
  }),
  tools: {
    [WORKSPACE_TOOLS.FILESYSTEM.WRITE_FILE]: { requireReadBeforeWrite: true },
    [WORKSPACE_TOOLS.FILESYSTEM.EDIT_FILE]: { requireReadBeforeWrite: true },
    [WORKSPACE_TOOLS.FILESYSTEM.DELETE]: { requireApproval: true },
    [WORKSPACE_TOOLS.SANDBOX.EXECUTE_COMMAND]: {
      maxOutputTokens: 5000,
      requireDescription: true,
    },
  },
})
```

```typescript
// src/mastra/agents/coding-agent.ts
import { Agent } from '@mastra/core/agent'
import { workspace } from '../workspace'

export const codingAgent = new Agent({
  id: 'coding-agent',
  name: 'Coding agent',
  instructions: `You work inside the project workspace.
Read a file before editing it. Run the test command after each change and report the result.`,
  model: 'openai/gpt-6.1-sol',
  workspace,
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { codingAgent } from './agents/coding-agent'

export const mastra = new Mastra({ agents: { codingAgent } })
```

`.env`: `WORKSPACE_PATH=/home/me/projects/demo`, `OPENAI_API_KEY=...`

`requireReadBeforeWrite` persists across turns when the Mastra instance has storage and the agent runs with a memory thread. Without them, reads are tracked per run.

---

## 2. S3 bucket mounted into an E2B sandbox

Commands and file tools see the same files at `/data` and `/reports`, and the files outlive the sandbox.

```typescript
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { Workspace } from '@mastra/core/workspace'
import { E2BSandbox } from '@mastra/e2b'
import { GCSFilesystem } from '@mastra/gcs'
import { S3Filesystem } from '@mastra/s3'

const workspace = new Workspace({
  mounts: {
    '/data': new S3Filesystem({
      bucket: 'agent-data',
      region: 'us-east-1',
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    }),
    '/reports': new GCSFilesystem({
      bucket: 'agent-reports',
    }),
  },
  sandbox: new E2BSandbox({ id: 'analysis-sandbox' }),
})

export const analyst = new Agent({
  id: 'analyst',
  name: 'Analyst',
  instructions: 'Read input files from /data, run Python to analyze them, and write summaries to /reports.',
  model: 'anthropic/claude-sonnet-5-5',
  workspace,
})

export const mastra = new Mastra({ agents: { analyst } })
```

Env: `E2B_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and Google Application Default Credentials (`GOOGLE_APPLICATION_CREDENTIALS`) for GCS.

E2B mounts through FUSE (`s3fs`, `gcsfuse`, `blobfuse2`) and installs the tools at startup when missing. Pre-build a template to cut startup time. If a mount fails, file tools still work through the provider SDK but commands cannot see the path.

---

## 3. One Daytona sandbox per user, with network limits and cleanup

```typescript
// src/mastra/workspace.ts
import { Workspace } from '@mastra/core/workspace'
import { DaytonaSandbox } from '@mastra/daytona'

const userSandboxes = new Map<string, DaytonaSandbox>()

export const workspace = new Workspace({
  sandbox: async ({ requestContext }) => {
    const userId = requestContext.get('user-id') as string
    const sandbox = new DaytonaSandbox({
      id: `user-${userId}`,
      networkBlockAll: true,
      domainAllowList: 'registry.npmjs.org,api.github.com',
    })
    await sandbox.start()
    userSandboxes.set(userId, sandbox)
    return sandbox
  },
  sandboxCacheKey: ({ requestContext }) => requestContext.get('user-id') as string,
})

// Call when the user's session ends. The workspace does not own these sandboxes.
export async function endUserSession(userId: string) {
  const sandbox = userSandboxes.get(userId)
  if (sandbox) {
    await sandbox.destroy()
    userSandboxes.delete(userId)
  }
  workspace.clearSandboxCache(userId)
}
```

Call the agent with the user ID in request context:

```typescript
import { RequestContext } from '@mastra/core/request-context'

const requestContext = new RequestContext()
requestContext.set('user-id', 'alice')
await mastra.getAgentById('coding-agent').generate('Run npm test', { requestContext })
```

Env: `DAYTONA_API_KEY`. On a Mastra server, set `user-id` from authenticated middleware, never from the request body (see `mastra-server`).

Inside a custom tool, reach the live sandbox:

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const startServerTool = createTool({
  id: 'start-server',
  description: 'Starts a server in the sandbox',
  inputSchema: z.object({ command: z.string() }),
  execute: async ({ command }, ctx) => {
    if (!ctx.workspace || !ctx.requestContext) {
      throw new Error('This tool requires a workspace execution context')
    }
    const sandbox = await ctx.workspace.resolveSandbox({ requestContext: ctx.requestContext })
    if (!sandbox?.processes) {
      throw new Error('The configured sandbox does not support background processes')
    }
    const server = await sandbox.processes.spawn(command)
    return { pid: server.pid }
  },
})
```

---

## 4. Searchable knowledge base with auto-indexing

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { LocalFilesystem, Workspace, WORKSPACE_TOOLS } from '@mastra/core/workspace'

const workspace = new Workspace({
  id: 'support-kb',
  filesystem: new LocalFilesystem({
    basePath: process.env.KB_PATH!,
    readOnly: true, // removes write tools and the index tool
  }),
  bm25: true,
  autoIndexPaths: ['docs/**/*.md', 'support/**/*.txt'],
  tools: {
    [WORKSPACE_TOOLS.SEARCH.INDEX]: { enabled: false },
  },
})

const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  instructions: 'Search the knowledge base before answering. Cite the document id of each source.',
  model: 'openai/gpt-6-luna',
  workspace,
})

export const mastra = new Mastra({ agents: { supportAgent }, workspace })

// autoIndexPaths runs only here. Registration alone does not index.
await workspace.init()
```

Query from application code:

```typescript
const results = await workspace.search('password reset', { topK: 5 })
for (const r of results) console.log(r.id, r.score)
```

For semantic search add `vectorStore` and `embedder` (see `references/api.md`, Search options) or pick a store with `mastra-vector-stores`. Auto-indexing scans once. Re-index changed files with `workspace.index(path, content)`.
