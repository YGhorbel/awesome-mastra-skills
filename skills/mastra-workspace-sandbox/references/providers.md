# Sandbox and filesystem providers

Distilled from `https://mastra.ai/integrations/sandboxes/*`, `https://mastra.ai/integrations/file-storage/*`, and `https://mastra.ai/reference/workspace/platform-*`. Each class implements `WorkspaceSandbox` or `WorkspaceFilesystem`. Options change often: open the provider page before writing a constructor.

## Contents

- Choosing a sandbox
- Sandbox providers
- Filesystem providers
- Mount support matrix
- Mastra Factory sandboxes

---

## Choosing a sandbox

| Need | Pick |
|---|---|
| Trusted local dev, fastest loop | `LocalSandbox` with `isolation` |
| Local container, CI, air-gapped | `DockerSandbox` (or `AppleContainerSandbox` on Apple silicon, macOS 26+) |
| Hosted, mount S3/GCS/Azure into the sandbox | `E2BSandbox`, `DaytonaSandbox`, `BlaxelSandbox` |
| Desktop control (computer use) | `E2BDesktopSandbox`, `DaytonaSandbox({ computerUse: true })` |
| Strict outbound network policy | `DaytonaSandbox` (`networkBlockAll`, `domainAllowList`), `RailwaySandbox` (`networkIsolation`), `LocalSandbox` isolation |
| Persistent VM that hibernates and reconnects by name | `SpritesSandbox` |
| Already deployed on Mastra Platform | `PlatformSandbox` |
| Agent already runs in AWS AgentCore Runtime | `AgentCoreRuntimeSandbox` (one-shot commands only) |
| Stateless function execution | `VercelServerlessSandbox` (no processes, only `/tmp` writable) |

---

## Sandbox providers

| Provider | Package | Class | Minimal constructor | Credentials (env) | Processes | Notes |
|---|---|---|---|---|---|---|
| Local | `@mastra/core/workspace` | `LocalSandbox` | `{ workingDirectory, isolation }` | none | yes | Not isolated by default. |
| AgentCore | `@mastra/agentcore` | `AgentCoreRuntimeSandbox` | `{ region, agentRuntimeArn, runtimeSessionId }` | AWS SDK chain, `AGENTCORE_RUNTIME_ARN` in examples | no | No stdin, no mounts. |
| Apple Container | `@mastra/apple-container` | `AppleContainerSandbox` | `{ image: 'node:22-slim', volumes, workingDirectory }` | none | see page | Run `container system start` first. |
| Blaxel | `@mastra/blaxel` | `BlaxelSandbox` | `{ image, memory, region: 'auto', timeout: '10m' }` | Blaxel account; `BL_REGION` optional | yes | Mounts S3 and GCS. |
| Cloudflare | `@mastra/cloudflare-sandbox` | `CloudflareSandbox` | `{ baseUrl, apiToken, workingDirectory, commandTimeout }` | `CLOUDFLARE_SANDBOX_BRIDGE_URL`, `CLOUDFLARE_SANDBOX_API_KEY` | no | Needs a deployed Sandbox Bridge Worker. `/workspace` is lost on sleep; mount S3/R2. |
| Daytona | `@mastra/daytona` | `DaytonaSandbox` | `{ language: 'typescript', timeout }` | `DAYTONA_API_KEY` | yes | Snapshots, volumes, `networkBlockAll`, `domainAllowList`, `networkAllowList`, `secrets`, `computerUse`. |
| Docker | `@mastra/docker` | `DockerSandbox` | `{ image: 'node:22-slim' }` | Docker Engine running | yes | Hardening: `memory`, `pidsLimit`, `capDrop`, `readonlyRootfs`, `tmpfs`. `createDockerRepoTemplate`. |
| E2B | `@mastra/e2b` | `E2BSandbox` | `{ id, timeout }` | `E2B_API_KEY` | yes | Default timeout 5 min, pauses on timeout. `sandboxId` + `reattach: 'required'`. Templates. Native `filesystem`. |
| E2B Desktop | `@mastra/e2b-desktop` | `E2BDesktopSandbox` | `{ resolution: [1280, 720] }` | `E2B_API_KEY` | yes | Computer tools, `computer.streamUrl()`. |
| Mastra Platform | `@mastra/platform-workspace` | `PlatformSandbox` | `{}` on Platform | `MASTRA_PLATFORM_ACCESS_TOKEN`, `MASTRA_PROJECT_ID`, `MASTRA_ENVIRONMENT_ID`, `SANDBOX_PROVIDER` (default `railway`) | see page | Python 3, Node 22 preinstalled. Stable `id` enables checkpoint recovery. |
| Modal | `@mastra/modal` | `ModalSandbox` | `{ id, baseImage: 'ubuntu:22.04', timeoutMs }` | `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` | yes | `volumes` for persistent files. |
| Railway | `@mastra/railway` | `RailwaySandbox` | `{ idleTimeoutMinutes: 30 }` | `RAILWAY_API_TOKEN`, `RAILWAY_ENVIRONMENT_ID` | yes | `networkIsolation: 'ISOLATED' \| 'PRIVATE'`, checkpoints, `fork()`. |
| Fly.io Sprites | `@mastra/sprites` | `SpritesSandbox` | `{ id: 'mastra-project' }` | `SPRITES_TOKEN` | yes | Requires Node.js 24+. `id` is the Sprite name; files persist. |
| Vercel Sandbox | `@mastra/vercel` | `VercelSandbox` | `{ runtime: 'node24', timeout: 600_000 }` | Vercel OIDC (`vercel env pull`), or all of `VERCEL_TOKEN`, `VERCEL_TEAM_ID`, `VERCEL_PROJECT_ID` | yes | Firecracker microVM, ports, `sudo`. |
| Vercel Serverless | `@mastra/vercel` | `VercelServerlessSandbox` | `{ token: process.env.VERCEL_TOKEN }` | `VERCEL_TOKEN` | no | Stateless. Only `/tmp` writable. |

