# Tool integrations API reference

Distilled from `https://mastra.ai/integrations/tools/*.md` and `https://mastra.ai/reference/connect/*.md`. Verify against the installed version.

## Contents

- Tavily
- Bright Data
- Parallel
- Perplexity
- Firecrawl (hand-built)
- Connect: tools()
- Connect: channels()
- Connect: credential()
- Connect env vars and errors

---

## Tavily (`@mastra/tavily`)

Install `@mastra/tavily @tavily/core zod`. Config (`TavilyClientOptions`): `apiKey` (falls back to `TAVILY_API_KEY`), `clientName` (default `'mastra'`), `apiBaseURL`, `proxies`, `projectId`.

| Factory | Tool ID | Key inputs |
|---|---|---|
| `createTavilyTools(config?)` | returns `{ tavilySearch, tavilyExtract, tavilyCrawl, tavilyMap }` | |
| `createTavilySearchTool(config?)` | `tavily-search` | `query`, `searchDepth` (`'basic' \| 'advanced' \| 'fast' \| 'ultra-fast'`), `maxResults` (1-20), `includeAnswer`, `includeImages`, `includeRawContent` (`false \| 'markdown' \| 'text'`), `includeDomains`, `excludeDomains`, `timeRange` |
| `createTavilyExtractTool(config?)` | `tavily-extract` | `urls` (1-20), `extractDepth`, `query`, `includeImages`, `format` (`'markdown'` default) |
| `createTavilyCrawlTool(config?)` | `tavily-crawl` | Crawl a site from a URL |
| `createTavilyMapTool(config?)` | `tavily-map` | Map a site's URLs |

## Bright Data (`@mastra/brightdata`)

Install `@mastra/brightdata zod`. Config (`BrightDataClientOptions` from `@brightdata/sdk`): `apiKey` (falls back to `BRIGHTDATA_API_TOKEN`), plus `bdclient` fields such as `timeout`, `webUnlockerZone`, `serpZone`, `rateLimit`.

| Factory | Tool ID | Input | Output |
|---|---|---|---|
| `createBrightDataTools(config?)` | returns `{ webSearch, webFetch }` | | |
| `createBrightDataSearchTool(config?)` | `brightdata-search` | `query`, `country?`, `start?` | `{ query, results: [{ link, title, description }], currentPage }` |
| `createBrightDataFetchTool(config?)` | `brightdata-fetch` | `url` | `{ url, content }` (Markdown) |

Search uses Google through the SERP API. Fetch uses Web Unlocker.

## Parallel (`@mastra/parallel`)

Install `@mastra/parallel parallel-web zod`. Config (`ParallelClientOptions`): `apiKey` (falls back to `PARALLEL_API_KEY`), `baseURL` (`PARALLEL_BASE_URL`), `timeout`, `fetch`, `fetchOptions`, `maxRetries` (2), `defaultHeaders`, `defaultQuery`, `logLevel`, `logger`. `getParallelClient()` returns the official client. The client initializes at first execution, so a missing key fails then.

| Factory | Tool ID | Key inputs |
|---|---|---|
| `createParallelTools(config?)` | returns `{ parallelSearch, parallelExtract }` | |
| `createParallelSearchTool(config?)` | `parallel-search` | `searchQueries`, `objective`, `mode` (`'advanced'` default), `maxResults`, `includeDomains`, `excludeDomains`, `afterDate`, `location`, `fetchPolicy`, `sessionId` |
| `createParallelExtractTool(config?)` | `parallel-extract` | `urls` (1-20), `objective`, `searchQueries`, `fullContent`, `excerptMaxCharsPerResult`, `maxCharsTotal`, `fetchPolicy`, `sessionId` |

## Perplexity (`@mastra/perplexity`)

Install `@mastra/perplexity zod`. Config (`PerplexityClientOptions`): `apiKey` (falls back to `PERPLEXITY_API_KEY`, then `PPLX_API_KEY`), `baseUrl` (default `'https://api.perplexity.ai'`), `fetch`.

| Factory | Tool ID | Input | Output |
|---|---|---|---|
| `createPerplexityTools(config?)` | returns `{ perplexitySearch }` | | |
| `createPerplexitySearchTool(config?)` | `perplexity-search` | `query`, `maxResults` (1-20), `searchDomainFilter` (prefix `-` to exclude, do not mix), `searchRecencyFilter`, `searchAfterDateFilter`, `searchBeforeDateFilter` (`m/d/yyyy`) | `{ query, results: [{ title, url, snippet, date? }] }` |

## Firecrawl (hand-built)

