# Browser API reference

Distilled from `https://mastra.ai/reference/browser/*.md` and `https://mastra.ai/docs/browser.md`. Verify against the installed version before relying on an option.

## Contents

- MastraBrowser base options
- MastraBrowser methods
- AgentBrowser
- FirecrawlBrowser
- StagehandBrowser
- BrowserViewer
- Recording

---

## MastraBrowser base options

`MastraBrowser` is abstract. Use a provider. Shared options:

| Option | Type | Default | Notes |
|---|---|---|---|
| `headless` | `boolean` | `true` | |
| `viewport` | `{ width, height } \| 'window'` | `{ width: 1280, height: 720 }` | `'window'` supported by AgentBrowser, and Stagehand over CDP. |
| `timeout` | `number` | provider-specific | AgentBrowser and Stagehand: `30000`. |
| `cdpUrl` | `string \| () => string \| Promise<string>` | | Connect to an existing browser. HTTP endpoints resolve to WebSocket. Forces `'shared'` scope. |
| `scope` | `'shared' \| 'thread'` | `'thread'` (`'shared'` with `cdpUrl`) | |
| `onLaunch` | `({ browser }) => void \| Promise<void>` | | After status `ready`. |
| `onClose` | `({ browser }) => void \| Promise<void>` | | Before close. |
| `screencast` | `{ format: 'jpeg' \| 'png', quality, maxWidth, maxHeight, everyNthFrame }` | enabled | Needs `ws` and `@hono/node-ws`. |

Properties: `id`, `name`, `provider`, `headless`, `status` (`pending|launching|ready|error|closing|closed`).

---

## MastraBrowser methods

| Method | Returns | Notes |
|---|---|---|
| `ensureReady()` | `Promise<void>` | Called before tool execution automatically. |
| `close()` | `Promise<void>` | Closes everything. Drops pending cookies. |
| `isBrowserRunning()` | `boolean` | |
| `setCurrentThread(threadId)` / `getCurrentThread()` | | Used by the agent runtime. |
| `hasThreadSession(threadId)` | `boolean` | |
| `closeThreadSession(threadId)` | `Promise<void>` | Thread scope: closes that browser. Shared: clears thread state. |
| `setCookies(cookies, threadId?)` | `Promise<void>` | `BrowserCookie` from `@mastra/core/browser`: `name`, `value`, plus `url` or `domain` + `path`, optional `expires` (seconds), `httpOnly`, `secure`, `sameSite`. Supported by AgentBrowser, BrowserViewer, FirecrawlBrowser, StagehandBrowser. |
| `getTools()` | `Record<string, Tool>` | |
| `startScreencast(options?)` | `Promise<ScreencastStream>` | Emits `frame` and `stop`. |
| `injectMouseEvent(params, threadId?)` / `injectKeyboardEvent(params, threadId?)` | | Used by Studio live interaction. |
| `getBrowserState(threadId?)` | `Promise<BrowserState \| null>` | `{ tabs: { url, title? }[], activeTabIndex, closeReason?, activeUrlChangeSource? }` |
| `getCurrentUrl(threadId?)` | `Promise<string \| null>` | |

---

## AgentBrowser

`import { AgentBrowser } from '@mastra/agent-browser'`. Deterministic, uses accessibility-tree refs.

Extra options: `recording` (`{ outputDir, maxDurationMs?, maxWidth?, maxHeight? }`, Beta), `excludeTools` (`BrowserToolName[]`). Local launch needs Playwright Chromium (`npx playwright install chromium`).

Core tools:

| Tool | Key inputs |
|---|---|
| `browser_goto` | `url`, `waitUntil` (`load \| domcontentloaded \| networkidle`), `timeout` |
| `browser_snapshot` | `interactiveOnly`, `maxDepth`. Returns refs like `@e5`. |
| `browser_click` | `ref`, `button`, `clickCount`, `modifiers` |
| `browser_type` | `ref`, `text`, `clear`, `delay` |
| `browser_press` | `key` (for example `Enter`, `Control+a`), `modifiers` |
| `browser_select` | `ref` plus one of `value`, `label`, `index` |
| `browser_scroll` | `direction`, `amount` (default 300), `ref` |
| `browser_screenshot` | `fullPage`, `path` (also saves to the workspace, honoring write-file settings) |
| `browser_close` | none |

Extended tools: `browser_hover` (`ref`), `browser_back`, `browser_dialog` (`triggerRef`, `action: accept \| dismiss`, `text`), `browser_wait` (`ref`, `state: visible \| hidden \| attached \| detached`, `timeout`), `browser_tabs` (`action: list \| new \| switch \| close`, `url`, `index`), `browser_drag` (`sourceRef`, `targetRef`), `browser_evaluate` (`script`, `returnValue`).

