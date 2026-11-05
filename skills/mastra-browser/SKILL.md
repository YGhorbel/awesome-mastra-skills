---
name: mastra-browser
description: "Give a Mastra agent a real web browser: navigate pages, click and type, fill forms, extract data, take screenshots, and record sessions, using AgentBrowser (Playwright with accessibility refs), StagehandBrowser (natural language actions), FirecrawlBrowser (hosted sessions), or BrowserViewer (CLI tools over CDP). Use this skill whenever the user wants an agent to browse websites, scrape JavaScript-rendered pages, automate a multi-step web task, log in to a site, connect to Browserbase or another cloud browser, or watch the agent browse live in Studio. Triggers on MastraBrowser, @mastra/agent-browser, AgentBrowser, @mastra/stagehand, StagehandBrowser, @mastra/browser-firecrawl, FirecrawlBrowser, @mastra/browser-viewer, BrowserViewer, browser_snapshot, stagehand_act, cdpUrl, browser scope, setCookies, screencast, browser recording, browser-use, agent-browser CLI. Also triggers for web automation or computer-use-on-the-web requests in a Mastra project even if the user does not say browser."
license: Apache-2.0
metadata:
  category: sandbox-and-browser
  catalog_summary: "Browser providers for agents: AgentBrowser, Stagehand, Firecrawl, BrowserViewer, scope, cookies, cloud CDP, screencast"
  display_order: 2
  docs: https://mastra.ai/docs/browser
---

# Mastra Browser

Attach a browser provider to an agent so it can navigate, interact with, and extract from real web pages, with the right provider, scope, and credentials handling.

---

## When to use

- An agent must open URLs, click, type, select, scroll, or submit forms
- Pages render with JavaScript or need a login, so a plain HTTP fetch fails
- Choosing between deterministic refs (AgentBrowser) and natural language actions (Stagehand)
- Running browsers in the cloud (Firecrawl, Browserbase, Browser Use Cloud, any CDP endpoint)
- Driving a browser through a CLI (`browser-use`, `agent-browser`, `browse`) from a workspace sandbox
- Isolating browsers per conversation thread, or sharing one
- Signing the browser in with cookies the model never sees
- Watching the agent live in Studio (screencast) or recording a session

## When NOT to use

- Shell commands, files, sandboxes, or full desktop control (use `mastra-workspace-sandbox`)
- Prebuilt scraping and search tool integrations without a browser (use `mastra-tool-integrations`)
- Writing your own fetch or scraping tool (use `mastra-tools`)
- Approval before risky browser actions in general (use `mastra-agent-approval-hitl`)
- Typed extraction results from the agent itself (use `mastra-structured-output`)

---

## Required inputs

- The task: which sites, which actions, and what data comes back
- Determinism vs flexibility: fixed flows favor AgentBrowser, varied layouts favor Stagehand
- Where the browser runs: local Chromium, a cloud service, or an existing CDP endpoint
- Concurrency: one browser per thread (default) or one shared browser
- Whether the agent needs to be signed in, and how your app obtains that session
- Whether the agent's model supports vision (screenshot tools)

---

## The framework: provider on the agent, tools come with it

Assign a provider to the agent's `browser` option. Mastra adds the provider's tools to the agent automatically.

| Provider | Package | Kind | Tools | Pick it when |
|---|---|---|---|---|
| `AgentBrowser` | `@mastra/agent-browser` | SDK (Playwright) | 16 `browser_*` tools using refs like `@e5` | Reproducible, fast, precise automation |
| `StagehandBrowser` | `@mastra/stagehand` | SDK (Stagehand, AI) | 7 `stagehand_*` tools (`act`, `extract`, `observe`, ...) | Elements are easier to describe than to target; Browserbase |
| `FirecrawlBrowser` | `@mastra/browser-firecrawl` | SDK, extends AgentBrowser | Same as AgentBrowser | No local Chromium; hosted sessions |
| `BrowserViewer` | `@mastra/browser-viewer` | CLI | None; agent runs CLI commands through `execute_command` | Agent already uses a browser CLI in a sandbox |

```typescript
import { Agent } from '@mastra/core/agent'
import { AgentBrowser } from '@mastra/agent-browser'

const browser = new AgentBrowser({
  headless: true,
  viewport: { width: 1280, height: 720 },
  scope: 'thread',
})

export const browserAgent = new Agent({
  id: 'browser-agent',
  name: 'Browser Agent',
  instructions: `You can browse the web. Use browser_snapshot to see the page structure,
then interact with elements using their refs (e.g., @e5).`,
  model: 'openai/gpt-6.1-sol',
  browser,
})
```

`BrowserViewer` is different: it goes on the `Workspace` (`browser` option) next to a sandbox, not on the agent.

### Scope

| `scope` | Behavior | Use |
|---|---|---|
| `'thread'` (default) | One browser per memory thread | Concurrent users, full isolation |
| `'shared'` | One browser for all threads | Cheaper, non-conflicting tasks |

