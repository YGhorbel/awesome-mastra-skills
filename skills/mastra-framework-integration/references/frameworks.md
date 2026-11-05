# Framework setup table

Distilled from the pages under `https://mastra.ai/integrations/frameworks/`. Every guide assumes Node.js `v22.13.0` or later and a provider key, and starts with `npx mastra@latest init`, which creates `src/mastra/index.ts`, `src/mastra/agents/weather-agent.ts`, and `src/mastra/tools/weather-tool.ts`.

Shapes: **A** in-app route, **B** server adapter, **C** separate Mastra server on port 4111.

## Contents

- Summary table
- Per-framework details
- Doc inconsistencies to watch

---

## Summary table

| Framework | Shape | Install | Files to create or edit | Test URL |
|---|---|---|---|---|
| Next.js | A (chat), B (full API) | `@mastra/ai-sdk @ai-sdk/react ai`; `@mastra/next hono` for B | `src/app/api/chat/route.ts` (`POST` + `GET`), `src/app/chat/page.tsx`; B: `src/app/api/[...mastra]/route.ts` | `http://localhost:3000/chat` |
| Vite + React | C | `@mastra/ai-sdk @ai-sdk/react ai`, Tailwind, `ai-elements` | `chatRoute({ path: '/chat/:agentId' })` in `src/mastra/index.ts`; `src/App.tsx` with `useChat` | Vite dev URL plus `mastra dev` |
| Astro | A | `@mastra/ai-sdk @ai-sdk/react ai`; `output: 'server'` with `@astrojs/node` | API route exporting `POST: APIRoute` and `GET: APIRoute`; React chat component | Astro dev URL |
| SvelteKit | A | `@mastra/ai-sdk @ai-sdk/svelte ai` | `src/routes/api/chat/+server.ts`, `src/routes/+page.ts` (`load` fetches history), `src/routes/+page.svelte` with `Chat` | `http://localhost:5173` |
| Nuxt | A | `@mastra/ai-sdk @ai-sdk/vue ai` | `server/api/chat.ts` with `defineEventHandler` (branches on `event.method`), `app/app.vue` with `Chat` | Nuxt dev URL |
| Angular | C | `@mastra/ai-sdk @ai-sdk/angular ai` | `chatRoute({ path: '/chat/:agentId', version: 'v7' })`; `src/app/app.ts` with `Chat`; exclude `src/mastra/**` in `tsconfig.app.json` | Angular dev URL plus `mastra dev` |
| Electron | C | `@mastra/ai-sdk @ai-sdk/react ai` | `chatRoute` plus `server.cors`; CSP `connect-src http://localhost:4111` in `src/renderer/index.html`; `src/renderer/src/App.tsx` | App window plus `mastra dev` |
| Express | B | `@mastra/express` | `src/index.ts`: `express.json()`, `MastraServer`, `await server.init()` | `POST /api/agents/weather-agent/generate` on port 3000 |
| Hono | B | `@mastra/hono` | `src/index.ts`: typed `Hono`, `MastraServer`, `serve()` | Same, port 3000 |
| NestJS | B | `@mastra/nestjs` (Express platform) | `src/app.module.ts` with `MastraModule.register({ mastra })` | Same, port 3000 |
| TanStack Start | B | `@mastra/tanstack-start hono` | `src/routes/api/$.ts` with `createStartRouteHandler`; `vite.config.ts` excludes | Same, port 3000 |

---

## Per-framework details

### Next.js

- Scaffold: `npx create-next-app@latest my-nextjs-agent --yes --ts --eslint --tailwind --src-dir --app --turbopack --no-react-compiler --no-import-alias`.
- Chat route uses `handleChatStream({ mastra, agentId, version: 'v7', params })` and `createUIMessageStreamResponse`. History `GET` uses `toAISdkMessages(messages, { version: 'v7' })`.
- UI uses `useChat({ transport: new DefaultChatTransport({ api: '/api/chat' }) })` and AI Elements components.
- For Studio alongside Next.js, set storage to an absolute `file:` path.
- Full API: catch-all route exporting `GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD` from `createNextRouteHandler({ mastra })`. Use `prefix: '/api/mastra'` when mounted at `app/api/mastra/[...mastra]/route.ts`.

