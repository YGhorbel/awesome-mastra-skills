# Skill to docs mapping

Each skill lists the Mastra docs pages it was built from. Paths are relative to `https://mastra.ai/` (append `.md` to fetch Markdown). Globs mean every page in that folder. When a page changes upstream, refresh the skills that list it.

## getting-started

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-guide` | `llms.txt`, `docs`, `docs/guides/overview`, `docs/develop`, all section overviews |
| 2 | `mastra-project-setup` | `docs`, `docs/develop`, `reference/cli/create-mastra`, `reference/configuration`, `reference/core/*`, `reference/templates/*` |
| 3 | `mastra-build-playbook` | `docs/guides/agent-lifecycle`, `docs/guides/context-engineering`, `docs/guides/build-an-eval-loop`, `docs` (use cases and templates) |
| 4 | `mastra-troubleshooting` | `reference/client-js/error-handling`, common errors across docs, official `mastra-ai/skills` common-errors reference |
| 5 | `mastra-migrations` | `reference/migrations/*` |

## agents

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-agents` | `docs/agents/overview`, `reference/agents/*`, `reference/core/getAgentById`, `docs/server/request-context` (dynamic config) |
| 2 | `mastra-tools` | `docs/agents/tools`, `docs/agents/code-mode`, `reference/tools/create-tool`, `reference/tools/ask-user-tool`, `reference/tools/submit-plan-tool`, `reference/tools/task-tools`, `reference/tools/create-code-mode`, `reference/tools/quickjs-transport`, `reference/tools/isolated-vm-transport`, `reference/processors/tool-search-processor` |
| 3 | `mastra-structured-output` | `docs/agents/structured-output`, `reference/agents/generate` (structuredOutput) |
| 4 | `mastra-processors-guardrails` | `docs/agents/processors`, `docs/agents/guardrails`, `reference/processors/*` |
| 5 | `mastra-agent-approval-hitl` | `docs/agents/human-in-the-loop`, `reference/agents/listSuspendedRuns`, `reference/tools/ask-user-tool` |
| 6 | `mastra-multi-agent` | `docs/subagents`, `docs/guides/multi-agent-systems`, `reference/agents/network` |
| 7 | `mastra-agent-skills` | `docs/skills`, `docs/sandbox/skills`, `reference/agents/createSkill`, `reference/agents/getSkill`, `reference/agents/listSkills` |
| 8 | `mastra-file-based-agents` | `reference/file-based-agents/*` |
| 9 | `mastra-classifier` | `docs/classifier`, `reference/classifier/*` |
| 10 | `mastra-streaming` | `docs/guides/streaming`, `reference/streaming/*` |
| 11 | `mastra-voice` | `reference/voice/*`, `integrations/voice/*` |

## models

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-models` | `models`, `models/providers`, `models/gateways`, `models/embeddings`, `models/environment-variables`, `reference/core/addGateway`, official model-selection reference |

## workflows

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-workflows` | `docs/workflows/overview`, `docs/workflows/control-flow`, `docs/workflows/agents-and-tools`, `docs/workflows/workflow-state`, `docs/workflows/error-handling`, `docs/workflows/dynamic-workflows`, `reference/workflows/*`, `reference/streaming/workflows/*` |
| 2 | `mastra-workflow-suspend-resume` | `docs/workflows/suspend-and-resume`, `docs/workflows/human-in-the-loop`, `docs/workflows/snapshots`, `docs/workflows/time-travel` |

## memory-and-knowledge

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-memory` | `docs/memory/overview`, `docs/memory/message-history`, `docs/memory/multi-user-threads`, `docs/memory/working-memory`, `docs/memory/memory-processors`, `reference/memory/*` |
| 2 | `mastra-semantic-recall` | `docs/memory/semantic-recall`, `models/embeddings`, `reference/memory/*` (semanticRecall options) |
| 3 | `mastra-observational-memory` | `docs/memory/observational-memory`, `reference/memory/*` (observational options) |
| 4 | `mastra-rag` | `reference/rag/*`, `reference/tools/vector-query-tool`, `reference/tools/graph-rag-tool`, `reference/tools/document-chunker-tool`, `reference/tools/bedrock-kb-tool` |
| 5 | `mastra-knowledge` | `docs/knowledge/*`, `reference/knowledge/*`, `docs/studio/knowledge` |
| 6 | `mastra-storage` | `docs/storage`, `reference/storage/*`, `integrations/databases/*` |
| 7 | `mastra-vector-stores` | `integrations/vectors/*`, `reference/rag/vector-databases` |

## harness

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-harness` | `docs/harness/overview`, `docs/harness/agent-controller`, `docs/harness/durable-agents`, `docs/harness/background-tasks`, `docs/harness/goals`, `reference/agent-controller/*`, `reference/agents/durable-agent`, `reference/coding-agent/*`, `reference/code-sdk/*`, `reference/workers/*` |
| 2 | `mastra-schedules` | `docs/harness/schedules`, `docs/workflows/scheduled-workflows`, `reference/schedules/*` |
| 3 | `mastra-signals` | `docs/signals/*`, `reference/signals/*` |

## sandbox-and-browser

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-workspace-sandbox` | `docs/sandbox/*`, `reference/workspace/*`, `integrations/sandboxes/*`, `integrations/file-storage/*` |
| 2 | `mastra-browser` | `docs/browser`, `reference/browser/*`, `integrations/browsers/*` |

## connections

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-mcp` | `docs/connections/mcp`, `reference/tools/mcp-client`, `reference/tools/mcp-server`, `docs/guides/mcp-authentication-authorization` |
| 2 | `mastra-a2a-acp` | `docs/connections/overview`, `docs/connections/a2a`, `docs/connections/acp`, `docs/connections/sdk-agents`, `reference/acp/*` |
| 3 | `mastra-channels` | `docs/channels`, `integrations/channels/*`, `reference/channels/*`, `reference/agents/channels` |
| 4 | `mastra-tool-integrations` | `integrations/tools/*`, `docs/mastra-platform/connect/*`, `reference/connect/*` |

## server-and-frontend

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-server` | `docs/server/overview`, `docs/server/custom-api-routes`, `docs/server/middleware`, `docs/server/request-context`, `docs/server/server-adapters`, `docs/server/custom-adapters`, `docs/server/pubsub`, `reference/server/*`, `reference/pubsub/*` |
| 2 | `mastra-client-sdk` | `docs/server/mastra-client`, `reference/client-js/*` |
| 3 | `mastra-framework-integration` | `integrations/frameworks/*` |
| 4 | `mastra-agentic-ui` | `integrations/agentic-ui/*`, `reference/ai-sdk/*` |
| 5 | `mastra-auth` | `docs/auth/*`, `integrations/auth/*`, `reference/auth/*`, `docs/guides/authentication-identity` |

## quality

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-evals` | `docs/evals/overview`, `docs/evals/built-in-scorers`, `docs/evals/custom-scorers`, `docs/evals/quick-checks`, `docs/evals/evals-with-memory`, `docs/evals/multi-turn`, `reference/evals/*` |
| 2 | `mastra-datasets-experiments` | `docs/evals/datasets`, `docs/evals/experiments`, `docs/evals/gates-and-verdicts`, `docs/evals/running-in-ci`, `docs/evals/vitest-integration`, `docs/guides/build-an-eval-loop`, `reference/datasets/*` |
| 3 | `mastra-observability` | `docs/observability/*`, `integrations/observability/*`, `reference/observability/*`, `reference/logging/*` |
| 4 | `mastra-studio-editor` | `docs/studio/*`, `reference/editor/*` |

## deploy-and-platform

| # | Skill | Sources |
|---|---|---|
| 1 | `mastra-deployment` | `docs/deployment/*`, `integrations/deploy/*`, `reference/deployer/*` |
| 2 | `mastra-platform` | `docs/mastra-platform/*` (except `connect/`), official platform reference |
| 3 | `mastra-cli-api` | `reference/cli/mastra`, official mastra-api and trace-query references |
