---
name: mastra-framework-integration
description: "Add Mastra agents to an existing web, server, or desktop app: Next.js, React with Vite, Astro, SvelteKit, Nuxt, Angular, Electron, Express, Hono, NestJS, and TanStack Start. Covers the three integration shapes (call the agent in your own route, mount the Mastra API with a server adapter, or run a separate Mastra server and call it from the frontend), mastra init, chat routes, history loading, CORS, CSP, and bundler fixes. Use this skill whenever the user wants to put a Mastra agent into a specific framework, asks where the src/mastra folder goes, how to stream chat into their app, or how to expose /api/agents from their app. Triggers on Next.js App Router route.ts, @mastra/next, createNextRouteHandler, @mastra/tanstack-start, createStartRouteHandler, @mastra/express, @mastra/hono, @mastra/nestjs, MastraModule, SvelteKit +server.ts, Nuxt defineEventHandler, Astro APIRoute, Angular Chat, Electron renderer, Vite React, mastra init, handleChatStream in a framework route."
license: Apache-2.0
metadata:
  category: server-and-frontend
  catalog_summary: "Add Mastra to Next.js, Vite, Astro, SvelteKit, Nuxt, Angular, Electron, Express, Hono, NestJS, TanStack Start"
  display_order: 3
  docs: https://mastra.ai/integrations/frameworks/next-js
---

# Mastra Framework Integration

Wire Mastra into an existing application framework so its routes and UI can call agents, with the least moving parts for that framework.

---

## When to use

- Adding Mastra to an existing Next.js, Vite + React, Astro, SvelteKit, Nuxt, Angular, or Electron app
- Exposing Mastra's HTTP API from an Express, Hono, NestJS, Next.js, or TanStack Start app
- Deciding whether Mastra should run inside the app or as a separate server
- Fixing framework-specific build errors (ESM imports, top-level await, browser build pulling in server code, native modules)
- Hydrating chat history from memory on page load

## When NOT to use

- Starting a brand new standalone Mastra project (use `mastra-project-setup`)
- Server options, custom routes, middleware, adapter internals (use `mastra-server`)
- Chat UI components, `useChat()` details, custom tool rendering (use `mastra-agentic-ui`)
- Calling a remote Mastra server with `MastraClient` (use `mastra-client-sdk`)
- Securing the routes (use `mastra-auth`)
- Hosting the result on Vercel, Netlify, Cloudflare, or containers (use `mastra-deployment`)

---

## Required inputs

- The framework, its version, and its router style (for example Next.js App Router, SvelteKit, Nuxt server routes)
- Whether the framework has a server runtime (SSR or API routes) or is browser-only
- Package manager and module system (`"type": "module"` or CommonJS)
- What the UI needs: a chat page, a single API call, or the full Mastra API
- The model provider key to configure

---

## The framework: three integration shapes

| Shape | How it works | Frameworks in the docs |
|---|---|---|
| A. In-app route | Import `mastra` into a server route and call `handleChatStream()` or the agent directly | Next.js, Astro, SvelteKit, Nuxt |
| B. Server adapter | Mount all Mastra routes (`/api/agents/...`) inside the app | Express, Hono, NestJS, Next.js (`@mastra/next`), TanStack Start |
| C. Separate Mastra server | Run `mastra dev` on port 4111, add `chatRoute()` to `apiRoutes`, call it from the browser | Vite + React, Angular, Electron |

Every guide starts the same way: run `npx mastra@latest init` in the project root. It creates `src/mastra/` with `index.ts`, `agents/weather-agent.ts`, and `tools/weather-tool.ts`, and asks for a provider key.

Shape A, Next.js App Router:

```typescript
// src/app/api/chat/route.ts
import { handleChatStream } from '@mastra/ai-sdk'
import { createUIMessageStreamResponse } from 'ai'
import { mastra } from '@/mastra'

export async function POST(req: Request) {
  const params = await req.json()
  const stream = await handleChatStream({
    mastra,
    agentId: 'weather-agent',
    version: 'v7',
    params,
  })
  return createUIMessageStreamResponse({ stream })
}
```

Shape B, Express:

```typescript
import express from 'express'
import { MastraServer } from '@mastra/express'
import { mastra } from './mastra'

const app = express()
app.use(express.json())
const server = new MastraServer({ app, mastra })
await server.init()
app.listen(3000)
```

Shape C, Mastra config:

```typescript
import { Mastra } from '@mastra/core/mastra'
import { chatRoute } from '@mastra/ai-sdk'

export const mastra = new Mastra({
  server: {
    apiRoutes: [chatRoute({ path: '/chat/:agentId' })],
  },
})
```

The browser then points `DefaultChatTransport` at `http://localhost:4111/chat/weather-agent`.

### Picking a shape