### Vite + React

- Scaffold: `npm create vite@latest mastra-react -- --template react-ts`. Add `@tailwindcss/vite` and an `@` path alias in `vite.config.ts` and both tsconfig files.
- Add `chatRoute({ path: '/chat/:agentId' })` to `server.apiRoutes`. Run `mastra dev` and the Vite dev server together.

### Astro

- Scaffold: `npm create astro@latest mastra-astro -- --add node --add react --add tailwind --install --skip-houston --template minimal --git`.
- `astro.config` sets `output: 'server'` and `adapter: node({ mode: 'standalone' })`.
- The route handlers use `handleChatStream` and `toAISdkV5Messages`. You can also opt in to SSR per file.

### SvelteKit

- Scaffold: `npx sv create mastra-svelte --template minimal --types ts --add tailwindcss="plugins:forms" --install npm`.
- `+server.ts` exports `POST` and `GET` typed `RequestHandler`. `+page.ts` loads history so `+page.svelte` can pass it to `new Chat({ transport, get messages() {...} })` from `@ai-sdk/svelte`.

### Nuxt

- Scaffold: `npm create nuxt@latest mastra-nuxt -- --template minimal --packageManager npm --gitInit --modules`.
- `server/api/chat.ts` reads the body with `readBody(event)` for `POST` and returns converted messages for `GET`.
- UI uses `Chat` from `@ai-sdk/vue` in `app/app.vue`.

### Angular

- Scaffold client-side only: `npm create @angular@latest mastra-angular -- --defaults --ssr=false`.
- Add `"src/mastra/**"` to `exclude` in `tsconfig.app.json`. The default `noPropertyAccessFromIndexSignature` otherwise fails on `process.env` in the server code.
- `Chat` from `@ai-sdk/angular` with `DefaultChatTransport({ api: 'http://localhost:4111/chat/weather-agent' })`. Older projects may use `app.component.ts` and `AppComponent`.

### Electron

- Scaffold: `npm create @quick-start/electron@latest electron-chat -- --template react-ts --skip`.
- CSP meta: `default-src 'self'; connect-src http://localhost:4111; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:`. Change for the production server URL.
- `server.cors` uses `origin: '*'` in the guide. Restrict it to the app's origin in production.

### Express and Hono

- Express: `express.json()` before `MastraServer`. Hono: `new Hono<{ Bindings: HonoBindings; Variables: HonoVariables }>()` and `serve({ fetch: app.fetch, port: 3000 })`.
- Routes are under `/api` by default. Add `mastra.startWorkers()` after listening if you use schedules or scheduled workflows.

### NestJS

- Scaffold: `npx @nestjs/cli new mastra-nest`. NestJS CLI v12 creates ESM projects.
- ESM: add `.js` to relative imports in generated files. CommonJS: remove the top-level `await` `DuckDBStore` observability domain (observability then uses the default LibSQL storage).
- Inject with `MastraService` (`getAgent`, `getWorkflow`, `getMastra`, `getOptions`, `isShuttingDown`) or `@Inject(MASTRA)`.

### TanStack Start

- `vite.config.ts`: `optimizeDeps: { exclude: ['@mastra/duckdb', 'execa'] }` and Nitro `rollupConfig.external: [/^@sentry\//, /^@duckdb\//]`.
- Splat route at `src/routes/api/$.ts`. Use `prefix: '/api/mastra'` when mounted at `src/routes/api/mastra/$.ts`.

---

## Doc inconsistencies to watch

- Next.js passes `version: 'v7'` and uses `toAISdkMessages(..., { version: 'v7' })`. Astro, SvelteKit, and Nuxt omit `version` and use `toAISdkV5Messages()`. Match the `version` to the installed `ai` major version.
- The Nuxt page says `mastra init` creates a `mastra` folder but imports from `../../src/mastra`. Check where the folder landed and fix the import.
