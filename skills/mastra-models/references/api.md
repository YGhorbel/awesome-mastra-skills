# Models API reference

Distilled from `https://mastra.ai/models.md`, `https://mastra.ai/models/embeddings.md`, `https://mastra.ai/models/gateways/custom-gateways.md`, `https://mastra.ai/models/gateways/azure-openai.md`, `https://mastra.ai/reference/core/mastra-model-gateway.md`, and `https://mastra.ai/reference/core/addGateway.md`. Verify against the installed version before relying on an option.

## Contents

- Model ID formats
- The `model` field
- Fallback entries
- Provider options and precedence
- Embedding models
- Built-in gateways
- `AzureOpenAIGateway` options
- Custom gateways: `MastraModelGateway`
- `ProviderConfig`
- Mastra gateway accessors
- Related environment variables

---

## Model ID formats

| Format | Example | Meaning |
|---|---|---|
| `provider/model` | `'openai/gpt-6.1-sol'` | Direct provider |
| `gateway/provider/model` | `'openrouter/anthropic/claude-haiku-4.5'` | Gateway with upstream provider |
| `gateway/model` | `'custom/model-1'` | Gateway whose provider ID equals the gateway ID |
| `azure-openai/deployment` | `'azure-openai/my-gpt-5-4-deployment'` | Azure deployment name |

Types: `ModelRouterModelId` (language models) and `EmbeddingModelId` (embedding models), both from `@mastra/core/llm`.

---

## The `model` field

Accepted on `new Agent({ model })` and anywhere a model is configured. The docs show a function `({ requestContext }) => 'provider/model'` for dynamic selection, and functions for each fallback-entry field.

| Form | Fields | Notes |
|---|---|---|
| String | `'provider/model'` | Reads the provider env var automatically. |
| Config object | `id` | Router form of the model ID. |
| | `apiKey` | Overrides the env var. |
| | `headers` | Extra request headers, for example `'OpenAI-Organization'`. |
| | `url` | Base URL of an OpenAI-compatible endpoint (ends in `/v1`). |
| | `api` | `'chat'` (default) or `'responses'` for `url` endpoints. |
| Fallback array | see below | Tried in order. |
| AI SDK model | `groq('gemma2-9b-it')` | Any AI SDK provider module. Also valid inside fallbacks and scorers. |

---

## Fallback entries

`model: [{ ... }, { ... }]`

| Field | Notes |
|---|---|
| `model` | Router string (or AI SDK model). |
| `maxRetries` | Retries for this entry before moving on. |
| `modelSettings` | Per-entry settings such as `temperature`. |
| `providerOptions` | Per-entry provider options. |
| `headers` | Per-entry headers. |

Each field also accepts a function of `requestContext`. Failover triggers on 500 errors, rate limits, and timeouts.

---

## Provider options and precedence

Where to set `providerOptions`:

| Level | Shape |
|---|---|
| Agent instructions | `instructions: { role: 'system', content, providerOptions }` |
| One message | `agent.generate([{ role: 'user', content, providerOptions }])` |
| One call | `agent.generate(msg, { providerOptions: { openai: {...} } })` |
| Fallback entry | `{ model, providerOptions }` |

Precedence:

- `modelSettings`, `providerOptions`: fallback entry over call-time over agent `defaultOptions`. `modelSettings` shallow-merges by key; `providerOptions` deep-merges.
- `headers`: call-time `modelSettings.headers` over per-entry `headers` over router-model headers.

Common keys (full lists on each provider page):

| Namespace | Example keys |
|---|---|
| `openai` | `reasoningEffort`, `parallelToolCalls`, `previousResponseId`, `promptCacheKey`, `maxToolCalls` |
| `anthropic` | `cacheControl: { type: 'ephemeral', ttl?: '5m' \| '1h' }`, `thinking` |
| `google` | `thinkingConfig: { thinkingBudget }` |
| `azure` | `transport: 'websocket'`, `store`, `websocket: { closeOnFinish }` (Responses API only) |
| `openai-compatible` | Read by custom `url` endpoints on the chat API |

---

## Embedding models

Import: `import { ModelRouterEmbeddingModel } from '@mastra/core/llm'`

| Constructor form | Example |
|---|---|
| Router string | `new ModelRouterEmbeddingModel('openai/text-embedding-3-small')` |
| Gateway string | `new ModelRouterEmbeddingModel('mastra/openai/text-embedding-3-small')` |
| Custom endpoint | `new ModelRouterEmbeddingModel({ providerId, modelId, url, apiKey })` |

| Model | Dimensions | Max tokens | Env var |
|---|---|---|---|
| `openai/text-embedding-3-small` | 1536 | 8191 | `OPENAI_API_KEY` |
| `openai/text-embedding-3-large` | 3072 | 8191 | `OPENAI_API_KEY` |
| `openai/text-embedding-ada-002` | 1536 | 8191 | `OPENAI_API_KEY` |
| `google/gemini-embedding-001` | 768 | 2048 | `GOOGLE_API_KEY` (fallback `GOOGLE_GENERATIVE_AI_API_KEY`) |

- Use with AI SDK `embedMany({ model, values })` from `ai`, or as `new Memory({ embedder })`.
- `embedder` accepts an `EmbeddingModelId` string, an AI SDK v1 `EmbeddingModel`, or an AI SDK v2 `EmbeddingModelV2`.
- The constructor throws on an unknown provider (`Unknown provider: ...`) and on a missing key (`API key not found for provider openai. Set OPENAI_API_KEY ...`).
- VoyageAI ships separately as `@mastra/voyageai` (`voyage`, `voyageEmbedding({ model, inputType, outputDimension, baseUrl })`, env `VOYAGE_API_KEY`). Default dimension 1024.

