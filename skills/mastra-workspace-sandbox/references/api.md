# Workspace API reference

Distilled from `https://mastra.ai/reference/workspace/workspace-class.md`, `local-sandbox.md`, `local-filesystem.md`, `sandbox.md`, `filesystem.md`, `process-manager.md`, and the `docs/sandbox/*` pages. Verify against the installed version before relying on an option.

## Contents

- Workspace constructor
- Tool configuration (`tools`)
- Generated agent tools
- Workspace properties and methods
- LocalSandbox
- LocalFilesystem
- WorkspaceSandbox interface
- SandboxProcessManager and ProcessHandle
- WorkspaceFilesystem interface
- Search options
- LSP options
- Computer capability

---

## Workspace constructor: `new Workspace({...})`

Import: `import { Workspace, LocalFilesystem, LocalSandbox, WORKSPACE_TOOLS } from '@mastra/core/workspace'`. Added in `@mastra/core@1.1.0`.

| Option | Type | Default | Notes |
|---|---|---|---|
| `id` | `string` | auto | Stable `id` keeps the default vector index name stable. |
| `name` | `string` | `workspace-{first 8 of id}` | |
| `filesystem` | `WorkspaceFilesystem \| ({ requestContext }) => WorkspaceFilesystem` | | Static provider or resolver. |
| `mounts` | `Record<string, WorkspaceFilesystem>` | | Builds a `CompositeFilesystem`. Not with `filesystem`. No resolver form. Not with a sandbox resolver. |
| `sandbox` | `WorkspaceSandbox \| ({ requestContext }) => WorkspaceSandbox` | | Static provider or resolver. |
| `sandboxCacheKey` | `({ requestContext }) => string \| undefined` | | Memoizes resolver sandboxes per key. |
| `instructions.dynamicSandbox` | `'placeholder' \| 'resolve' \| ({ requestContext }) => string` | `'placeholder'` | How a resolver sandbox contributes to instructions. `'resolve'` provisions it. |
| `bm25` | `boolean \| { k1, b }` | | Keyword search. |
| `vectorStore` | `MastraVector` | | Semantic search. |
| `embedder` | `(text) => Promise<number[]>` or batch fn with `batch: true`, `maxBatchSize` | | Required with `vectorStore` unless the store embeds server-side (MongoDB `autoEmbed`). |
| `searchIndexName` | `string` | `{id}_search` sanitized | Letter or `_` first, letters, digits, `_`, max 63 chars. |
| `autoIndexPaths` | `string[]` | | Files, dirs, globs. Indexed on `init()` only. |
| `skills` | `string[] \| (ctx) => string[] \| Promise<string[]>` | | SKILL.md discovery paths. See `mastra-agent-skills`. |
| `skillSource` | `SkillSource` | | Replaces filesystem/local disk for skills. |
| `lsp` | `true \| { root, diagnosticTimeout, initTimeout, maxOpenClients, disableServers, binaryOverrides, searchPaths, packageRunner, servers }` | | LSP inspection. |
| `browser` | `BrowserViewer` | | CLI browser provider. See `mastra-browser`. |
| `onMount` | `OnMountHook` | | Return `false` to skip, `{ success: true }` if handled, `undefined` for default. |
| `tools` | `WorkspaceToolsConfig` | | See below. |
| `operationTimeout` | `number` | | Milliseconds. |

---

## Tool configuration (`tools`)

Global keys: `enabled`, `requireApproval`, `hooks`, `writeLockTimeoutMs`. `hooks` and `writeLockTimeoutMs` are global only. Per-tool keys use `WORKSPACE_TOOLS.*` constants.

| Per-tool option | Type | Default | Notes |
|---|---|---|---|
| `enabled` | `boolean \| ({ requestContext, workspace }) => boolean` | `true` | Evaluated when tools are listed. |
| `requireApproval` | `boolean \| ({ requestContext, workspace, args }) => boolean` | `false` | Evaluated at execution. |
| `name` | `string` | | Exposed name. Must be unique. Config key stays the constant. |
| `requireReadBeforeWrite` | `boolean \| fn` | `false` | Write tools reject files not read first. Tracked per thread in `threadState` storage. |
| `maxOutputTokens` | `number` | | Token truncation where supported. |

Tool-specific options:

| Tool constant | Extra options |
|---|---|
| `WORKSPACE_TOOLS.FILESYSTEM.READ_FILE` | `mediaTypes` (default `['image/png','image/jpeg','image/webp','application/pdf']`), `maxMediaBytes` (default 10 MiB) |
| `WORKSPACE_TOOLS.FILESYSTEM.APPLY_PATCH` | Opt-in: needs its own `{ enabled: true }`. Global `enabled` does not turn it on. |
| `WORKSPACE_TOOLS.SANDBOX.EXECUTE_COMMAND` | `backgroundProcesses: { onStdout, onStderr, onExit, abortSignal }`, `requireDescription` (default `false`) |
| `WORKSPACE_TOOLS.COMPUTER.*` | `screenshotAfterAction`, `screenshotDelayMs` |
| `WORKSPACE_TOOLS.SEARCH.INDEX` / `.SEARCH` | standard options |
| `WORKSPACE_TOOLS.LSP.LSP_INSPECT` | standard options |

