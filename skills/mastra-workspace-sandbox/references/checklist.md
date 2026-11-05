# Workspace checklist

Run this before calling a workspace done.

## Isolation and security

- [ ] Untrusted code never runs in a `LocalSandbox` without `isolation` (`seatbelt` or `bwrap`), or runs in a container or remote sandbox
- [ ] Outbound network is blocked or allowlisted at sandbox creation (`allowNetwork: false`, Daytona `networkBlockAll` + `domainAllowList`, Railway `networkIsolation`)
- [ ] Commands receive only the env vars they need (no `env: process.env`), scoped per command where possible
- [ ] `LocalFilesystem` keeps `contained: true`; extra roots go in `allowedPaths`
- [ ] LSP `root` points at a trusted project; the LSP tool is off when users can submit host paths
- [ ] Exposed port URLs (`networking.getPortUrl`) are not left publicly reachable longer than needed

## Tool policy

- [ ] Destructive tools (`delete`, `execute_command` on shared data) require approval or are disabled
- [ ] `requireReadBeforeWrite` on `write_file` and `edit_file` for code-editing agents
- [ ] If files may change only through file tools, `execute_command` is disabled (mounted paths are writable by commands)
- [ ] Noisy tools capped with `maxOutputTokens`
- [ ] `apply_patch` enabled explicitly only if wanted
- [ ] Renamed tools have unique names

## Scope and lifecycle

- [ ] Sharing model is deliberate: Mastra-level, agent-level, or resolver with `sandboxCacheKey`
- [ ] Per-user or per-thread storage uses a resolver with a `prefix`; mounts happen inside the sandbox resolver
- [ ] Resolver-returned sandboxes are tracked, destroyed at session end, and removed with `clearSandboxCache(key)`
- [ ] Agent `workspace` functions do not start infrastructure
- [ ] Custom servers call `mastra.shutdown()` on exit; standalone scripts call `workspace.destroy()`
- [ ] `workingDirectory` and `basePath` are absolute paths from env vars

## Search

- [ ] `await workspace.init()` runs once at startup when `autoIndexPaths` is set
- [ ] `autoIndexPaths` excludes `node_modules`, build output, and binaries
- [ ] Writes that must be searchable also call `workspace.index()`
- [ ] Stable workspace `id` or `searchIndexName` for persistent vector indexes
- [ ] `minScore` tuned for the active mode and store

## Verification

- [ ] Provider env vars documented in `.env.example`
- [ ] Agent lists files and runs one harmless command in Studio (`npx mastra dev`)
- [ ] A forbidden action (network call, write outside root) fails as expected