Setting `cdpUrl` forces `'shared'`, because Mastra cannot spawn new instances of an external browser.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read the embedded docs in `node_modules/@mastra/agent-browser/dist/docs/` (or the installed provider) and its types. Otherwise fetch `https://mastra.ai/docs/browser.md` and the provider page, for example `https://mastra.ai/reference/browser/agent-browser.md`. Trust these over memory.
2. **Pick the provider** from the table above. Install it (`npm install @mastra/agent-browser`).
3. **Pick where it runs.** Local launch needs Chromium (`npx playwright install chromium` if missing). Cloud: Firecrawl `apiKey`, Stagehand `env: 'BROWSERBASE'`, or `cdpUrl` for any CDP service.
4. **Set scope** to `'thread'` for multi-user apps. Use memory so each conversation has a thread.
5. **Write tool-aware instructions.** AgentBrowser: snapshot, act by ref, snapshot again to verify. Stagehand: name `stagehand_act`, `stagehand_extract`, `stagehand_observe`.
6. **Trim tools.** Use `excludeTools` to drop `browser_screenshot` or `stagehand_screenshot` for non-vision models, and `browser_evaluate` if arbitrary JavaScript is too broad.
7. **Handle sign-in outside the model.** Call `browser.setCookies(cookies, threadId)` from app code.
8. **Enable observability.** Install `ws` and `@hono/node-ws` for Studio screencast. Add `recording.outputDir` if runs must be reviewable.
9. **Register and test** in Studio (`npx mastra dev`), watching the screencast. Close browsers on shutdown with `browser.close()`.

---

## Deep dive: signed-in browsing without exposing secrets

The model never sees cookie values set with `setCookies`. With `'thread'` scope, cookies reach only that thread's browser. If the browser has not launched yet, they apply when it does.

```typescript
await browser.setCookies(
  [
    {
      name: 'my_app_session',
      value: sessionToken,
      domain: 'app.example.com',
      path: '/',
      httpOnly: true,
      secure: true,
    },
  ],
  threadId,
)
```

Each cookie needs `url`, or both `domain` and `path`, otherwise `setCookies` throws. Start `domain` with a dot to cover subdomains. With `'shared'` scope the cookies reach every thread, so use `'thread'` scope for per-user sessions. Pending cookies are dropped on `close()` and, with `'thread'` scope, on `closeThreadSession(threadId)`.

Firecrawl has its own persistence: `firecrawl.profile: { name, saveChanges: true }` keeps login state in Firecrawl's infrastructure. It is not the local `profile` option inherited from AgentBrowser.

---

## Failure patterns

- **`browser executable is missing`.** Local AgentBrowser needs Playwright's Chromium. Run `npx playwright install chromium`, or connect with `cdpUrl`.
- **Clicking by CSS selector with AgentBrowser.** Its tools take refs from `browser_snapshot`. Instruct the agent to snapshot first and re-snapshot after page changes.
- **Users seeing each other's sessions.** `scope: 'shared'` or a `cdpUrl` puts all threads in one browser. Use `'thread'` scope with memory threads, or one CDP session per user via an async `cdpUrl` function.
- **Putting passwords or session tokens in prompts.** Use `setCookies` from app code, or a Firecrawl profile.
- **Screenshot tool on a non-vision model.** Calls fail or waste tokens. Use `excludeTools`.
- **No screencast in Studio.** Install `ws` and `@hono/node-ws`. They are left out on purpose for serverless targets such as Cloudflare Workers.
- **Putting `BrowserViewer` on the agent.** It belongs on `new Workspace({ sandbox, browser })` and has no tools of its own; the agent runs CLI commands.
- **BrowserViewer CLI not installed.** Install the CLI in the sandbox environment and add its skill (for example `npx skills add browser-use/browser-use --skill browser-use`).
- **Stagehand without a model key.** Stagehand calls a model for every action. Set `model` and the provider env var (`OPENAI_API_KEY` for `openai/...`).
- **Expecting more than one recording at once.** Only one recording can be active per process. Default max 30 s, hard cap 120 s.
- **Unbounded `browser_evaluate`.** It runs arbitrary JavaScript in the page. Exclude it unless the task needs it.

---

## Output format

A finished browser delivery contains:

- `src/mastra/browsers/<name>.ts` (or inline) creating the provider
- The agent with `browser` set (or a `Workspace` with `BrowserViewer` and a sandbox)
- Instructions that name the provider's tools and the snapshot-act-verify loop
- Env vars in `.env.example` (`FIRECRAWL_API_KEY`, `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID`, model keys)
- Memory configured when `scope: 'thread'` should isolate conversations
- Evidence: a Studio run with the screencast, or a recording path

---

## Reference files

- [`references/api.md`](references/api.md) - `MastraBrowser` options and methods, and each provider's options and tools.
- [`references/examples.md`](references/examples.md) - Local AgentBrowser agent, Stagehand on Browserbase, Firecrawl hosted sessions, BrowserViewer with a CLI.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist.

**Live docs**

- https://mastra.ai/docs/browser
- https://mastra.ai/reference/browser/mastra-browser
- https://mastra.ai/reference/browser/agent-browser
- https://mastra.ai/reference/browser/stagehand-browser
- https://mastra.ai/reference/browser/firecrawl-browser
- https://mastra.ai/reference/browser/browser-viewer
- https://mastra.ai/integrations/browsers/agent-browser
- https://mastra.ai/integrations/browsers/stagehand
- https://mastra.ai/integrations/browsers/firecrawl
- https://mastra.ai/integrations/browsers/browser-viewer
