# Routing examples

How common requests map to features and a chain of skills. Apply the skills in order.

## 1. "Build a customer support chatbot for our website"

Features: agent, tools for order lookup, memory per user, guardrails, chat UI, auth, evals.

1. `mastra-project-setup` (or `mastra-framework-integration` if adding to an existing Next.js app)
2. `mastra-agents` then `mastra-tools` (order lookup, refund request)
3. `mastra-memory` (resource = user id, thread = conversation id)
4. `mastra-processors-guardrails` (PII redaction, prompt injection)
5. `mastra-agent-approval-hitl` (approve refunds above a limit)
6. `mastra-agentic-ui` (useChat with `chatRoute`), `mastra-auth`
7. `mastra-evals`, `mastra-observability`, then `mastra-deployment`

## 2. "Process every uploaded invoice and flag mismatches for a human"

Features: workflow (fixed steps), structured extraction, human review, retries.

1. `mastra-workflows` (extract, match, decide)
2. `mastra-structured-output` (typed invoice fields from an agent step)
3. `mastra-workflow-suspend-resume` (suspend on mismatch, resume with reviewer decision)
4. `mastra-storage` (Postgres for snapshots in production)
5. `mastra-datasets-experiments` (golden invoices as a regression set)

## 3. "Answer questions from our 5,000 PDF manuals with citations"

Features: ingestion, chunking, embeddings, vector store, retrieval tool.

1. `mastra-rag` (MDocument, chunk, embed, vector query tool)
2. `mastra-vector-stores` (choose pgvector, Pinecone, Qdrant, etc.)
3. `mastra-models` (embedding model)
4. `mastra-agents` (agent that must cite retrieved chunks)
5. `mastra-evals` (faithfulness and context relevance scorers)

Consider `mastra-knowledge` instead when content is managed by users and needs scopes and access control.

## 4. "A coding agent that edits files and runs tests in isolation"

1. `mastra-workspace-sandbox` (filesystem, sandbox provider such as E2B, Daytona, or Docker)
2. `mastra-harness` (AgentController or the coding agent factory, background tasks, goals)
3. `mastra-agent-approval-hitl` (approve shell commands)
4. `mastra-signals` (task tracking with `TaskSignalProvider`)

## 5. "A Slack bot that triages incidents every morning"

1. `mastra-channels` (Slack provider)
2. `mastra-schedules` (daily run)
3. `mastra-mcp` or `mastra-tool-integrations` (PagerDuty, GitHub, Linear tools)
4. `mastra-multi-agent` (triage supervisor with specialist subagents)

## 6. "Expose our Mastra tools to Claude Desktop and Cursor"

1. `mastra-mcp` (MCPServer)
2. `mastra-auth` (protect the endpoint), `mastra-deployment`

## 7. "Our agent's answers got worse after a prompt change"

1. `mastra-observability` (compare traces before and after)
2. `mastra-datasets-experiments` (run both prompt versions against a dataset)
3. `mastra-studio-editor` (version prompts in the Editor)

## 8. "It throws Cannot find module or Property does not exist"

1. `mastra-troubleshooting`
2. `mastra-migrations` if the code was written for an older version
