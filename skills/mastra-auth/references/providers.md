# Auth providers

Distilled from the pages under `https://mastra.ai/integrations/auth/` and `https://mastra.ai/reference/auth/`. Every provider plugs into `new Mastra({ server: { auth } })`. Most accept `name`, `authorizeUser`, `protected`, and `public` in addition to the options below.

## Contents

- Summary table
- Constructor shapes
- RBAC providers
- Client-side token handling

---

## Summary table

| Provider | Package | Class | Required config (env fallback) | Default `authorizeUser` | Studio login |
|---|---|---|---|---|---|
| Simple Auth | `@mastra/core` | `SimpleAuth` from `@mastra/core/server` | `tokens` map | Allows mapped users | Yes |
| JWT | `@mastra/auth` | `MastraJwtAuth` | `secret` (`JWT_AUTH_SECRET`) | Not documented | Yes |
| Auth0 | `@mastra/auth-auth0` | `MastraAuthAuth0` | `domain` (`AUTH0_DOMAIN`), `audience` (`AUTH0_AUDIENCE`) | Allows valid tokens | No |
| Better Auth | `@mastra/auth-better-auth` | `MastraAuthBetterAuth` | `auth` (a `betterAuth()` instance) or `secret` | Allows valid sessions | Yes |
| Clerk | `@mastra/auth-clerk` | `MastraAuthClerk` | `publishableKey` (`CLERK_PUBLISHABLE_KEY`), `secretKey` (`CLERK_SECRET_KEY`), `jwksUri` (`CLERK_JWKS_URI`) | Allows valid tokens, or org members when `organizationId`/`organizationSlug` set | No |
| Firebase | `@mastra/auth-firebase` | `MastraAuthFirebase` | `serviceAccount` (`FIREBASE_SERVICE_ACCOUNT`), `databaseId` (`FIRESTORE_DATABASE_ID` or `FIREBASE_DATABASE_ID`) | Requires a `user_access` document keyed by UID | No |
| Google | `@mastra/auth-google` | `MastraAuthGoogle` (+ `MastraRBACGoogle`) | `clientId` (`GOOGLE_CLIENT_ID`), `clientSecret` (`GOOGLE_CLIENT_SECRET`), `redirectUri` (`GOOGLE_REDIRECT_URI`), `allowedDomains` (`GOOGLE_ALLOWED_DOMAINS`) | Not documented (`allowedDomains` checks the verified `hd` claim) | Yes |
| Okta | `@mastra/auth-okta` | `MastraAuthOkta` (+ `MastraRBACOkta`) | `domain` (`OKTA_DOMAIN`), `clientId` (`OKTA_CLIENT_ID`), `clientSecret` (`OKTA_CLIENT_SECRET`), `redirectUri` (`OKTA_REDIRECT_URI`) | Not documented | Not listed |
| Supabase | `@mastra/auth-supabase` | `MastraAuthSupabase` | `url` (`SUPABASE_URL`), `anonKey` (`SUPABASE_ANON_KEY`) | Checks `isAdmin` in the `users` table | No |
| WorkOS | `@mastra/auth-workos` | `MastraAuthWorkos` (+ `MastraFGAWorkos`) | `apiKey` (`WORKOS_API_KEY`), `clientId` (`WORKOS_CLIENT_ID`) | Not documented | Yes |
| Neon Auth | `@mastra/auth-neon` | `MastraAuthNeon` (+ `MastraRBACNeon`) | `baseUrl` (`NEON_AUTH_BASE_URL`), `jwksUrl` (`NEON_AUTH_JWKS_URL`) | Not documented | Not listed |

"Studio login" follows the auth overview, which lists Simple Auth, JWT, WorkOS, Better Auth, and Google.

---

## Constructor shapes

```typescript
import { MastraAuthAuth0 } from '@mastra/auth-auth0'
new MastraAuthAuth0({ domain: process.env.AUTH0_DOMAIN, audience: process.env.AUTH0_AUDIENCE })
// or new MastraAuthAuth0() with env vars set
```

```typescript
import { betterAuth } from 'better-auth'
import { MastraAuthBetterAuth } from '@mastra/auth-better-auth'

const auth = betterAuth({
  database: { provider: 'postgresql', url: process.env.DATABASE_URL },
  emailAndPassword: { enabled: true },
  baseURL: process.env.BETTER_AUTH_URL,
  secret: process.env.BETTER_AUTH_SECRET, // at least 32 chars
})
new MastraAuthBetterAuth({ auth })
```

