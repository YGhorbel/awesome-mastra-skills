# Agent skills examples

All examples follow the current docs. Verify before copying into a project on an older version.

## Contents

1. Inline skill with bundled references
2. Role-based dynamic skills
3. Workspace skills shared across agents, with an agent-level override
4. Validating an uploaded SKILL.md before saving

---

## 1. Inline skill with bundled references

```typescript
// src/mastra/skills/release-checklist.ts
import { createSkill } from '@mastra/core/skills'

export const releaseChecklist = createSkill({
  name: 'release-checklist',
  description: 'Use when preparing a release.',
  instructions: `
    ## Release Checklist
    1. Run the full test suite
    2. Update CHANGELOG.md
    3. Bump version numbers
    4. Create a git tag
  `,
  references: {
    'changelog-format.md': '# Changelog Format\nUse Keep a Changelog...',
  },
})
```

```typescript
// src/mastra/agents/release-agent.ts
import { Agent } from '@mastra/core/agent'
import { releaseChecklist } from '../skills/release-checklist'

export const releaseAgent = new Agent({
  id: 'release-agent',
  name: 'Release Agent',
  instructions: 'You help engineers ship releases safely.',
  model: 'openai/gpt-6.1-sol',
  skills: [releaseChecklist],
})
```

The agent sees `release-checklist` and its description in the system message. When asked to cut a release it calls `skill` to load the checklist, and `skill_read` for `changelog-format.md` if needed.

Read it from application code:

```typescript
const skill = await releaseAgent.getSkill('release-checklist')
if (skill) console.log(skill.instructions, skill.path) // path: 'inline/release-checklist'
```

---

## 2. Role-based dynamic skills

```typescript
import { Agent } from '@mastra/core/agent'
import { createSkill } from '@mastra/core/skills'

const devSkill = createSkill({
  name: 'dev-tools',
  description: 'Developer productivity tools.',
  instructions: '...',
})

const supportSkill = createSkill({
  name: 'support-guide',
  description: 'Customer support guidelines.',
  instructions: '...',
})

export const agent = new Agent({
  id: 'dynamic-agent',
  name: 'Dynamic Agent',
  instructions: 'You help users of our product.',
  model: 'openai/gpt-6.1-sol',
  skills: ({ requestContext }) => {
    const role = requestContext.get('userRole')
    if (role === 'developer') return [devSkill]
    return [supportSkill]
  },
})
```

```typescript
import { RequestContext } from '@mastra/core/request-context'

const requestContext = new RequestContext()
requestContext.set('userRole', 'developer')

const skills = await agent.listSkills({ requestContext })
// [{ name: 'dev-tools', description: 'Developer productivity tools.', path: 'inline/dev-tools' }]

await agent.generate('How do I profile the build?', { requestContext })
```

An async resolver that fetches entitlements can add its own span. Guard it, because metadata reads run without one:

```typescript
skills: async ({ requestContext, tracingContext }) => {
  const span = tracingContext?.currentSpan?.createChildSpan({
    type: 'generic',
    name: 'entitlements-lookup',
  })
  const skills = await fetchSkillsFor(requestContext.get('userId'))
  span?.end()
  return skills
}
```

---

## 3. Workspace skills shared across agents, with an agent-level override

Layout:

```plaintext
workspace/
  skills/
    code-review/
      SKILL.md
      references/style-guide.md
    testing/
      SKILL.md
```

```markdown
---
name: code-review
description: Reviews code for bugs and readability issues
---

# Code review

Check the code for bugs, missing error handling, and unclear naming.
Read references/style-guide.md before commenting on style.
```

```typescript
import { Agent } from '@mastra/core/agent'
import { Workspace, LocalFilesystem } from '@mastra/core/workspace'
import { createSkill } from '@mastra/core/skills'

const workspace = new Workspace({
  filesystem: new LocalFilesystem({ basePath: './workspace' }),
  skills: ['skills'], // provides "code-review" and "testing"
})

const customReview = createSkill({
  name: 'code-review', // same name as the workspace skill
  description: 'Custom review process.',
  instructions: '...',
})

export const reviewer = new Agent({
  id: 'reviewer',
  name: 'Reviewer',
  instructions: 'You review pull requests.',
  model: 'openai/gpt-6.1-sol',
  workspace,
  skills: [customReview], // agent-level "code-review" wins
})

export const tester = new Agent({
  id: 'tester',
  name: 'Tester',
  instructions: 'You write and fix tests.',
  model: 'openai/gpt-6.1-sol',
  workspace, // gets the workspace "code-review" and "testing"
})
```

Add role-specific paths with a dynamic workspace resolver:

```typescript
const workspace = new Workspace({
  filesystem: new LocalFilesystem({ basePath: './workspace' }),
  skills: ({ requestContext }) => {
    const paths = ['skills']
    if (requestContext?.get('user-role') === 'developer') paths.push('developer-skills')
    return paths
  },
})
```

---

## 4. Validating an uploaded SKILL.md before saving

```typescript
import { validateSkillContent } from '@mastra/core/skills'

export function assertValidSkill(skillMarkdown: string, directoryName: string) {
  const result = validateSkillContent({ content: skillMarkdown, directoryName })

  if (!result.valid) {
    throw new Error(`Invalid skill:\n${result.errors.join('\n')}`)
  }
  // result.warnings lists non-blocking issues, such as very long instructions
  return result.warnings
}
```

Call it in the tool, route, or upload handler that writes the file, before any write to the workspace.
