---
name: mastra-models
description: "Pick, verify, and configure language and embedding models in Mastra through the model router: provider/model strings, gateways such as OpenRouter, Vercel, Netlify, Azure OpenAI, and the Mastra Gateway, custom gateways, provider API key env vars, fallback chains, provider options, custom headers, local OpenAI-compatible endpoints, and embedding models. Use this skill whenever the user chooses or changes a model, gets a missing API key or unknown provider error, wants a cheaper or faster model, needs failover between providers, or asks which env var a provider needs. Triggers on model router, provider/model, openai/, anthropic/, google/, openrouter/, ModelRouterEmbeddingModel, @mastra/core/llm, MastraModelGateway, addGateway, AzureOpenAIGateway, providerOptions, reasoningEffort, cacheControl, model fallback, OPENAI_API_KEY, ANTHROPIC_API_KEY, LMStudio, Ollama, embedder. Also triggers whenever a model ID must be written into code, because model IDs change often and must be verified."
license: Apache-2.0
metadata:
  category: models
  catalog_summary: "Model router strings, providers and env vars, gateways, custom gateways, fallbacks, provider options, embeddings"
  display_order: 1
  docs: https://mastra.ai/models
---

# Mastra Models

Choose a model, write its ID in the router format, make sure its API key is set, and add fallbacks or provider options when needed. Mastra's model router reaches thousands of models from hundreds of providers with one string format and no extra provider packages.

---

## When to use

- Writing a `model:` value on an agent, scorer, classifier, or structured output call
- Verifying that a provider prefix or model ID exists in the installed Mastra version
- Finding the environment variable a provider needs
- Routing through a gateway (OpenRouter, Vercel, Netlify, Neon, Merge, Azure OpenAI, Mastra Gateway)
- Building a custom gateway for a private or enterprise LLM deployment
- Adding a fallback chain across providers
- Setting provider options (`reasoningEffort`, `cacheControl`, `thinkingConfig`) or custom headers
- Pointing Mastra at a local or self-hosted OpenAI-compatible server (LMStudio, vLLM, Ollama)
- Choosing an embedding model for memory or RAG

## When NOT to use

- Writing the agent itself, its instructions, tools, or `generate()` calls (use `mastra-agents`)
- Semantic recall configuration and vector indexes for memory (use `mastra-semantic-recall`)
- Chunking, embedding pipelines, and retrieval (use `mastra-rag`)
- Choosing a vector database (use `mastra-vector-stores`)
- Voice models, speech-to-text, and text-to-speech (use `mastra-voice`)
- Model cost and token metrics in traces (use `mastra-observability`)
- Debugging a broken project setup or `.env` loading (use `mastra-project-setup` or `mastra-troubleshooting`)

---

## Required inputs

- The task the model serves (reasoning, fast chat, extraction, embeddings) and any budget or latency limit
- The provider or gateway the user already has credentials for
- Whether the deployment must stay inside a cloud or region (Azure, Bedrock-style gateway, self-hosted)
- Whether failover across providers is required
- For embeddings: the target vector dimension, which must match the vector index

If the user names a model from memory, verify it before writing it into code.

---

## The framework: one string, many providers

The router takes `provider/model` for direct providers and `gateway/provider/model` for gateways. It reads the matching env var (for example `ANTHROPIC_API_KEY`) and throws a runtime error naming the missing variable when it is absent.

```typescript
import { Agent } from '@mastra/core/agent'

export const agent = new Agent({
  id: 'my-agent',
  name: 'My Agent',
  instructions: 'You are a helpful assistant',
  model: 'anthropic/claude-sonnet-5-5', // provider/model
})
// Gateway form: 'openrouter/anthropic/claude-haiku-4.5', 'mastra/openai/gpt-5-mini'
// Azure form:   'azure-openai/<your-deployment-name>'
```

The `model` field accepts five shapes:

| Shape | Example | Use for |
|---|---|---|
| Router string | `'openai/gpt-6.1-sol'` | Default choice |
| Config object | `{ id, apiKey?, headers?, url?, api? }` | Custom headers, explicit key, OpenAI-compatible URL |
| Fallback array | `[{ model, maxRetries, modelSettings?, providerOptions?, headers? }]` | Failover across providers |
| Function | `({ requestContext }) => string` | Per-tenant or per-tier choice |
| AI SDK model | `groq('gemma2-9b-it')` | When you must use an `@ai-sdk/*` provider module directly |

Embeddings use the same strings through `ModelRouterEmbeddingModel` from `@mastra/core/llm`:

```typescript
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'

const embedder = new ModelRouterEmbeddingModel('openai/text-embedding-3-small') // 1536 dims
```

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and run the registry script (step 2). Otherwise fetch `https://mastra.ai/models.md` and the provider page, for example `https://mastra.ai/models/providers/openai.md`. Trust these over memory. Model IDs in training data are often stale.
2. **Verify the model ID.** From the project root, run `node <skill-dir>/scripts/provider-registry.mjs --list` to list provider prefixes, then `--provider <prefix>` to list that provider's models, newest first. The script reads `node_modules/@mastra/core/dist/provider-registry.json`, so it reflects the installed version. Without `node_modules`, use the provider page's model table.
3. **Pick the env var.** Look up the prefix in [`references/providers.md`](references/providers.md). Add the variable to `.env.example` and the real value to `.env`.
4. **Write the model value.** Use the router string. Switch to the config object only for headers, an explicit `apiKey`, or a custom `url`.
5. **Add resilience if asked.** Use a fallback array with a `maxRetries` per entry. Put the cheapest reliable model last.
6. **Tune with provider options.** Set `providerOptions` on the system message, a user message, the call options, or a fallback entry.
7. **Register custom gateways** on `new Mastra({ gateways })` or with `mastra.addGateway()`, then reference models as `<gateway-id>/<provider>/<model>`.
8. **Test** one call through Studio (`npx mastra dev`) or a short script, and confirm the response comes from the expected model.

