# Tool integration providers

Comparison of the web tool packages and the Mastra Connect provider directory. Sourced from `https://mastra.ai/integrations/tools/*` and `https://mastra.ai/docs/mastra-platform/connect/providers`. Provider availability for Connect depends on the platform catalog and your installed `@mastra/connect`. Run `mastra connect list` for the live list.

## Contents

- Web tool packages
- Choosing a web provider
- Connect generated toolsets
- Connect MCP providers
- Connect channel providers

---

## Web tool packages

| Provider | Package and peers | Factories | Tool IDs | Env var | Capabilities |
|---|---|---|---|---|---|
| Tavily | `@mastra/tavily @tavily/core zod` | `createTavilyTools`, `createTavilySearchTool`, `createTavilyExtractTool`, `createTavilyCrawlTool`, `createTavilyMapTool` | `tavily-search`, `tavily-extract`, `tavily-crawl`, `tavily-map` | `TAVILY_API_KEY` | Search with optional answer, extract up to 20 URLs, crawl, map |
| Bright Data | `@mastra/brightdata zod` | `createBrightDataTools`, `createBrightDataSearchTool`, `createBrightDataFetchTool` | `brightdata-search`, `brightdata-fetch` | `BRIGHTDATA_API_TOKEN` | Google SERP results, unblocked page fetch as Markdown |
| Parallel | `@mastra/parallel parallel-web zod` | `createParallelTools`, `createParallelSearchTool`, `createParallelExtractTool` | `parallel-search`, `parallel-extract` | `PARALLEL_API_KEY` (`PARALLEL_BASE_URL`) | Objective-driven search with excerpts, extract up to 20 URLs |
| Perplexity | `@mastra/perplexity zod` | `createPerplexityTools`, `createPerplexitySearchTool` | `perplexity-search` | `PERPLEXITY_API_KEY` (or `PPLX_API_KEY`) | Ranked search with recency and date filters |
| Firecrawl | `firecrawl` (no Mastra package) | Build with `createTool` | your choice (docs use `firecrawl-search`, `firecrawl-scrape`) | `FIRECRAWL_API_KEY` (`FIRECRAWL_API_URL` self-hosted) | Search, scrape to Markdown or JSON |

All packaged tools are `createTool` instances with Zod schemas, so they work on agents, in workflows, and in Studio.

## Choosing a web provider

| Need | Good fit |
|---|---|
| One package with search, extract, crawl, and map | Tavily |
| Pages behind bot detection, geo-targeted Google results | Bright Data |
| Research tasks stated as an objective, token-budgeted excerpts | Parallel |
| Fresh results filtered by recency or date range | Perplexity |
| Self-hosted scraping or structured JSON extraction | Firecrawl |

Pair a search tool with a fetch or extract tool, and tell the agent in its instructions to search first, then read the best results.

---

## Connect generated toolsets

Tool keys are `<provider>_<action>` (for example `linear_create_issue`). Counts reflect the docs' package version.

| Provider ID | Provider | Tools | Channels |
|---|---|---|---|
| `clerk` | Clerk | 42 | |
| `discord` | Discord | 34 | yes |
| `fireflies` | Fireflies.ai | 27 | |
| `github` | GitHub | 49 | |
| `google-calendar` | Google Calendar | 43 | |
| `google-docs` | Google Docs | 37 | |
| `google-drive` | Google Drive | 32 | |
| `google-mail` | Gmail | 52 | |
| `google-sheet` | Google Sheets | 18 | |
| `hubspot` | HubSpot | 50 | |
| `incident-io` | incident.io | 66 | |
| `jira` | Jira | 38 | |
| `linear` | Linear | 46 | |
| `microsoft-excel` | Microsoft Excel | 27 | |
| `microsoft-powerpoint` | Microsoft PowerPoint | 18 | |
| `microsoft-teams` | Microsoft Teams | 25 | yes |
| `microsoft-word` | Microsoft Word | 18 | |
| `notion` | Notion | 44 | |
| `one-drive` | OneDrive | 20 | |
| `openai` | OpenAI | 26 | |
| `outlook` | Microsoft Outlook | 30 | |
| `posthog` | PostHog | 67 | |
| `resend` | Resend | 80 | |
| `sharepoint-online` | SharePoint Online | 53 | |
| `slack` | Slack | 52 | via `slack-channels` |
| `snowflake` | Snowflake | 15 | |
| `supabase` | Supabase | 27 | |
| `workos` | WorkOS | 40 | |

Example Linear keys: `linear_list_issues`, `linear_create_issue`, `linear_create_comment`, `linear_archive_issue`, `linear_delete_issue`. See `https://mastra.ai/reference/connect/providers` for every key.

## Connect MCP providers

Tools are discovered at runtime from the provider's hosted MCP server and named `<provider-id>_<tool-name>`.

| Provider ID | Provider |
|---|---|
| `attio-mcp` | Attio |
| `canva-mcp` | Canva |
| `clay-mcp` | Clay |
| `neon-mcp` | Neon |
| `render-mcp` | Render |
| `robinhood-mcp` | Robinhood |
| `sanity-mcp` | Sanity |

Gate risky MCP tools explicitly, for example `'neon-mcp': { requireApproval: ['neon-mcp_run_sql'] }`.

## Connect channel providers

| ID | Setup | Notes |
|---|---|---|
| `slack-channels` (alias `slack`) | `mastra connect add slack-channels`, OAuth | Platform rotates the configuration credential |
| `discord` | Create a bot, `mastra connect add discord`, enter bot token | Bot invite scopes `bot` and `applications.commands` |
| `telegram` | BotFather token, `mastra connect add telegram` | Set `MASTRA_ENCRYPTION_KEY`; webhook needs public HTTPS |
| `microsoft-teams` | `mastra connect add microsoft-teams`, Microsoft work account | First tenant connection may need Entra admin consent |

After connecting, link the channel to an agent in Studio. Channel behavior is covered in `mastra-channels`.