`backgroundProcesses.abortSignal`: `undefined` uses the agent signal. `null` or `false` lets processes outlive the request.

Hooks:

```typescript
tools: {
  hooks: {
    beforeToolCall: ({ toolName, workspaceToolName, input }) => {
      // return { proceed: false, output } to skip the call
    },
    afterToolCall: ({ toolName, output, error }) => {},
  },
}
```

Order with agent hooks: agent `beforeToolCall`, workspace `beforeToolCall`, tool, workspace `afterToolCall`, agent `afterToolCall`.

---

## Generated agent tools

| Capability | Tools |
|---|---|
| Filesystem | `mastra_workspace_read_file`, `_write_file`, `_edit_file`, `_list_files`, `_delete`, `_file_stat`, `_mkdir`, `_grep`, `_ast_edit` (needs `@ast-grep/napi`), `_apply_patch` (opt-in) |
| Sandbox | `mastra_workspace_execute_command`, `_get_process_output`, `_kill_process` |
| Search | `mastra_workspace_search` (default `topK` 5), `mastra_workspace_index` |
| LSP | `mastra_workspace_lsp_inspect` (input `{ path, line, match }` with one `<<<` marker before the symbol) |
| Computer | `mastra_workspace_computer_screenshot`, `_click`, `_double_click`, `_right_click`, `_move_mouse`, `_drag`, `_type`, `_press_key`, `_scroll`, `_get_screen_info`, `_wait` |
| Skills | `skill`, `skill_read`, `skill_search` |

Read-only static filesystem: write tools and the index tool are removed. Resolver filesystem: write tools stay, writes fail at runtime. Static sandbox: tools match capabilities. Resolver sandbox: all sandbox tools register.

---

## Workspace properties and methods

Properties: `id`, `name`, `status` (`pending|initializing|ready|paused|error|destroying|destroyed`), `filesystem` and `sandbox` (static only, `undefined` with a resolver), `skills`, `lsp`, `canBM25`, `canVector`, `canHybrid`.

| Method | Notes |
|---|---|
| `init()` | Starts filesystem and sandbox, runs `autoIndexPaths`. Re-running clears and rebuilds the BM25 index. Not for request paths. |
| `stop()` | Stops LSP, browser, sandbox. Remote providers pause. Not a teardown. `mastra.shutdown()` calls it. |
| `destroy()` | Closes LSP, browsers, sandbox, filesystem. Does not delete `LocalFilesystem` files. Does not destroy resolver sandboxes. |
| `index(path, content, { metadata }?)` | Adds text under an ID. Does not read the file. |
| `search(query, { topK, mode, minScore, vectorWeight, filter }?)` | `topK` default 10. Returns `{ id, content, score, lineRange?, metadata?, scoreDetails? }[]`. |
| `getInfo({ includeFileCount, requestContext, resolveDynamicProviders })` | Never calls a sandbox resolver. |
| `getInstructions({ requestContext })` / `getInstructionsAsync(...)` | Async form for resolvers. |
| `getToolsConfig()` / `setToolsConfig(config?)` | `setToolsConfig` fully replaces. `undefined` resets. |
| `hasFilesystemConfig()` / `resolveFilesystem({ requestContext })` | |
| `hasSandboxConfig()` / `resolveSandbox({ requestContext })` | Use in tools via `ctx.workspace.resolveSandbox({ requestContext: ctx.requestContext })`. |
| `clearSandboxCache(cacheKey?)` | Drops keyed references only. |

`mastra.removeWorkspace(id, { destroy: true })` removes and tears down a registered workspace.

---

## LocalSandbox

`new LocalSandbox({...})`

| Option | Default | Notes |
|---|---|---|
| `id` | auto | |
| `workingDirectory` | `process.cwd()/.sandbox/` | Relative paths resolve from cwd. Prefer absolute. |
| `env` | only `PATH` | `process.env` exposes every secret. |
| `outputEncoding` | `'utf-8'` | WHATWG label. |
| `timeout` | `30000` | ms. |
| `isolation` | `'none'` | `'seatbelt'` (macOS) or `'bwrap'` (Linux). |
| `nativeSandbox.allowNetwork` | `false` | Only with isolation. Without isolation commands use the host network. |
| `nativeSandbox.readOnlyPaths` / `readWritePaths` | | |
| `nativeSandbox.allowSystemBinaries` | `true` | |
| `nativeSandbox.seatbeltProfilePath` / `bwrapArgs` | | `bwrapArgs` replaces the generated policy. |
| `instructions` | | String replaces, function extends. |
| `onStart`, `onStop`, `onDestroy` | | Lifecycle hooks receive `{ sandbox }` (`onStart` also `outcome`). |

Static: `LocalSandbox.detectIsolation()` returns `{ backend, available, message }`. Property `processes` is a `LocalProcessManager`.

---

## LocalFilesystem

`new LocalFilesystem({ basePath, id?, contained = true, allowedPaths = [], readOnly = false, instructions? })`

