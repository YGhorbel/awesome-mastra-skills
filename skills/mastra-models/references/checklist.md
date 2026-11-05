# Model checklist

Run this before calling a model change done.

## Selection

- [ ] Model ID verified with `scripts/provider-registry.mjs --provider <prefix>` or the provider page, not taken from memory
- [ ] String uses a slash (`provider/model` or `gateway/provider/model`), never a colon
- [ ] Context window, tool support, and price fit the task (see the provider page's model table)
- [ ] No `@ai-sdk/*` provider package installed unless the router cannot reach the provider

## Credentials

- [ ] Provider env var name taken from `references/providers.md`
- [ ] Variable listed in `.env.example`, real value only in `.env` or the deployment's secret store
- [ ] Gateways with several variables (Netlify, Neon, Azure discovery) have all of them set
- [ ] A test call succeeds without a missing-key error

## Resilience and tuning

- [ ] User-facing agents use a fallback array across at least two providers
- [ ] Each fallback entry has a `maxRetries`
- [ ] Provider options sit under the right namespace (`openai`, `anthropic`, `google`, `azure`)
- [ ] Per-entry `modelSettings` set where models in the chain need different temperatures

## Gateways and custom endpoints

- [ ] Custom and Azure gateways registered on `new Mastra({ gateways })` or with `addGateway()`
- [ ] Custom gateway `id` matches the prefix used in model strings
- [ ] `url` endpoints use the base URL ending in `/v1`
- [ ] `api: 'responses'` set only when the endpoint supports `/v1/responses`

## Embeddings

- [ ] Embedder created with `ModelRouterEmbeddingModel` or a supported package
- [ ] Vector index dimension equals the embedder's output dimension
- [ ] Changing the embedding model triggers a re-embed of stored vectors
