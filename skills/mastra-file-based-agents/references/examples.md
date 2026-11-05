# File-based agent examples

All examples follow the current docs. Run them with `npx mastra dev` so discovery runs. Verify before copying into a project on an older version.

## Contents

1. Minimal agent
2. Agent with tools, a skill, memory, and storage
3. Research supervisor with subagents
4. Support agent with schedules

---

## 1. Minimal agent

```text
src/mastra/agents/
  writing-assistant/
    config.ts
    instructions.md
```

```typescript
// src/mastra/agents/writing-assistant/config.ts
import { agentConfig } from '@mastra/core/agent'

export default agentConfig({
  model: 'openai/gpt-6.1-sol',
})
```

```markdown
Rewrite text clearly and concisely.
```

Mastra registers the agent as `writing-assistant`. Run `npx mastra dev`, open Studio at `http://localhost:4111`, and select `writing-assistant`.

`.env`: `OPENAI_API_KEY=...`

---

## 2. Agent with tools, a skill, memory, and storage

```text
src/mastra/
  storage.ts
  agents/
    weather/
      config.ts
      instructions.ts
      memory.ts
      tools/
        get_weather.ts
      skills/
        units.md
```

```typescript
// src/mastra/storage.ts
import { LibSQLStore } from '@mastra/libsql'

export default new LibSQLStore({
  id: 'mastra-storage',
  url: 'file:./mastra.db',
})
```

```typescript
// src/mastra/agents/weather/config.ts
import { agentConfig } from '@mastra/core/agent'

export default agentConfig({
  id: 'weather-assistant',
  name: 'Weather Assistant',
  model: 'openai/gpt-6.1-sol',
  workspace: undefined, // no default file and shell tools
})
```

```typescript
// src/mastra/agents/weather/instructions.ts
import { agentInstructions } from '@mastra/core/agent'

export default agentInstructions(({ requestContext }) => {
  const tier = requestContext.get('tier') ?? 'standard'
  return `You are a helpful weather assistant. Treat this as a ${tier}-tier customer.`
})
```

```typescript
// src/mastra/agents/weather/tools/get_weather.ts  -> tool key: get_weather
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export default createTool({
  id: 'get_weather',
  description: 'Get the current weather for a location.',
  inputSchema: z.object({
    location: z.string(),
  }),
  outputSchema: z.object({
    location: z.string(),
    temperatureCelsius: z.number(),
    conditions: z.string(),
  }),
  execute: async ({ location }) => {
    return { location, temperatureCelsius: 21, conditions: 'sunny' }
  },
})
```

```markdown
---
description: Use when reporting temperatures or comparing forecast units.
---

Always report temperatures in Celsius and Fahrenheit. Include the user's preferred unit first when known.
```

```typescript
// src/mastra/agents/weather/memory.ts
import { Memory } from '@mastra/memory'

export default new Memory({
  options: {
    lastMessages: 20,
    workingMemory: {
      enabled: true,
      scope: 'resource',
    },
  },
})
```

Call it with the same `resource` and `thread` to continue a conversation:

```typescript
const weatherAgent = mastra.getAgentById('weather-assistant')

const response = await weatherAgent.generate('Remember that I prefer Celsius.', {
  memory: {
    resource: 'user-123',
    thread: 'weather-chat',
  },
})
```

---

## 3. Research supervisor with subagents

```text
src/mastra/agents/
  research-supervisor/
    config.ts
    instructions.md
    subagents/
      researcher/
        config.ts
        instructions.md
        tools/
          search_web.ts
      writer/
        config.ts
        instructions.md
        workspace/
          draft-template.md
```

```typescript
// research-supervisor/config.ts
import { agentConfig } from '@mastra/core/agent'

export default agentConfig({
  model: 'openai/gpt-6.1-sol',
})
```

```markdown
You coordinate research and writing.

Delegate fact gathering to `researcher`. Delegate final drafting to `writer`.
```

```typescript
// research-supervisor/subagents/researcher/config.ts
import { agentConfig } from '@mastra/core/agent'

export default agentConfig({
  model: 'openai/gpt-6-luna',
  description: 'Use to gather facts, sources, and concise research notes for a topic.',
})
```

```typescript
// research-supervisor/subagents/writer/config.ts
import { agentConfig } from '@mastra/core/agent'

export default agentConfig({
  model: 'openai/gpt-6.1-sol',
  description: 'Use to turn research notes into a structured draft.',
})
```

The supervisor gets `researcher` and `writer` delegation tools. `researcher` owns `search_web`. `writer` gets its own nested workspace seeded with `draft-template.md`. Neither inherits the parent's tools or memory. For delegation hooks and filtering, see `mastra-multi-agent`.

---

## 4. Support agent with schedules

```text
src/mastra/
  storage.ts
  agents/
    support/
      config.ts
      instructions.md
      schedules/
        weekly-digest.md
        billing/
          sweep.ts
```

```typescript
// support/config.ts
import { agentConfig } from '@mastra/core/agent'

export default agentConfig({
  model: 'openai/gpt-6.1-sol',
})
```

```markdown
---
cron: '0 9 * * 1'
timezone: 'America/New_York'
---

Summarize the past week's tickets and post the digest to the team channel.
```

```typescript
// support/schedules/billing/sweep.ts  -> id: billing/sweep
import { defineSchedule } from '@mastra/core/agent'

export default defineSchedule({
  cron: '0 3 * * *',
  timezone: 'America/New_York',
  handler: async () => {
    const overdue = await findOverdueInvoices()
    if (overdue.length === 0) return null // skip this fire
    return { prompt: `Draft reminders for ${overdue.length} overdue invoices.` }
  },
})
```

`storage.ts` is required so schedule rows survive restarts. Test without waiting for the cron:

```bash
curl http://localhost:4111/api/schedules
curl -X POST http://localhost:4111/api/schedules/<scheduleId>/run
```

Copy the id from the list response. `billing/sweep` on `support` is stored as `fsa_support__billing%2Fsweep`.
