# Model examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models` and its provider pages. Run `scripts/provider-registry.mjs` before copying an ID into a project on another version.

## Contents

1. Dynamic model per request
2. Azure OpenAI through the built-in gateway
3. Custom private gateway
4. Local model plus local embeddings

---

## 1. Dynamic model per request

Pick the model from request context. Models are plain strings, so any logic can build them.

```typescript
// src/mastra/agents/assistant.ts
import { Agent } from '@mastra/core/agent'

export const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'You are a helpful assistant.',
  model: ({ requestContext }) =>
    requestContext.get('tier') === 'pro' ? 'anthropic/claude-opus-5-5' : 'openai/gpt-6-luna',
})
```

```typescript
import { RequestContext } from '@mastra/core/request-context'
import { mastra } from './src/mastra/index.ts'

const requestContext = new RequestContext()
requestContext.set('tier', 'pro')

const { text } = await mastra.getAgentById('assistant').generate('Summarize our Q3 plan.', {
  requestContext,
})
```

`.env.example`:

```bash
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

---

## 2. Azure OpenAI through the built-in gateway

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { AzureOpenAIGateway } from '@mastra/core/llm'
import { azureAgent } from './agents/azure-agent'

export const mastra = new Mastra({
  gateways: {
    'azure-openai': new AzureOpenAIGateway({
      resourceName: 'my-openai-resource',
      apiKey: process.env.AZURE_API_KEY!,
      deployments: ['gpt-5-4-prod', 'gpt-5-4-mini-dev'],
    }),
  },
  agents: { azureAgent },
})
```

```typescript
// src/mastra/agents/azure-agent.ts
import { Agent } from '@mastra/core/agent'

export const azureAgent = new Agent({
  id: 'azure-agent',
  name: 'Azure Agent',
  instructions: 'You are a helpful assistant',
  model: 'azure-openai/gpt-5-4-prod', // the deployment name, not a model name
})
```

For keyless auth, replace `apiKey` with `authentication: { type: 'entraId', credential: new DefaultAzureCredential() }` and install `@azure/identity`.

---

## 3. Custom private gateway

A plain-object gateway for an internal OpenAI-compatible service. Install the OpenAI-compatible AI SDK provider the docs name.

```typescript
// src/mastra/gateways/private-gateway.ts
import { type MastraModelGatewayInterface, type ProviderConfig } from '@mastra/core/llm'
import { createOpenAICompatible } from '@ai-sdk/openai-compatible-v5'

export const privateGateway: MastraModelGatewayInterface = {
  id: 'private',
  name: 'My Private Gateway',
  async fetchProviders(): Promise<Record<string, ProviderConfig>> {
    return {
      'my-provider': {
        name: 'My Provider',
        models: ['model-1'],
        apiKeyEnvVar: 'MY_API_KEY',
        gateway: 'private',
        url: 'https://api.myprovider.com/v1',
        pricing: { 'model-1': { input: 0.5, output: 1.5, cache_read: 0.05 } },
      },
    }
  },
  buildUrl() {
    return 'https://api.myprovider.com/v1'
  },
  async getApiKey() {
    return process.env.MY_API_KEY ?? ''
  },
  async resolveLanguageModel({ modelId, providerId, apiKey }) {
    return createOpenAICompatible({
      name: providerId,
      apiKey,
      baseURL: 'https://api.myprovider.com/v1',
    }).chatModel(modelId)
  },
}
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { privateGateway } from './gateways/private-gateway'

const internalAgent = new Agent({
  id: 'internal-agent',
  name: 'Internal Agent',
  instructions: 'You are a helpful assistant',
  model: 'private/my-provider/model-1',
})

export const mastra = new Mastra({
  gateways: { privateGateway },
  agents: { internalAgent },
})
```

Run `mastra dev` (or set `MASTRA_DEV=true`) so Mastra generates types for `private/...` IDs. Until then, type the ID with a union of `ModelRouterModelId` and your custom IDs.

---

## 4. Local model plus local embeddings

LMStudio serves chat on `http://localhost:1234/v1`. Ollama serves embeddings on `http://localhost:11434/v1`.

```typescript
import { Agent } from '@mastra/core/agent'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { Memory } from '@mastra/memory'

const embedder = new ModelRouterEmbeddingModel({
  providerId: 'ollama',
  modelId: 'nomic-embed-text',
  url: 'http://localhost:11434/v1',
  apiKey: 'not-needed',
})

export const localAgent = new Agent({
  id: 'local-agent',
  name: 'Local Agent',
  instructions: 'You are a helpful assistant',
  model: {
    id: 'lmstudio/qwen/qwen3-30b-a3b-2507',
    url: 'http://localhost:1234/v1',
  },
  memory: new Memory({ embedder }),
})
```

Create any vector index with the embedder's real output dimension. Semantic recall setup lives in `mastra-semantic-recall`.
