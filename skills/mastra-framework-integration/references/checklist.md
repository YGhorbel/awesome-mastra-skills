# Framework integration checklist

Run this before calling a framework integration done.

## Structure

- [ ] Integration shape chosen and noted: in-app route, server adapter, or separate Mastra server
- [ ] `src/mastra/` compiles under the app's module system (`.js` extensions for `nodenext` ESM, no top-level `await` in CommonJS)
- [ ] Server-only code excluded from browser builds (Angular `tsconfig.app.json`, Vite `optimizeDeps`, Nitro externals)
- [ ] Imports of the `mastra` instance point at the real folder location

## Server piece

- [ ] Chat route forces `memory.thread` and `memory.resource` from the signed-in user, not constants
- [ ] `version` passed to `handleChatStream()`, `chatRoute()`, and converters matches the installed `ai` major version
- [ ] History route handles a missing thread without throwing
- [ ] Adapter `prefix` matches the mount path (Next.js, TanStack Start)
- [ ] NestJS `MastraModule` imported last or under its own prefix
- [ ] Workers started after listen when schedules or scheduled workflows are used (adapters)

## Cross-origin (separate server)

- [ ] `server.cors.origin` restricted to the frontend origin in production
- [ ] Electron CSP `connect-src` lists the real server URL
- [ ] Frontend reads the server URL from env, not a hard-coded `localhost:4111`

## Verification

- [ ] Storage path absolute if Studio and the app share a SQLite file
- [ ] `curl` against `/api/agents/<id>/generate` (adapters) or the chat page returns a streamed answer
- [ ] Provider key and server URL documented in `.env.example`
- [ ] Routes protected before exposure (see `mastra-auth`)