Better Auth extra options: `signUpEnabled` (default `true`, only for the instance the provider builds itself when you pass `secret` instead of `auth`).

```typescript
import { MastraAuthClerk } from '@mastra/auth-clerk'
new MastraAuthClerk({
  publishableKey: process.env.CLERK_PUBLISHABLE_KEY,
  secretKey: process.env.CLERK_SECRET_KEY,
  jwksUri: process.env.CLERK_JWKS_URI,
  organizationId: process.env.CLERK_ORGANIZATION_ID, // optional
})
```

```typescript
import { MastraAuthFirebase } from '@mastra/auth-firebase'
new MastraAuthFirebase() // reads FIREBASE_SERVICE_ACCOUNT and FIRESTORE_DATABASE_ID
```

```typescript
import { MastraAuthGoogle } from '@mastra/auth-google'
new MastraAuthGoogle({
  clientId: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  redirectUri: process.env.GOOGLE_REDIRECT_URI, // e.g. http://localhost:4111/api/auth/sso/callback
  allowedDomains: ['example.com'],
})
```

Google extras: `hostedDomain` (login hint only), `scopes` (default `openid profile email`). Session cookies use `GOOGLE_COOKIE_PASSWORD` (32+ chars).

```typescript
import { MastraAuthOkta } from '@mastra/auth-okta'
new MastraAuthOkta({
  domain: process.env.OKTA_DOMAIN,
  clientId: process.env.OKTA_CLIENT_ID,
  clientSecret: process.env.OKTA_CLIENT_SECRET,
  redirectUri: process.env.OKTA_REDIRECT_URI,
})
```

Okta extras: `issuer` (default `https://{domain}/oauth2/default`), `audience` (`OKTA_AUDIENCE`, defaults to client ID; set it to accept access tokens), `scopes` (default includes `groups`), `session.cookiePassword` (32+ chars, `OKTA_COOKIE_PASSWORD`).

```typescript
import { MastraAuthSupabase } from '@mastra/auth-supabase'
new MastraAuthSupabase({ url: process.env.SUPABASE_URL, anonKey: process.env.SUPABASE_ANON_KEY })
```

```typescript
import { MastraAuthWorkos } from '@mastra/auth-workos'
new MastraAuthWorkos({
  apiKey: process.env.WORKOS_API_KEY,
  clientId: process.env.WORKOS_CLIENT_ID,
})
```

WorkOS extras: `redirectUri` (`WORKOS_REDIRECT_URI`) for AuthKit sign-in, `fetchMemberships` (set `true` with `MastraFGAWorkos`), `jwtClaims` (map custom JWT claims), `trustJwtClaims` (service-account tokens).

```typescript
import { MastraAuthNeon } from '@mastra/auth-neon'
new MastraAuthNeon() // reads NEON_AUTH_BASE_URL
```

Neon extras: `sessionCookieName` (default `neonauth.session_token`), `signUpEnabled`, `mapUserToResourceId`. Bearer tokens are verified with JWKS, then checked as session tokens.

---

## RBAC providers

RBAC requires a Mastra Enterprise Edition license in production. It works without one in development. Register with `server.rbac` next to `server.auth`.

| Class | Maps | Extra options |
|---|---|---|
| `MastraRBACOkta` | Okta groups to permissions | `domain`, `apiToken` (`OKTA_API_TOKEN`), `getUserId`, `cache: { ttlMs, maxSize }` |
| `MastraRBACGoogle` | Google Workspace groups to permissions | Service account (`GOOGLE_SERVICE_ACCOUNT_EMAIL`, `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY`) or access token, `mapGroupToRoles`, `getUserKey`, `cache` |
| `MastraRBACNeon` | Neon Auth organization roles | `organizationId`, `getUserRoles`, `cache` |

`roleMapping` keys are group or role names. Values are permission arrays such as `['*']`, `['agents:*', 'workflows:*']`, or `['agents:read']`. Use `_default` for unmatched users.

---

## Client-side token handling

- Clerk: `const token = await getToken()` from `useAuth()` in `@clerk/nextjs`, then `headers: { Authorization: \`Bearer ${token}\` }` on `MastraClient`.
- JWT: `headers: { Authorization: \`Bearer ${process.env.MASTRA_JWT_TOKEN}\` }`.
- Cookie-based providers (Better Auth, Neon, SSO sessions) across origins: `credentials: 'include'` on `MastraClient` and a credentialed CORS policy.
- Studio with JWT: Settings, Headers, add `Authorization: Bearer <jwt>`.
