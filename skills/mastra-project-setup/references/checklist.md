# New project checklist

Run this before calling a Mastra project set up.

## Scaffold

- [ ] Standalone project created with `create-mastra` (flags, not prompts, when run by an agent) or the manual install
- [ ] Existing apps routed to `mastra-framework-integration` instead
- [ ] Node.js and package manager versions noted in the README

## Configuration

- [ ] `package.json` has `"type": "module"` and `dev` and `build` scripts
- [ ] `@mastra/core`, `zod@^4` in dependencies; `mastra`, `typescript`, `@types/node` in devDependencies
- [ ] `tsconfig.json` uses `"module": "ES2022"` and `"moduleResolution": "bundler"`
- [ ] No AI SDK provider packages installed for router models

## Structure

- [ ] Code lives under `src/mastra/` (`agents/`, `tools/`, `workflows/`, optional `scorers/`, `mcp/`, `public/`)
- [ ] `src/mastra/index.ts` exports exactly one `mastra` instance
- [ ] Every agent, workflow, tool, and scorer is registered on it
- [ ] Tools are built with `createTool()`, agents with `new Agent({ id, name, instructions, model })`

## Environment

- [ ] Provider keys in `.env`; names in `.env.example`
- [ ] `.gitignore` covers `.env`, `.mastra/`, `node_modules/`, and local DB files such as `mastra.db`
- [ ] Storage configured if memory, suspendable workflows, or traces must persist

## Verification

- [ ] `npm run dev` starts and Studio loads at `http://localhost:4111`
- [ ] One agent or workflow runs successfully in Studio, a script, or `mastra api`
- [ ] `npx tsc --noEmit` passes
- [ ] `npx mastra lint` passes
- [ ] `npm run build` produces `.mastra/output`