Every sandbox accepts `workingDirectory` (deprecated aliases: `workingDir` on Docker and Apple Container, `workdir` on Modal). Most accept `env`, `instructions`, and lifecycle hooks.

Usage shape is the same for all:

```typescript
import { Workspace } from '@mastra/core/workspace'
import { E2BSandbox } from '@mastra/e2b'

const workspace = new Workspace({
  sandbox: new E2BSandbox({ id: 'dev-sandbox', timeout: 60_000 }),
})
```

Add a provider Mastra lacks by implementing the `WorkspaceSandbox` interface (`https://mastra.ai/reference/workspace/sandbox`).

---

## Filesystem providers

| Provider | Package | Class | Minimal constructor | Credentials |
|---|---|---|---|---|
| Local | `@mastra/core/workspace` | `LocalFilesystem` | `{ basePath }` | none |
| AgentFS (Turso/SQLite) | `@mastra/agentfs` | `AgentFSFilesystem` | `{ agentId }` or `{ path }` or `{ agent }` | none (local `.agentfs` dir) |
| Amazon S3 and compatibles (R2, MinIO, Tigris, Spaces) | `@mastra/s3` | `S3Filesystem` | `{ bucket, region, prefix? }` | AWS default chain or `accessKeyId`/`secretAccessKey`; `endpoint` for compatibles |
| Archil | `@mastra/archil` | `ArchilFilesystem` | `{ diskId, apiKey, region }` | `ARCHIL_API_KEY`, `ARCHIL_REGION`, optional `ARCHIL_S3_BASE_URL` |
| Azure Blob | `@mastra/azure` (import `@mastra/azure/blob`) | `AzureBlobFilesystem` | `{ container, connectionString }` | `AZURE_STORAGE_CONNECTION_STRING`, or account name + key, or SAS, or `DefaultAzureCredential` |
| Google Cloud Storage | `@mastra/gcs` | `GCSFilesystem` | `{ bucket, projectId?, credentials? }` | Application Default Credentials or service account JSON |
| Google Drive | `@mastra/google-drive` | `GoogleDriveFilesystem` | `{ folderId, accessToken }` | `accessToken`, `getAccessToken`, or `serviceAccount` (share the folder; service accounts cannot write to My Drive) |
| Mastra Platform | `@mastra/platform-workspace` | `PlatformFilesystem` | `{}` on Platform | `MASTRA_PLATFORM_ACCESS_TOKEN`, `MASTRA_PROJECT_ID`, `MASTRA_PLATFORM_BUCKET_NAME` |
| Mesa (versioned repos) | `@mastra/mesa` | `MesaFilesystem` | `{ privateKey, authors, layout: { '/docs': repo('docs', {...}) } }` | `MESA_PRIVATE_KEY`. No sandbox mount yet. |
| Neon Object Storage | `@mastra/s3` + `@neon/config` | `S3Filesystem` | `{ bucket, region, endpoint, accessKeyId, secretAccessKey }` | `AWS_REGION`, `AWS_ENDPOINT_URL_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Vercel Files (FilesSDK) | `@mastra/files-sdk` + `files-sdk` | `FilesSDKFilesystem` | `{ files }` from `new Files({ adapter: s3({...}) })` | per adapter |

Every provider supports the file tools. Per-user storage: return a provider with a user `prefix` from a `filesystem` resolver.

---

## Mount support matrix

Built-in sandbox mounting (commands see the files):

| Sandbox | Mountable filesystems |
|---|---|
| `LocalSandbox` | `LocalFilesystem` (symlink under `workingDirectory`) |
| E2B | S3, GCS, Azure Blob (FUSE) |
| Daytona | S3, GCS, Azure Blob (FUSE) |
| Blaxel | S3, GCS (FUSE) |
| Cloudflare | S3-compatible only, through the bridge (`s3fs`) |

Other combinations need an `onMount` hook or provider-specific setup. When a mount fails, file tools keep working through the provider SDK and Mastra tells the agent the path is file-tools only.

---

## Mastra Factory sandboxes

`MastraFactory` (coding-agent sessions) takes a `FactorySandbox`: `PlatformFactorySandbox` (`@mastra/platform-workspace`), `E2BFactorySandbox` (`@mastra/e2b`), `DockerFactorySandbox` (`@mastra/docker`), `LocalFactorySandbox` (`@mastra/factory`). Each accepts its sandbox class options minus `id`, `sandboxId`, `template`, plus `template` and `defaults`. See `https://mastra.ai/reference/workspace/factory-sandbox` and `mastra-harness`.