Methods: `init()`, `destroy()`, `setAllowedPaths(pathsOrUpdater)`, `readFile(path, { encoding })`, `writeFile(path, content, { recursive, overwrite, expectedMtime })` (stale mtime throws `StaleFileError`), `appendFile`. Containment covers file tools and indexing, not shell commands or LSP.

---

## WorkspaceSandbox interface

| Member | Notes |
|---|---|
| `start()` | Returns `{ outcome: 'created' \| 'connected' }` or `void`. Known `id` means get-or-create. Concurrent calls coalesce. |
| `onStart` option / `setOnStart(prev => fn)` | Runs after `running`, before mounts. A throw fails `start()`. Keep it idempotent. |
| `workingDirectory` option | Default cwd for commands. Per-command `cwd` wins. |
| `stop()`, `destroy()`, `snapshot()` | Backend-defined. |
| `executeCommand(command, args?, { timeout, cwd, env, onStdout, onStderr })` | Returns `{ success, exitCode, stdout, stderr, ... }`. |
| `setEnv(env => next)` / `getEnv()` | Runtime env merged into every command. Optional: use `?.`. |
| `getInfo()`, `getInstructions({ requestContext })` | |
| `processes` | Optional `SandboxProcessManager`. |
| `filesystem` | Optional native file API. Not contained. `E2BSandbox` always has it. |
| `computer` | Optional `SandboxComputer`. Check with `supportsComputer(sandbox)`. |
| `networking?.getPortUrl(port)` | Public URL for a port, where supported. |
| `mount(filesystem, path)` | On mount-capable providers. |

---

## SandboxProcessManager and ProcessHandle

Added in `@mastra/core@1.7.0`. Built into Local, E2B, Daytona, Blaxel, Modal sandboxes.

| Method | Notes |
|---|---|
| `spawn(command, { timeout, env, cwd, onStdout, onStderr, abortSignal, stdinMode })` | `stdinMode` `'pipe'` (default) or `'ignore'`. Returns `ProcessHandle`. |
| `list()` | `{ pid, command, running, exitCode }[]` |
| `get(pid, { release = true })` | |
| `kill(pid)` | `Promise<boolean>` |

`ProcessHandle`: `pid`, `stdout`, `stderr`, `exitCode`, `command`, `reader`, `writer`, `wait({ onStdout, onStderr })` (resolves `{ success, exitCode, stdout, stderr, executionTimeMs, timedOut, killed }`), `kill()`, `sendStdin(data)`, `closeStdin()`.

---

## WorkspaceFilesystem interface

Required: `readFile`, `writeFile`, `deleteFile`, `appendFile`, `copyFile`, `moveFile`, `readdir`, `mkdir`, `rmdir`, `exists`, `stat`. Optional: `init`, `destroy`, `getInfo`, `getInstructions`, `walk`, `grep`. Implement it to add a custom provider.

`CompositeFilesystem({ mounts })` routes by path prefix and strips the prefix. Mount paths cannot nest.

---

## Search options

| Option | Notes |
|---|---|
| `topK` | API default 10, agent tool default 5. |
| `mode` | `'bm25' \| 'vector' \| 'hybrid'`. Default: hybrid when both are configured. |
| `minScore` | Scale depends on mode and store. Tune per index. |
| `vectorWeight` | Hybrid only. `0` ignores vector, `1` ignores BM25. |
| `filter` | Vector metadata filter. Does not filter BM25-only hits. |

Deleting a file does not remove its indexed document. There is no public single-document delete.

---

## LSP options

Requirements: static sandbox with bidirectional process streams, `vscode-jsonrpc` and `vscode-languageserver-protocol` installed, a language server binary (for example `typescript-language-server`), absolute `root`. Built-in servers: TypeScript/JavaScript, Python, Go, Rust.

| Option | Notes |
|---|---|
| `root` | Fallback project root. |
| `diagnosticTimeout`, `initTimeout` | ms. Agent tool waits up to 5 s. |
| `maxOpenClients` | Positive integer. Unlimited when omitted. |
| `disableServers` | Server IDs. |
| `binaryOverrides` | `{ typescript: '/path --stdio' }` |
| `searchPaths` | Extra package roots. |
| `packageRunner` | Last-resort fallback such as `pnpm dlx`. Off by default. |
| `servers` | Custom `{ id, name, languageIds, extensions, markers, command, initializationOptions? }`. |

Direct use: `workspace.lsp?.prepareQuery(absPath)` returns `{ client, uri, release }`. Positions are 0-indexed. Call `client.notifyClose(path)` and `release()` in `finally`.

---

## Computer capability

`SandboxComputer`: `screenshot()`, `leftClick(x, y)`, `rightClick`, `doubleClick`, `moveMouse`, `drag(from, to)`, `scroll(direction, amount)`, `type(text)`, `press(key | keys[])`, `getScreenSize()`, `getCursorPosition()`, `streamUrl()`.

Supported by `DaytonaSandbox` (with `computerUse: true`) and `E2BDesktopSandbox`. Tools register only for a static sandbox.
