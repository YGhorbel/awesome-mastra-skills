---
name: mastra-workspace-sandbox
description: "Give Mastra agents a Workspace: a filesystem for reading, writing, and searching files, a sandbox for shell commands and background processes, computer-use desktop control, LSP code inspection, BM25 or vector search, and filesystem-backed skills. Use this skill whenever the user wants an agent to run code, execute shell commands, clone and test a repo, edit files, keep files between runs, mount S3 or GCS into a sandbox, isolate each user or thread in its own sandbox, or control a remote desktop. Triggers on Workspace, @mastra/core/workspace, LocalSandbox, LocalFilesystem, WORKSPACE_TOOLS, execute_command, mounts, CompositeFilesystem, sandboxCacheKey, autoIndexPaths, E2BSandbox, DaytonaSandbox, DockerSandbox, VercelSandbox, ModalSandbox, RailwaySandbox, PlatformSandbox, S3Filesystem, GCSFilesystem, seatbelt, bwrap, computer use, lsp_inspect. Also triggers for coding agents, code interpreters, and file-processing agents even if the user never says workspace."
license: Apache-2.0
metadata:
  category: sandbox-and-browser
  catalog_summary: "Workspace class, filesystems, sandboxes, mounts, per-user isolation, tool policies, search, LSP, computer use, providers"
  display_order: 1
  docs: https://mastra.ai/docs/sandbox/overview
---

# Mastra Workspace and Sandbox

Configure a `Workspace` so an agent can read and write files, run commands in an isolated environment, search indexed content, and inspect code, with the right isolation and lifecycle.

---

## When to use

- An agent must run shell commands, tests, builds, or scripts (`execute_command`)
- An agent must read, write, edit, or grep files in a directory or bucket
- Files must outlive an ephemeral sandbox (mount S3, GCS, or Azure Blob into it)
- Each user, tenant, or memory thread needs its own sandbox or storage prefix
- Picking a sandbox provider (local, Docker, E2B, Daytona, Vercel, Modal, Railway, Mastra Platform, others)
- Restricting workspace tools: approval, read-before-write, renaming, disabling, hooks
- Keyword or semantic search over workspace files (`bm25`, `vectorStore`, `autoIndexPaths`)
- Type-aware code inspection (`lsp`) or desktop control (computer use)

## When NOT to use

- Web browsing with browser tools (use `mastra-browser`)
- Defining skills in agent code with `createSkill()`, or skill format details (use `mastra-agent-skills`)
- Writing custom tools with `createTool` (use `mastra-tools`)
- Generic tool approval flows and resuming suspended runs (use `mastra-agent-approval-hitl`)
- RAG pipelines with chunking and vector query tools (use `mastra-rag`)
- Choosing a vector database (use `mastra-vector-stores`)
- Durable coding-agent runtimes and background tasks (use `mastra-harness`)
- Delegating to an external coding agent such as Claude Code over ACP (use `mastra-a2a-acp`)

---

## Required inputs

- What the agent does with the workspace: files only, commands, or both
- Trust level of the code it runs (trusted dev scripts vs untrusted user code)
- Scope: one shared environment, or one per user, tenant, or thread
- Where files must persist (local disk, S3, GCS, Azure, Google Drive, Platform bucket)
- Network policy: which outbound hosts commands may reach
- Which credentials commands need, and their minimum scope

If the code is untrusted, never default to an unisolated `LocalSandbox`.

---

## The framework: filesystem plus sandbox, attached to an agent

A `Workspace` combines up to four capabilities. Each one adds agent tools automatically.

| Config | Adds tools | Notes |
|---|---|---|
| `filesystem` or `mounts` | `mastra_workspace_read_file`, `write_file`, `edit_file`, `list_files`, `delete`, `file_stat`, `mkdir`, `grep` (`ast_edit`, `apply_patch` opt-in) | Configure one, never both (`INVALID_CONFIG`) |
| `sandbox` | `mastra_workspace_execute_command`, `get_process_output`, `kill_process` | Process tools need a process manager |
| `bm25` and/or `vectorStore` + `embedder` | `mastra_workspace_search`, `mastra_workspace_index` | Index is separate from files |
| `lsp` | `mastra_workspace_lsp_inspect` | Needs a static sandbox with a process manager |
| `skills` | `skill`, `skill_read`, `skill_search` | See `mastra-agent-skills` |