---

## FirecrawlBrowser

`import { FirecrawlBrowser } from '@mastra/browser-firecrawl'`. Extends AgentBrowser (same tools and options) with hosted Firecrawl Browser Sandbox sessions. No local Chromium.

| Option | Notes |
|---|---|
| `apiKey` | Falls back to `FIRECRAWL_API_KEY`. Constructor throws if neither is set. |
| `apiUrl` | Self-hosted Firecrawl. |
| `firecrawl.ttl` | Max session lifetime, seconds. |
| `firecrawl.activityTtl` | Idle timeout, seconds. |
| `firecrawl.streamWebView` | `boolean` |
| `firecrawl.profile` | `{ name, saveChanges? }`. `saveChanges: true` persists cookies and login state. |
| `firecrawl.integration`, `firecrawl.origin` | Labels. |

Session lifecycle: `'thread'` scope creates one Firecrawl session per thread on first use; `'shared'` creates one at launch. Sessions are deleted on close, including after partial failures.

---

## StagehandBrowser

`import { StagehandBrowser } from '@mastra/stagehand'`. AI-driven actions.

| Option | Default | Notes |
|---|---|---|
| `env` | `'LOCAL'` | `'BROWSERBASE'` for cloud. |
| `apiKey`, `projectId` | | Required with `BROWSERBASE`. |
| `model` | `'openai/gpt-5.5'` | Router string, or `{ modelName, apiKey, baseURL }`. |
| `selfHeal` | `true` | |
| `domSettleTimeout` | `5000` | ms |
| `verbose` | `1` | `0`, `1`, `2` |
| `systemPrompt` | | |
| `recording`, `excludeTools` | | `StagehandToolName[]` |

Tools:

| Tool | Inputs | Returns |
|---|---|---|
| `stagehand_act` | `instruction`, `variables` (for `%name%` substitution), `useVision`, `timeout` | `{ success, message?, action?, url? }` |
| `stagehand_extract` | `instruction`, optional JSON `schema` | `{ success, data?, hint?, error?, url? }` |
| `stagehand_observe` | `instruction?`, `onlyVisible`, `timeout` | `{ success, actions: { selector, description, method?, arguments? }[], url? }` |
| `stagehand_navigate` | `url`, `waitUntil` | |
| `stagehand_tabs` | `action`, `url`, `index` | |
| `stagehand_screenshot` | `fullPage` | PNG image |
| `stagehand_close` | none | |

AgentBrowser vs Stagehand: refs are exact and faster (no inference); Stagehand is adaptive and slower.

---

## BrowserViewer

`import { BrowserViewer } from '@mastra/browser-viewer'`. CLI provider (`providerType: 'cli'`). Place it on `new Workspace({ sandbox, browser })`.

| Option | Default | Notes |
|---|---|---|
| `cli` | | `'agent-browser' \| 'browser-use' \| 'browse' \| 'browse-cli'` |
| `headless` | `true` | |
| `cdpUrl` | | Connect instead of launching. Scope defaults to `'shared'`. |
| `cdpPort` | `0` (auto) | Only when launching. |
| `scope` | `'thread'` | |
| `viewport` | `{ width: 1280, height: 720 }` | |
| `executablePath` | Playwright Chromium | |
| `onLaunch`, `onClose`, `screencast` | | |

Methods: `launch(threadId?)`, `ensureReady()`, `isBrowserRunning(threadId?)`, `close()`, `getCdpUrl(threadId?)`, `connectToExternalCdp(cdpUrl, threadId?)`, `startScreencast()`, `injectMouseEvent()`, `injectKeyboardEvent()`.

CLI injection when the agent runs a matching command through the workspace execute tool:

| CLI | Install | Skill | CDP flag |
|---|---|---|---|
| `agent-browser` | `npm install -g agent-browser` | `npx skills add vercel-labs/agent-browser` | `--cdp` |
| `browser-use` | `pip install browser-use` | `npx skills add browser-use/browser-use --skill browser-use` | `--cdp-url` (stdin invocations get `BU_CDP_WS` and `BU_NAME` env instead) |
| `browse` | `npm install -g browse` | `browse skills install` | `--ws` |

---

## Recording

AgentBrowser and StagehandBrowser accept `recording: { outputDir }` (Beta). This adds `browser_record` (start, check, stop) and `browser_record_caption` (label actions, max 80 chars). Output is Motion-JPEG AVI, no `ffmpeg` needed. Default max duration 30 s, hard cap 120 s, max frame 1024 x 720, one active recording per process. A custom `outputPath` must resolve inside `outputDir`.