- The app has a Node server and you only need chat: shape A.
- The app is a backend (Express, Hono, NestJS) or other services need the whole API: shape B.
- The app is browser-only (Vite SPA, Angular CSR, Electron renderer): shape C.
- You need Studio, file-based agents, or independent scaling: shape C.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read the embedded docs in `node_modules/@mastra/ai-sdk/dist/docs/` and the adapter package. Otherwise fetch the framework page as Markdown, for example `https://mastra.ai/integrations/frameworks/next-js.md`. Trust these over memory.
2. **Pick the shape** with the table above.
3. **Initialize Mastra.** Run `npx mastra@latest init` and enter the provider key. Check the generated `src/mastra/index.ts`.
4. **Fix the module system.** ESM projects with `nodenext` need `.js` on relative imports. CommonJS projects can't use top-level `await` in `src/mastra/index.ts`.
5. **Install packages.** Shape A or C chat: `@mastra/ai-sdk`, `ai`, and the UI binding (`@ai-sdk/react`, `@ai-sdk/svelte`, `@ai-sdk/vue`, `@ai-sdk/angular`). Shape B: the adapter package.
6. **Add the server piece.** In-app route, adapter mount, or `chatRoute()` in `apiRoutes`.
7. **Keep server code out of the browser.** Angular: exclude `src/mastra/**` in `tsconfig.app.json`. TanStack Start: exclude DuckDB and `execa` from Vite and Nitro.
8. **Allow cross-origin calls for shape C.** Add `server.cors` and, for Electron, add `http://localhost:4111` to the CSP `connect-src`.
9. **Add the UI** (see `mastra-agentic-ui`).
10. **Test.** `curl -X POST http://localhost:3000/api/agents/weather-agent/generate -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"Weather in Seoul?"}]}'` for adapters, or open the chat page.

---

## Deep dive: loading history in shape A

Add a `GET` handler next to the chat `POST` that reads memory and converts it for `useChat()`:

```typescript
import { toAISdkMessages } from '@mastra/ai-sdk/ui'
import { NextResponse } from 'next/server'
import { mastra } from '@/mastra'

const THREAD_ID = 'example-user-id'
const RESOURCE_ID = 'weather-chat'

export async function GET() {
  const memory = await mastra.getAgentById('weather-agent').getMemory()
  let response = null
  try {
    response = await memory?.recall({ threadId: THREAD_ID, resourceId: RESOURCE_ID })
  } catch {
    console.log('No previous messages found.')
  }
  return NextResponse.json(toAISdkMessages(response?.messages || [], { version: 'v7' }))
}
```

In the `POST` handler, force the same `memory.thread` and `memory.resource` into `params`. Replace the constants with the signed-in user's IDs in real apps.

---

## Failure patterns

- **Studio and the app see different data.** `next dev` and `mastra dev` resolve a relative SQLite path from different directories. Use an absolute `file:` URL in storage.
- **NestJS ESM build fails on imports.** Add `.js` to every relative import in the generated files.
- **NestJS CommonJS build fails on `await`.** Remove the top-level `await` (the `DuckDBStore` observability domain) from `src/mastra/index.ts`.
- **NestJS unrelated routes 404.** `MastraModule` is a catch-all. Import it last or give it its own prefix.
- **Angular build errors on `process.env`.** `src/mastra/**` is compiled into the browser build. Exclude it in `tsconfig.app.json`.
- **TanStack Start dev crashes on a `.node` file.** Add `optimizeDeps.exclude: ['@mastra/duckdb', 'execa']` and Nitro external `/^@duckdb\//`.
- **Electron or Vite chat fails with a CORS or CSP error.** Add `server.cors` to the Mastra config and `connect-src http://localhost:4111` to the renderer CSP.
- **Adapter prefix mismatch.** `@mastra/next` and `@mastra/tanstack-start` need `prefix` equal to the mount path (for example `/api/mastra`).
- **AI SDK message type errors.** `handleChatStream()`, `chatRoute()`, and converters default to the v5 contract. Pass `version` to match the installed `ai` package.
- **`ai-elements` TypeScript errors.** The registry ships Radix UI components only. Use a Radix style in `components.json`.
- **Hard-coded thread IDs in production.** Every user shares one conversation. Derive `thread` and `resource` from auth.

---

## Output format

A finished integration contains:

- `src/mastra/` (agents, tools, `index.ts`) compiling under the app's module system
- The server piece: a chat route file, an adapter mount, or `chatRoute()` in `apiRoutes`
- Build config changes (tsconfig excludes, Vite or Nitro settings, CSP, CORS) with a comment on why
- Provider key and `MASTRA_API_URL` (shape C) in `.env.example`
- A run note: which commands start the app (and the Mastra server for shape C), and a working `curl` or chat test

---

## Reference files

- [`references/frameworks.md`](references/frameworks.md) - One row per framework: shape, packages, files to create, and gotchas.
- [`references/api.md`](references/api.md) - Signatures for the helpers the guides use: `handleChatStream`, `chatRoute`, `toAISdkMessages`, adapter mount functions.
- [`references/examples.md`](references/examples.md) - Complete SvelteKit, Nuxt, Angular, and NestJS integrations.
- [`references/checklist.md`](references/checklist.md) - Integration checklist.

**Live docs**

- https://mastra.ai/integrations/frameworks/next-js
- https://mastra.ai/integrations/frameworks/vite-react
- https://mastra.ai/integrations/frameworks/astro
- https://mastra.ai/integrations/frameworks/sveltekit
- https://mastra.ai/integrations/frameworks/nuxt
- https://mastra.ai/integrations/frameworks/angular
- https://mastra.ai/integrations/frameworks/electron
- https://mastra.ai/integrations/frameworks/express
- https://mastra.ai/integrations/frameworks/hono
- https://mastra.ai/integrations/frameworks/nestjs
- https://mastra.ai/integrations/frameworks/tanstack-start