---

## Deep dive: fallbacks and provider options

```typescript
import { Agent } from '@mastra/core/agent'

export const resilient = new Agent({
  id: 'tuned-resilient',
  name: 'Tuned Resilient Agent',
  instructions: 'You are a helpful assistant.',
  model: [
    {
      model: 'google/gemini-3.8-flash',
      maxRetries: 2,
      modelSettings: { temperature: 0.3 },
      providerOptions: { google: { thinkingConfig: { thinkingBudget: 0 } } },
    },
    {
      model: 'openai/gpt-6-luna',
      maxRetries: 2,
      modelSettings: { temperature: 0.7 },
      providerOptions: { openai: { reasoningEffort: 'low' } },
    },
  ],
})
```

- Mastra moves to the next entry on a 500 error, rate limit, or timeout, after that entry's retries are spent.
- Precedence for `modelSettings` and `providerOptions`: fallback entry, then call-time options, then agent `defaultOptions`. `modelSettings` shallow-merges. `providerOptions` deep-merges.
- Headers: call-time `modelSettings.headers` beat per-entry `headers`, which beat headers from the router model.
- Options are namespaced by provider key: `openai`, `anthropic`, `google`, `azure`. The provider page lists every option (for example Anthropic `cacheControl` and `thinking`).

## Deep dive: local and custom endpoints

Point at any OpenAI-compatible server with `url` (the base URL ending in `/v1`, never the chat endpoint):

```typescript
model: {
  id: 'lmstudio/qwen/qwen3-30b-a3b-2507',
  url: 'http://localhost:1234/v1',
}
```

- Use `provider/model` in `id` when the server expects a bare model name. Use `gateway/provider/model` when the upstream namespace includes the provider.
- Add `api: 'responses'` when the endpoint exposes the OpenAI Responses API. The default is `'chat'`. Responses reads `providerOptions.openai`; chat reads `providerOptions['openai-compatible']`.
- To proxy a built-in provider without changing code, set `OPENAI_BASE_URL` or `ANTHROPIC_BASE_URL` next to the API key.

---

## Failure patterns

- **Colon form `openai:gpt-...`.** The router uses a slash. Write `'openai/gpt-6.1-sol'`.
- **Model ID from memory.** It may not exist in the installed version. Run the registry script or read the provider page first.
- **Installing `@ai-sdk/openai` and importing `openai(...)` by default.** Not needed. The router string needs no provider package. Use AI SDK modules only when the router lacks the provider.
- **Missing or misnamed env var.** The error names the expected variable. Check the table: Google uses `GOOGLE_API_KEY` (falls back to `GOOGLE_GENERATIVE_AI_API_KEY`), Together uses `TOGETHER_API_KEY`, Vercel uses `AI_GATEWAY_API_KEY`.
- **Gateway string without the provider segment.** OpenRouter, Vercel, Netlify, and Mastra Gateway need `gateway/provider/model`.
- **Azure model string set to a model name.** Azure uses your deployment name: `'azure-openai/my-gpt-5-4-deployment'`, plus an `AzureOpenAIGateway` registered on `Mastra`.
- **`url` set to `/v1/chat/completions`.** Use the base URL (`http://localhost:1234/v1`).
- **Embedding dimension mismatch.** `text-embedding-3-small` is 1536 dimensions, `text-embedding-3-large` is 3072. Create the vector index with the same dimension.
- **Fallback chain with identical providers.** An outage takes out every entry. Mix providers.
- **Custom gateway models fail type checks.** Run with `MASTRA_DEV=true` to generate types, or widen with a `ModelRouterModelId | CustomModelId` union.

---

## Output format

A finished model change contains:

- The `model:` value as a verified router string, fallback array, or config object
- The provider env var in `.env.example` (never commit `.env`)
- Any gateway registered on `new Mastra({ gateways })`
- For embeddings: the embedder and the matching vector dimension
- Evidence: the registry script output or provider page used to verify the ID, and one successful call

---

## Reference files

- [`references/api.md`](references/api.md) - Model config shapes, fallback fields, embeddings, gateway classes, `MastraModelGateway` methods, `ProviderConfig`, Mastra gateway accessors, related env vars.
- [`references/providers.md`](references/providers.md) - Every provider and gateway prefix with its environment variables.
- [`references/examples.md`](references/examples.md) - Dynamic model per tier, Azure OpenAI gateway, custom private gateway, local model with embeddings.
- [`references/checklist.md`](references/checklist.md) - Model selection and production checklist.
- `scripts/provider-registry.mjs` - Lists installed providers (`--list`) and a provider's models (`--provider <prefix>`). Adapted from github.com/mastra-ai/skills (Apache-2.0).

**Live docs**

- https://mastra.ai/models
- https://mastra.ai/models/providers
- https://mastra.ai/models/gateways
- https://mastra.ai/models/gateways/custom-gateways
- https://mastra.ai/models/embeddings
- https://mastra.ai/models/environment-variables
- https://mastra.ai/reference/core/addGateway
- https://mastra.ai/reference/core/mastra-model-gateway