```typescript
import { Agent } from '@mastra/core/agent'
import { LocalFilesystem, LocalSandbox, Workspace } from '@mastra/core/workspace'

export const codingAgent = new Agent({
  id: 'coding-agent',
  name: 'Coding agent',
  instructions: 'Use the sandbox to complete coding tasks.',
  model: 'openai/gpt-6.1-sol',
  workspace: new Workspace({
    filesystem: new LocalFilesystem({ basePath: './workspace' }),
    sandbox: new LocalSandbox({ workingDirectory: './workspace' }),
  }),
})
```

Attach a workspace to one agent (`workspace` option), or to the `Mastra` instance (`new Mastra({ workspace })`). Agents without their own workspace inherit the Mastra-level one.

### Who shares a sandbox

| Configuration | Shared by |
|---|---|
| Mastra-level | Every agent that inherits it |
| Agent-level static sandbox | Every request and thread of that agent |
| Resolver + `sandboxCacheKey` on user ID | One sandbox per user |
| Resolver + `sandboxCacheKey` on thread ID | One sandbox per memory thread |

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Workspace` types, plus the provider package docs (for example `node_modules/@mastra/e2b/dist/docs/`). Otherwise fetch `https://mastra.ai/docs/sandbox/overview.md` and `https://mastra.ai/reference/workspace/workspace-class.md`. Trust these over memory.
2. **Pick the capability set.** Files only: `filesystem`. Commands: add `sandbox`. Programs need the files by path: use `mounts` with a mount-capable sandbox.
3. **Pick providers.** `LocalSandbox` for trusted local work, a container or remote sandbox for untrusted code (see [`references/providers.md`](references/providers.md)). Install the provider package and set its env vars.
4. **Set isolation and network.** For `LocalSandbox`, set `isolation: 'seatbelt'` (macOS) or `'bwrap'` (Linux), check with `LocalSandbox.detectIsolation()`. For remote sandboxes, apply the provider's network restriction at creation.
5. **Scope it.** Static for a shared environment. For per-user or per-thread, use a `sandbox` resolver plus `sandboxCacheKey`, and mount storage inside the resolver.
6. **Set tool policies.** `requireApproval` globally or per tool, `requireReadBeforeWrite` on write tools, `enabled: false` on tools you do not want, `maxOutputTokens` on noisy tools.
7. **Pass only needed secrets.** `LocalSandbox` exposes only `PATH` by default. Use per-command `env` or `setEnv()` for scoped tokens.
8. **Plan the lifecycle.** Call `workspace.init()` at startup only when you want early errors or `autoIndexPaths`. Destroy resolver-returned sandboxes yourself and call `workspace.clearSandboxCache(key)`.
9. **Register and test.** Register the agent on `Mastra`, run `npx mastra dev`, and ask the agent to list files and run a harmless command in Studio.

---

## Deep dive: per-thread sandbox with persistent storage

Static `mounts` cannot be combined with a sandbox resolver. Mount inside the resolver instead:

```typescript
import { MASTRA_THREAD_ID_KEY, type RequestContext } from '@mastra/core/request-context'
import { Workspace } from '@mastra/core/workspace'
import { DaytonaSandbox } from '@mastra/daytona'
import { S3Filesystem } from '@mastra/s3'

const getThreadId = (requestContext: RequestContext) =>
  requestContext.get(MASTRA_THREAD_ID_KEY) as string

const createThreadFilesystem = (threadId: string) =>
  new S3Filesystem({
    bucket: process.env.S3_BUCKET!,
    region: process.env.S3_REGION!,
    prefix: `threads/${threadId}`,
  })

const workspace = new Workspace({
  filesystem: ({ requestContext }) => createThreadFilesystem(getThreadId(requestContext)),
  sandbox: async ({ requestContext }) => {
    const threadId = getThreadId(requestContext)
    const sandbox = new DaytonaSandbox({ id: `thread-${threadId}`, language: 'typescript' })
    await sandbox.start()
    await sandbox.mount(createThreadFilesystem(threadId), '/workspace')
    return sandbox
  },
  sandboxCacheKey: ({ requestContext }) => getThreadId(requestContext),
})
```

