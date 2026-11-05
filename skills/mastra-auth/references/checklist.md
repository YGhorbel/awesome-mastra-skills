# Auth checklist

Run this before calling an auth setup done. Adapted from the identity guide's production checklist.

## Authentication

- [ ] `server.auth` configured for every deployment that is not purely local
- [ ] Production uses JWT or an identity provider, not SimpleAuth user tokens
- [ ] Provider env vars set and documented in `.env.example`; secrets never committed
- [ ] Anonymous requests to `/api/agents`, `/api/workflows`, `/api/memory`, and custom routes return 401
- [ ] Invalid tokens return 401 and do not populate request context
- [ ] Custom `apiPrefix` reflected in `protected` and `public` patterns
- [ ] Studio protected (`server.auth` or `studio.auth`) if deployed

## Identity and isolation

- [ ] `mapUserToResourceId` returns a stable, collision-free, non-empty string (for example `${orgId}:${userId}`)
- [ ] A second user gets 403 on the first user's thread
- [ ] Tools and routes read the user from `requestContext`, never from tool input or request bodies
- [ ] Outbound credentials resolved from trusted identity and kept out of tool results and prompts

## Public surface

- [ ] Every `requiresAuth: false` route listed with its reason
- [ ] Public webhooks verify signatures before trusting the body
- [ ] OpenAPI and Swagger endpoints public only on purpose

## Clients

- [ ] Clients send `Authorization: Bearer <token>` or use `credentials: 'include'` with a credentialed CORS origin
- [ ] Token refresh handled in the frontend (provider SDK) before calls

## Authorization

- [ ] Roles mapped with RBAC or checked in `authorizeUser` where needed
- [ ] FGA `resourceMapping` and `permissionMapping` cover agents, workflows, tools, and threads in use
- [ ] `requireForProtectedRoutes` or route-level `fga` metadata on custom resource routes
- [ ] Enterprise Edition license in place for RBAC or FGA in production
- [ ] Known users without permission get 403

## Workers

- [ ] Split worker deployments have `server.auth` and `MASTRA_WORKER_AUTH_TOKEN`
- [ ] Worker traffic uses HTTPS and is kept off the public internet
