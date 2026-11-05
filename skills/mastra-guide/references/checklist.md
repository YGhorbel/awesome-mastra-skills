# Native capability first checklist

Before writing custom infrastructure in a Mastra project, check each item. Mastra likely ships it.

| If you are about to build | Check first | Skill |
|---|---|---|
| A retry loop around model calls | Model fallback arrays, `modelSettings.maxRetries`, workflow step retries | `mastra-models`, `mastra-workflows` |
| An approval queue | `requireToolApproval`, `suspend()`, workflow suspend/resume | `mastra-agent-approval-hitl`, `mastra-workflow-suspend-resume` |
| A cron runner | Schedules and scheduled workflows | `mastra-schedules` |
| A job queue for long work | Background tasks, durable agents, workflow runners | `mastra-harness`, `mastra-deployment` |
| A task list tool | `TaskSignalProvider` and task tools | `mastra-signals`, `mastra-tools` |
| A web fetch or search tool | `webFetchTool`, `webSearchTool` | `mastra-tools` |
| An "ask the user" tool | `askUserTool` | `mastra-tools` |
| Conversation storage tables | `Memory` with a storage adapter | `mastra-memory`, `mastra-storage` |
| Summarizing old messages | Observational memory | `mastra-observational-memory` |
| PII scrubbing or moderation middleware | Built-in processors | `mastra-processors-guardrails` |
| A chunking and embedding pipeline | `MDocument`, `embedMany`, vector adapters | `mastra-rag` |
| Custom HTTP endpoints for agents | Built-in server routes, `registerApiRoute` | `mastra-server` |
| A fetch wrapper for the frontend | `MastraClient` | `mastra-client-sdk` |
| A Slack or Discord bot framework | Channels | `mastra-channels` |
| Prompt version storage | Editor versioning | `mastra-studio-editor` |
| Request logging and cost tracking | Tracing, metrics, exporters | `mastra-observability` |
| A test harness for prompts | Datasets, experiments, Vitest integration | `mastra-datasets-experiments` |
| A sandboxed code runner | Workspace sandbox providers, code mode | `mastra-workspace-sandbox`, `mastra-tools` |

## Before writing any Mastra code

- [ ] Installed version known (`npm ls @mastra/core`)
- [ ] API verified in embedded docs, types, or the live `.md` page
- [ ] Model ID verified (`mastra-models`)
- [ ] New primitive will be registered on `new Mastra({...})`
- [ ] Project is ESM with ES2022 settings