---

## Built-in gateways

| Gateway | Prefix | Env vars |
|---|---|---|
| Azure OpenAI | `azure-openai/` | `AZURE_API_KEY` (+ management vars for discovery) |
| Mastra Gateway | `mastra/` | `MASTRA_GATEWAY_API_KEY` |
| Merge Gateway | `merge-gateway/` | `MERGE_GATEWAY_API_KEY` |
| Neon | `neon/` | `NEON_AI_GATEWAY_BASE_URL`, `NEON_AI_GATEWAY_TOKEN` |
| Netlify | `netlify/` | `NETLIFY_TOKEN`, `NETLIFY_SITE_ID` |
| OpenRouter | `openrouter/` | `OPENROUTER_API_KEY` |
| Vercel | `vercel/` | `AI_GATEWAY_API_KEY` |

OpenRouter and similar gateways use the OpenAI-compatible `/chat/completions` endpoint, so some provider-specific features may be missing. The Mastra Gateway adds observational memory when you pass `memory: { thread, resource }` on calls.

---

## `AzureOpenAIGateway` options

Import: `import { AzureOpenAIGateway } from '@mastra/core/llm'`. Register as `new Mastra({ gateways: { 'azure-openai': new AzureOpenAIGateway({...}) } })`.

| Option | Required | Notes |
|---|---|---|
| `resourceName` | Yes | Azure OpenAI resource name. |
| `apiKey` | Yes* | From "Keys and Endpoint". |
| `authentication` | No | `{ type: 'entraId', credential, scope? }`. Use with `DefaultAzureCredential` from `@azure/identity`. |
| `deployments` | No | Static deployment names (enables autocomplete). |
| `management` | No | `{ tenantId, clientId, clientSecret, subscriptionId, resourceGroup }` for dynamic discovery. |
| `apiVersion` | No | Default `2024-04-01-preview`, or `v1` with the Responses API or `useDeploymentBasedUrls: false`. |
| `useResponsesAPI` | No | Default `false`. Required for WebSocket transport. |
| `useDeploymentBasedUrls` | No | Default `true` (or `false` with `useResponsesAPI`). Do not combine `true` with `useResponsesAPI: true`. |

\* Provide either `apiKey` or `authentication.type: 'entraId'`.

---

## Custom gateways: `MastraModelGateway`

Import: `import { MastraModelGateway, type ProviderConfig, type GatewayLanguageModel } from '@mastra/core/llm'`. Implement `MastraModelGatewayInterface` instead for a plain-object gateway.

| Member | Signature | Notes |
|---|---|---|
| `id` | `readonly string` | Required. Becomes the model-string prefix. |
| `name` | `readonly string` | Required. Display name. |
| `fetchProviders()` | `Promise<Record<string, ProviderConfig>>` | Required. Called on registration and about hourly. |
| `buildUrl(modelId, envVars?)` | `string \| undefined \| Promise<...>` | Required. Resolve `${PLACEHOLDERS}` here. |
| `getApiKey(modelId)` | `Promise<string>` | Required. |
| `resolveAuth(request)` | `GatewayAuthResult \| undefined` | Optional. Runs before `getApiKey()`. Result may hold `apiKey`, `bearerToken`, `headers`, `source`. |
| `resolveLanguageModel({ modelId, providerId, apiKey, headers?, transport?, responsesWebSocket? })` | `GatewayLanguageModel` | Required. Return an AI SDK v5, v6, or v7 language model. |
| `getId()` | `string` | Deprecated. Use `id`. |

The docs build the model with `createOpenAICompatible` from the OpenAI-compatible AI SDK provider. The custom gateways guide imports it from `@ai-sdk/openai-compatible-v5`, the class reference from `@ai-sdk/openai-compatible`. Use whichever package the installed docs name.

---

## `ProviderConfig`

| Field | Type | Notes |
|---|---|---|
| `name` | `string` | Display name. |
| `models` | `string[]` | Available model IDs. |
| `apiKeyEnvVar` | `string \| string[]` | Env var(s) for the key. |
| `gateway` | `string` | Gateway ID. |
| `url` | `string` | Optional base URL. |
| `apiKeyHeader` | `string` | Optional custom auth header. |
| `docUrl` | `string` | Optional docs link. |
| `pricing` | `Record<string, ModelPricing>` | Optional USD per 1M tokens: `input`, `output`, `cache_read`, `cache_write`, `reasoning`, `input_audio`, `output_audio`, optional `tiers`. Used for cost metrics when models.dev has no price. |

---

## Mastra gateway accessors

| Method | Notes |
|---|---|
| `new Mastra({ gateways: { key: gateway } })` | Register at construction. |
| `mastra.addGateway(gateway, key?)` | Register later. Key defaults to the gateway ID. Skipped if the key exists. Triggers type generation when `MASTRA_DEV=true`. |
| `mastra.getGateway(key)` | Lookup by registration key. |
| `mastra.getGatewayById(id)` | Lookup by gateway `id`. Returns `undefined` if missing. |
| `mastra.listGateways()` | `Record<string, MastraModelGateway>` keyed by registration key. |

---

## Related environment variables

| Variable | Effect |
|---|---|
| `MASTRA_AUTO_REFRESH_PROVIDERS=false` | Stops the hourly local model-list refresh in development (off by default in production). |
| `MASTRA_DEV=true` | Generates TypeScript types for custom gateways into `~/.cache/mastra/`. |
| `MASTRA_AUTO_REFRESH_PRICING=true` | Loads gateway pricing at startup. |
| `MASTRA_OFFLINE=true` | Skips loading gateway providers. |
| `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` | Redirect built-in provider calls through a proxy. |