Your application owns resolver-returned sandboxes. When the thread ends, call `destroy()` on the sandbox and then `workspace.clearSandboxCache(threadId)`. `workspace.destroy()` and `mastra.shutdown()` do not destroy them.

If the agent's `workspace` option is a function, keep it cheap. Mastra calls it for metadata routes (`GET /api/agents`) and startup too. Return a workspace with resolvers instead of starting infrastructure inside it.

---

## Failure patterns

- **Unisolated `LocalSandbox` for untrusted code.** It runs on the host with app permissions. Enable `isolation`, or use Docker, E2B, Daytona, or another remote sandbox.
- **Relative paths resolving to odd places.** Under `mastra dev`, `./workspace` resolves inside `src/mastra/public/`. Under `mastra start`, inside `.mastra/output/`. Use an absolute path from an env var.
- **Configuring both `filesystem` and `mounts`.** Throws `WorkspaceError` `INVALID_CONFIG`. Pick one.
- **Static `mounts` with a sandbox resolver.** Not supported. Mount inside the resolver with `sandbox.mount(fs, path)`.
- **Write approval on `write_file` only.** Commands can still write the same mounted path. Disable `execute_command` if files must change only through file tools.
- **Expecting `autoIndexPaths` to index on registration.** It runs during `workspace.init()`. Await `workspace.init()` once at startup.
- **Expecting writes to update the search index.** File and index mutations are independent. Call `workspace.index(path, content)` after writing.
- **Leaking per-user sandboxes.** Resolver sandboxes keep running. Destroy them and call `clearSandboxCache`.
- **Starting a sandbox inside an agent `workspace` function.** It runs on every metadata request. Use resolvers.
- **Missing process tools.** A static sandbox without a process manager exposes no `get_process_output` or `kill_process`. With a resolver, an unsupported call throws `SandboxFeatureNotSupportedError`.
- **No computer tools with a resolver.** Computer tools register only for a static `DaytonaSandbox` (`computerUse: true`) or `E2BDesktopSandbox`.
- **Passing `process.env` to the sandbox.** Every command sees every secret. Pass only the variables a command needs.
- **Read-only filesystem resolver still lists write tools.** Expected. The provider rejects writes at runtime.

---

## Output format

A finished workspace delivery contains:

- The workspace module (for example `src/mastra/workspace.ts`) and its attachment to the agent or `Mastra` instance
- Provider packages in `package.json` and their env vars in `.env.example`
- The isolation and network choice, stated in a comment or README line
- Tool policy (`tools` config) for writes, deletes, and commands
- Lifecycle code: `workspace.init()` if needed, and cleanup for resolver-backed sandboxes
- Evidence: a Studio or script run where the agent lists files and runs one command

---

## Reference files

- [`references/api.md`](references/api.md) - `Workspace` options, tool config, methods, `LocalSandbox`, `LocalFilesystem`, sandbox interface, process manager, search, LSP.
- [`references/examples.md`](references/examples.md) - Isolated local coding agent, S3 mounted into E2B, per-user Daytona sandbox with cleanup, searchable knowledge base.
- [`references/providers.md`](references/providers.md) - Every sandbox and filesystem provider: package, class, constructor, env vars, mount and process support.
- [`references/checklist.md`](references/checklist.md) - Security and production checklist.

**Live docs**

- https://mastra.ai/docs/sandbox/overview
- https://mastra.ai/docs/sandbox/filesystem
- https://mastra.ai/docs/sandbox/search
- https://mastra.ai/docs/sandbox/lsp
- https://mastra.ai/docs/sandbox/computer
- https://mastra.ai/docs/sandbox/skills
- https://mastra.ai/reference/workspace/workspace-class
- https://mastra.ai/reference/workspace/local-sandbox
- https://mastra.ai/reference/workspace/sandbox
- https://mastra.ai/reference/workspace/process-manager
