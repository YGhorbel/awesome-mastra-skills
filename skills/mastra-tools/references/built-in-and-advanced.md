# Built-in tools, code mode, and tool search

Distilled from `https://mastra.ai/docs/agents/tools.md`, `https://mastra.ai/docs/agents/code-mode.md`, the built-in tool references, the code mode transport references, and `https://mastra.ai/reference/processors/tool-search-processor.md`.

## Contents

- Built-in tools table
- webSearchTool
- webFetchTool
- askUserTool
- submitPlanTool
- Task tools
- Code mode
- Code mode transports
- ToolSearchProcessor

---

## Built-in tools

All import from `@mastra/core/tools`. Each has an export name and a tool ID the model sees.

| Export | Tool ID | Purpose |
|---|---|---|
| `askUserTool` | `ask_user` | Ask the user a question and wait for the answer |
| `submitPlanTool` | `submit_plan` | Submit a plan file for approval |
| `taskWriteTool` | `task_write` | Create or replace the task list |
| `taskUpdateTool` | `task_update` | Update one task by ID |
| `taskCompleteTool` | `task_complete` | Mark one task completed |
| `taskCheckTool` | `task_check` | Check task list completion |
| `webSearchTool` | provider-defined | Provider native web search |
| `webFetchTool` | `web_fetch` | Fetch a URL and return its text |

The AgentController includes all built-in tools in every mode automatically (see `mastra-harness`).

---

## `webSearchTool`

```typescript
import { Agent } from '@mastra/core/agent'
import { webSearchTool } from '@mastra/core/tools'

export const researchAgent = new Agent({
  id: 'research-agent',
  name: 'Research Agent',
  instructions: 'Use web search when you need current information.',
  model: 'openai/gpt-6.1-sol',
  tools: { search: webSearchTool },
})
```

- Resolved at run time from the active model's provider.
- Supports OpenAI, Anthropic, Google Gemini, and xAI. Other providers fail with `MastraError`.
- Resolved IDs: `openai.web_search`, `anthropic.web_search_20250305`, `google.google_search`, `xai.web_search`.
- The key (`search`) is only the agent-local name.

## `webFetchTool`

```typescript
import { webFetchTool } from '@mastra/core/tools'

// tools: { fetch: webFetchTool }
```

- Input: `url`. Output: `content`, `truncated`, `status`, `statusText`, `contentType`, `url`, `ok`.
- Only `http:` and `https:`. Blocks `localhost` and private or reserved IPs, including after DNS resolution.
- Truncates at 100,000 characters (`truncated: true`). At most 5 redirects. 15 second timeout.
- Failures return `isError: true` with the reason in `content`. They do not throw.

---

## `askUserTool`

Suspends the run with a `tool-call-suspended` event. Resume with `agent.resumeStream(answer, { runId })`. Outside an agent run it returns a readable fallback string.

Input (from the model):

| Field | Notes |
|---|---|
| `question` | Non-empty string. |
| `options` | `{ label, description? }[]`. Omit for free text. |
| `selectionMode` | `'single_select'` (default with options) or `'multi_select'`. Requires `options`. |

Suspend payload: `question`, `options`, `selectionMode` (omitted for free text).

Resume data: a `string` for free text and single select, a `string[]` for multi select.

```typescript
await agent.resumeStream(['Add tests', 'Update docs'], { runId: stream.runId })
```

Pair with `autoResumeSuspendedTools` to resume from the next chat message (see `mastra-agent-approval-hitl`).

## `submitPlanTool`

The agent writes a Markdown plan file and calls `submit_plan` with `{ path }`. The run suspends.

- Suspend payload: `toolId: 'submit_plan'`, `path`, and `title`/`plan` filled by the host.
- Resume data: `{ action: 'approved' | 'rejected', feedback?, path?, title?, plan? }`.
- Approved: the model is told to proceed with the approved plan.
- Rejected with feedback: the model revises and resubmits.
- Rejected without feedback: the model waits for the next user message.

```typescript
await agent.resumeStream(
  { action: 'rejected', feedback: 'Add error handling steps' },
  { runId: stream.runId },
)
```

---

## Task tools

Require memory (`threadId` + `resourceId`). Without memory they return an error. The list lives in thread-scoped `threadState` storage and survives observational memory truncation. Only one task can be `in_progress`.

Recommended setup bundles all four tools plus `TaskStateProcessor`:

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { TaskSignalProvider } from '@mastra/core/signals'

const agent = new Agent({
  id: 'coder',
  name: 'Coder',
  instructions: 'Track your progress with the task tools.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory(),
  signals: [new TaskSignalProvider()],
})
```

Or attach the tools directly: `tools: { taskWriteTool, taskUpdateTool, taskCompleteTool, taskCheckTool }`.

| Tool | Input | Behavior |
|---|---|---|
| `task_write` | `tasks: { id?, content, status, activeForm }[]` | Replaces the whole list. Multiple `in_progress` returns an error. |
| `task_update` | `id` plus at least one of `content`, `status`, `activeForm` | Setting `in_progress` demotes the other in-progress task. |
| `task_complete` | `id` | Unknown ID returns an error with available IDs. |
| `task_check` | none | Returns `content`, `tasks`, `summary` (`total`, `completed`, `inProgress`, `pending`, `incomplete`, `hasTasks`, `allCompleted`), `incompleteTasks`, `isError`. |

---

## Code mode

Added in `@mastra/core@1.38.0`. The model writes one TypeScript function that calls your tools as `external_<id>` functions and returns one aggregated result. Tools still run on the host with validation, request context, and tracing. Only the orchestration code runs in the boundary.

```typescript
import { Agent } from '@mastra/core/agent'
import { createCodeMode } from '@mastra/core/tools'
import { LocalSandbox } from '@mastra/core/workspace'

