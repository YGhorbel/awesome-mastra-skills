# Framework integration examples

All examples follow the framework guides under `https://mastra.ai/integrations/frameworks/`. Each assumes `npx mastra@latest init` already created `src/mastra/` with a `weather-agent`.

## Contents

1. SvelteKit in-app chat route with history
2. Nuxt server route
3. Angular against a separate Mastra server
4. NestJS module with an injected service

---

## 1. SvelteKit in-app chat route with history

`npm install @mastra/ai-sdk@latest @ai-sdk/svelte ai`

```typescript
// src/routes/api/chat/+server.ts
import type { RequestHandler } from './$types'
import { handleChatStream } from '@mastra/ai-sdk'
import { toAISdkV5Messages } from '@mastra/ai-sdk/ui'
import { createUIMessageStreamResponse } from 'ai'
import { mastra } from '../../../mastra'

const THREAD_ID = 'example-user-id'
const RESOURCE_ID = 'weather-chat'

export const POST: RequestHandler = async ({ request }) => {
  const params = await request.json()
  const stream = await handleChatStream({
    mastra,
    agentId: 'weather-agent',
    params: {
      ...params,
      memory: {
        ...params.memory,
        thread: THREAD_ID,
        resource: RESOURCE_ID,
      },
    },
  })
  return createUIMessageStreamResponse({ stream })
}

export const GET: RequestHandler = async () => {
  const memory = await mastra.getAgentById('weather-agent').getMemory()
  let response = null
  try {
    response = await memory?.recall({ threadId: THREAD_ID, resourceId: RESOURCE_ID })
  } catch {
    console.log('No previous messages found.')
  }
  return Response.json(toAISdkV5Messages(response?.messages || []))
}
```

```typescript
// src/routes/+page.ts
import type { UIDataTypes, UIMessage, UITools } from 'ai'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ fetch }) => {
  const response = await fetch('/api/chat')
  const initialMessages = (await response.json()) as UIMessage<unknown, UIDataTypes, UITools>[]
  return { initialMessages }
}
```

```svelte
<!-- src/routes/+page.svelte (minimal) -->
<script lang="ts">
  import { Chat } from '@ai-sdk/svelte';
  import { DefaultChatTransport } from 'ai';

  let input = $state('');
  const { data } = $props();
  let messages = $derived(data.initialMessages);

  const chat = new Chat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
    get messages() {
      return messages;
    }
  });

  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    chat.sendMessage({ text: input });
    input = '';
  }
</script>

{#each chat.messages as message, i (i)}
  {#each message.parts as part, j (j)}
    {#if part.type === 'text'}<p>{part.text}</p>{/if}
  {/each}
{/each}

<form onsubmit={handleSubmit}>
  <input bind:value={input} placeholder="City name" />
  <button type="submit">Send</button>
</form>
```

---

## 2. Nuxt server route

`npm install @mastra/ai-sdk@latest @ai-sdk/vue ai`

```typescript
// server/api/chat.ts
import { handleChatStream } from '@mastra/ai-sdk'
import { toAISdkV5Messages } from '@mastra/ai-sdk/ui'
import { createUIMessageStreamResponse } from 'ai'
import { mastra } from '../../src/mastra' // adjust to where mastra init created the folder

const THREAD_ID = 'example-user-id'
const RESOURCE_ID = 'weather-chat'

export default defineEventHandler(async event => {
  if (event.method === 'POST') {
    const params = await readBody(event)
    const stream = await handleChatStream({
      mastra,
      agentId: 'weather-agent',
      params: {
        ...params,
        memory: { ...params.memory, thread: THREAD_ID, resource: RESOURCE_ID },
      },
    })
    return createUIMessageStreamResponse({ stream })
  }

  if (event.method === 'GET') {
    const memory = await mastra.getAgentById('weather-agent').getMemory()
    let response = null
    try {
      response = await memory?.recall({ threadId: THREAD_ID, resourceId: RESOURCE_ID })
    } catch {
      console.log('No previous messages found.')
    }
    return toAISdkV5Messages(response?.messages || [])
  }
})
```

The UI in `app/app.vue` creates `new Chat({ transport: new DefaultChatTransport({ api: '/api/chat' }) })` from `@ai-sdk/vue`.

---

## 3. Angular against a separate Mastra server

`npm install @mastra/ai-sdk@latest @ai-sdk/angular ai`

```jsonc
// tsconfig.app.json
{
  "exclude": ["src/**/*.spec.ts", "src/mastra/**"]
}
```

```typescript
// src/mastra/index.ts (add to the existing config)
import { Mastra } from '@mastra/core/mastra'
import { chatRoute } from '@mastra/ai-sdk'

export const mastra = new Mastra({
  server: {
    apiRoutes: [
      chatRoute({
        path: '/chat/:agentId',
        version: 'v7',
      }),
    ],
  },
})
```

```typescript
// src/app/app.ts (trimmed)
import { JsonPipe } from '@angular/common'
import { Component, signal } from '@angular/core'
import { Chat } from '@ai-sdk/angular'
import { DefaultChatTransport } from 'ai'

@Component({
  selector: 'app-root',
  imports: [JsonPipe],
  template: `
    @for (message of chat.messages; track message.id) {
      @for (part of message.parts; track $index) {
        @if (part.type === 'text') {
          <p>{{ part.text }}</p>
        }
      }
    }
    <form (submit)="sendMessage($event)">
      <textarea #messageInput [value]="input()" (input)="input.set(messageInput.value)"></textarea>
      <button type="submit">Send</button>
    </form>
  `,
})
export class App {
  readonly chat = new Chat({
    transport: new DefaultChatTransport({
      api: 'http://localhost:4111/chat/weather-agent',
    }),
  })

  readonly input = signal('')

  sendMessage(event: Event) {
    event.preventDefault()
    this.chat.sendMessage({ text: this.input() })
    this.input.set('')
  }
}
```

Run `npx mastra dev` and `ng serve` in two terminals. The Angular dev server's origin must be allowed by the Mastra server's CORS settings (the default `origin` is `'*'`).

---

## 4. NestJS module with an injected service

`npm install @mastra/nestjs@latest`

```typescript
// src/app.module.ts
import { Module } from '@nestjs/common'
import { MastraModule } from '@mastra/nestjs'
import { mastra } from './mastra/index.js'

@Module({
  imports: [
    // Import last: MastraModule registers a catch-all controller
    MastraModule.register({ mastra }),
  ],
})
export class AppModule {}
```

```typescript
// src/memory.service.ts
import { Injectable, Inject } from '@nestjs/common'
import { MASTRA } from '@mastra/nestjs'
import type { Mastra } from '@mastra/core/mastra'

@Injectable()
export class MemoryService {
  constructor(@Inject(MASTRA) private readonly mastra: Mastra) {}

  getMemory() {
    return this.mastra.getMemory()
  }
}
```

```bash
npm run start
curl -X POST http://localhost:3000/api/agents/weather-agent/generate \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is the weather like in Seoul?"}]}'
```

In ESM projects, add `.js` to every relative import inside `src/mastra/`.