No Mastra package. `npm install firecrawl`, then wrap the SDK with `createTool`:

- `new Firecrawl({ apiKey: process.env.FIRECRAWL_API_KEY!, apiUrl? })` from `firecrawl`
- `firecrawl.search(query, { limit })` returns `results.web`
- `firecrawl.scrape(url, { formats: ['markdown'], onlyMainContent: true })` returns `result.markdown`
- Self-hosted: `FIRECRAWL_API_URL`

---

## Connect: `tools(options?)` (`@mastra/connect`)

Returns a `ToolsResolver`, a flat record keyed by tool key (`<provider>_<action>`). Pass it as an agent's `tools`, or call it: `await resolver()`.

| Option | Notes |
|---|---|
| `projectId` | Falls back to `MASTRA_PROJECT_ID`. |
| `providers` | Array form: allowlist. Record form: `true`/`{}` enable, `false` exclude, or `ToolsProviderOptions`. Unknown enabled IDs fail with `invalid_options`. |
| `allowTools` / `disallowTools` | Top-level defaults, keys or `*` globs, mutually exclusive. Lenient per provider. |
| `requireApproval` | `boolean \| string[]`. Default for providers without their own. Never gates `<provider>__list_connections`. |
| `client` | `{ accessToken?, orgId?, baseUrl?, fetch? }`. |
| `ttlMs` | Default 30000. `0` revalidates each time. |

Callback form: `tools(ctx => options)` receives `{ requestContext }`. Memoized per distinct options value (max 32, LRU).

`ToolsProviderOptions`: `connectionId`, `allowTools`, `disallowTools` (strict, unknown keys fail), `requireApproval` (`true`, `false`, or keys and globs).

Resolver methods: `refresh()`, `disconnect()`, `with(extra)` (merge extra tools, extras win).

MCP providers (`attio-mcp`, `canva-mcp`, `clay-mcp`, `neon-mcp`, `render-mcp`, `robinhood-mcp`, `sanity-mcp`) expose tools named `<provider-id>_<tool-name>` discovered at runtime.

## Connect: `channels(options?)`

`await channels(options)` returns a `ChannelsResolver` for `new Mastra({ channels })`.

| Option | Notes |
|---|---|
| `projectId`, `client`, `ttlMs` | As for `tools()`. |
| `providers` | IDs: `slack-channels` (alias `slack`, never both), `telegram`, `discord`, `microsoft-teams`. Array allowlist or record. |
| `providers.<id>.connectionId` | Pin a connection. |
| `providers.<id>.providerOptions` | Forwarded to the channel constructor (for example Discord `applicationId`, `publicKey`, `permissions`). Credential fields are stripped. |

Resolver: callable, `getRoutes()`, `refresh()`, `disconnect()`. Implementations load from `@mastra/slack`, `@mastra/telegram`, `@mastra/discord`, `@mastra/teams`.

## Connect: `credential(connectionId, { client? })`

Returns `Promise<ConnectionCredential>`:

```typescript
type ConnectionCredential =
  | { type: 'oauth2'; accessToken: string; expiresAt: string | null; secondaryAccessTokens?: Record<string, { accessToken: string; expiresAt: string | null }> }
  | { type: 'api_key'; apiKey: string }
  | { type: 'two_step'; token: string; expiresAt: string | null }
```

Re-fetch when `expiresAt` passes. Basic auth throws `unsupported_credential_type`.

## Connect env vars and errors

| Variable | Purpose |
|---|---|
| `MASTRA_PLATFORM_ACCESS_TOKEN` | Platform token (required) |
| `MASTRA_PLATFORM_SECRET_KEY` | Fallback token |
| `MASTRA_PROJECT_ID` | Project with the connections |
| `MASTRA_ORG_ID` | Sent as `x-organization-id` |
| `MASTRA_PLATFORM_REGION` | `us` or `eu` |
| `MASTRA_INTEGRATIONS_API_URL` | Overrides region base URL |
| `MASTRA_SERVER_URL` | Public URL for channel webhooks off-platform |
| `MASTRA_ENCRYPTION_KEY` | Encrypts Telegram webhook and Teams bot secrets |

`MastraConnectError.code`: `missing_project_id`, `missing_access_token`, `invalid_options`, `unauthorized`, `proxy_error` (`status`, `detail`), `unknown_connection`, `platform_error`, `connection_not_found`, `unsupported_credential_type`, `no_active_connection`.

CLI: `mastra auth login`, `mastra auth tokens create <name>`, `mastra connect add <provider-id>`, `mastra connect list` (see `mastra-cli-api`).