const { tool, instructions } = createCodeMode({
  tools: { getTopProducts, getProductRatings },
  sandbox: new LocalSandbox(), // runs model code on the host: trusted or local dev only
})

const agent = new Agent({
  id: 'shop-assistant',
  name: 'shop-assistant',
  instructions: ['You are a helpful shopping assistant.', instructions],
  model: 'openai/gpt-6.1-sol',
  tools: { execute_typescript: tool },
})
```

`createCodeMode(config, transport?)`:

| Config | Notes |
|---|---|
| `tools` | Allow-list exposed as `external_<id>`. |
| `sandbox` | Required unless the agent's workspace provides one or the transport isolates on its own. |
| `timeout` | Execution timeout in ms. Covers async hangs and sync infinite loops with in-process transports. |
| `id` | Tool id. Default `execute_typescript`. |

Returns `{ tool, instructions }`. Always add `instructions` to the agent.

Tool result (`CodeModeToolResult`): `success`, `result`, `logs` (captured console output), `error: { message, name?, line? }`.

Related helpers:

- `createCodeModeInstructions({ tools })` prints the generated prompt with one `declare function external_<id>(...)` per tool. Conflicting sanitized names throw.
- `createCodeModeTool({ tools, sandbox })` returns only the tool. Prefer `createCodeMode()`.

Scope least privilege by calling `createCodeMode()` several times with distinct `id`s (`sales_code`, `inventory_code`). Each instance can only call its own tools.

Use code mode when a query touches several tools, results can be reduced before reaching the model, math must be exact, or calls can run in parallel with `Promise.all`. Keep each tool focused.

## Code mode transports

| | `StdioCodeModeTransport` (default) | `IsolatedVmCodeModeTransport` | `QuickJsCodeModeTransport` |
|---|---|---|---|
| Package | `@mastra/core` | `@mastra/isolated-vm` | `@mastra/quickjs` |
| Boundary | Workspace sandbox | V8 isolate | QuickJS WebAssembly |
| Needs a sandbox | Yes | No | No |
| Native binary | Node.js in the sandbox | Yes | No |
| Node flags | None | `--no-node-snapshot` on Node 20+ | None |
| Runs in browser | No | No | Yes |
| Speed | Fastest | Fast | Slowest (compute-heavy code) |

```typescript
import { createCodeMode } from '@mastra/core/tools'
import { QuickJsCodeModeTransport } from '@mastra/quickjs'

const { tool, instructions } = createCodeMode(
  { tools }, // no sandbox needed
  new QuickJsCodeModeTransport({ memoryLimitMb: 128 }),
)
```

- `IsolatedVmCodeModeTransport({ memoryLimitMb })`. Start the host with `NODE_OPTIONS=--no-node-snapshot`.
- `QuickJsCodeModeTransport({ memoryLimitMb, maxStackSizeBytes, module })`. Good for serverless hosts that block native addons and Node flags.
- Remote sandboxes such as E2B need a transport that writes into the sandbox: `new E2BCodeModeTransport()` from `@mastra/e2b`, with `sandbox: new E2BSandbox()`.

---

## `ToolSearchProcessor`

An input processor that gives the agent two meta-tools, `search_tools` and `load_tool`, instead of every tool up front.

```typescript
import { Agent } from '@mastra/core/agent'
import { ToolSearchProcessor } from '@mastra/core/processors'

const agent = new Agent({
  id: 'dynamic-tools-agent',
  name: 'dynamic-tools-agent',
  instructions:
    'You are a helpful assistant with access to many tools. Use search_tools to find relevant tools, then load_tool to make them available.',
  model: 'openai/gpt-6.1-sol',
  inputProcessors: [
    new ToolSearchProcessor({ tools: allTools, search: { topK: 5, minScore: 0.1 } }),
  ],
})
```

| Option | Notes |
|---|---|
| `tools` | All searchable tools. Fixed at construction. |
| `includeResolvedTools` | Also index per-request tools (dynamic `tools` functions, credentialed MCP tools) and withhold them until loaded. Applies to memory, workspace, skill, and browser tools too. |
| `search.topK` | Max results. |
| `search.minScore` | Raw BM25 plus name boosts (+5 exact id term, +2 partial). Not normalized. Use 0 to 0.5. |
| `search.autoLoad` | Activate matches during search and hide `load_tool`. Keep `topK` small (for example 3). |
| `storage` | `'in-memory'` (default, per thread, TTL, lost on restart) or `'context'` (derived from messages, opt-in). |
| `ttl` | In-memory TTL in ms. Default one hour. `0` disables cleanup. |
| `filter` | `({ toolName, tool, requestContext, phase }) => boolean`. Phases: `search`, `load`, `active`. Throwing means disallowed. |

Loaded tools become available on the next turn. Loads are append-only, which keeps the cached prompt prefix stable. In-memory state helpers: `clearState(threadId)`, `clearAllState()`, `getStateStats()`, `cleanupNow()`.

Place `TokenLimiter` after `ToolSearchProcessor` when combining them (see `mastra-processors-guardrails`).
