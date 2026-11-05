# Suspend and resume examples

All examples follow the current docs. Verify before copying into a project on an older version.

## Contents

1. Expense approval with a resume endpoint
2. Multi-stage approval
3. Per-item approval inside foreach
4. Recovering a failed run with time travel

---

## 1. Expense approval with a resume endpoint

```typescript
// src/mastra/workflows/expense-workflow.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const expenseInput = z.object({
  value: z.number(),
  user: z.string(),
  requiredApprovers: z.array(z.string()),
})
const expenseOutput = z.object({ value: z.number(), approved: z.boolean() })

export const approvalStep = createStep({
  id: 'approval-step',
  description: 'Accepts a value, waits for confirmation',
  inputSchema: expenseInput,
  suspendSchema: z.object({
    message: z.string(),
    requestedBy: z.string(),
    approvers: z.array(z.string()),
  }),
  resumeSchema: z.object({
    confirm: z.boolean(),
    approver: z.string(),
  }),
  outputSchema: expenseOutput,
  execute: async ({ inputData, resumeData, suspend }) => {
    const { value, user, requiredApprovers } = inputData
    const { confirm } = resumeData ?? {}
    if (!confirm) {
      return await suspend({
        message: 'Workflow suspended',
        requestedBy: user,
        approvers: [...requiredApprovers],
      })
    }
    return { value, approved: confirm }
  },
})

export const expenseWorkflow = createWorkflow({
  id: 'expense-workflow',
  inputSchema: expenseInput,
  outputSchema: expenseOutput,
})
  .then(approvalStep)
  .commit()
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { expenseWorkflow } from './workflows/expense-workflow'

export const mastra = new Mastra({
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
  workflows: { expenseWorkflow },
})
```

Start the run and hand the `runId` and payload to a reviewer:

```typescript
const workflow = mastra.getWorkflow('expenseWorkflow')
const run = await workflow.createRun()
const result = await run.start({
  inputData: { value: 100, user: 'Michael', requiredApprovers: ['manager', 'finance'] },
})

if (result.status === 'suspended') {
  const [stepId] = result.suspended[0]
  await notifyReviewer({ runId: run.runId, payload: result.steps[stepId].suspendPayload })
}
```

Resume from a later request (any process with the same storage):

```typescript
export async function approveExpense(runId: string, approver: string) {
  const workflow = mastra.getWorkflow('expenseWorkflow')
  const run = await workflow.createRun({ runId })
  try {
    return await run.resume({
      step: 'approval-step',
      resumeData: { confirm: true, approver },
    })
  } catch (error) {
    if (error.id === 'WORKFLOW_RESUME_ALREADY_CLAIMED') return null
    throw error
  }
}
```

`notifyReviewer` stands for your own messaging code.

---

## 2. Multi-stage approval

Each stage suspends in turn. Rejection at either stage ends the run with `bail()`.

```typescript
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const decision = z.object({ approved: z.boolean() })
const reason = z.object({ reason: z.string() })

const managerApproval = createStep({
  id: 'manager-approval',
  inputSchema: z.object({ message: z.string() }),
  outputSchema: z.object({ message: z.string() }),
  resumeSchema: decision,
  suspendSchema: reason,
  execute: async ({ inputData, resumeData, suspend, bail }) => {
    const { approved } = resumeData ?? {}
    if (approved === false) return bail({ message: 'Rejected by manager' })
    if (!approved) return await suspend({ reason: 'Manager approval required.' })
    return inputData
  },
})

const financeApproval = createStep({
  id: 'finance-approval',
  inputSchema: z.object({ message: z.string() }),
  outputSchema: z.object({ message: z.string() }),
  resumeSchema: decision,
  suspendSchema: reason,
  execute: async ({ inputData, resumeData, suspend, bail }) => {
    const { approved } = resumeData ?? {}
    if (approved === false) return bail({ message: 'Rejected by finance' })
    if (!approved) return await suspend({ reason: 'Finance approval required.' })
    return { message: `${inputData.message} - Approved` }
  },
})

export const twoStageWorkflow = createWorkflow({
  id: 'two-stage-approval',
  inputSchema: z.object({ message: z.string() }),
  outputSchema: z.object({ message: z.string() }),
})
  .then(managerApproval)
  .then(financeApproval)
  .commit()
```

```typescript
await run.resume({ step: 'manager-approval', resumeData: { approved: true } }) // suspends at finance
await run.resume({ step: 'finance-approval', resumeData: { approved: true } }) // success
```

---

## 3. Per-item approval inside foreach

Every array item suspends on its own. Resume items individually with `forEachIndex`.

```typescript
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const approve = createStep({
  id: 'approve',
  inputSchema: z.object({ item: z.string() }),
  outputSchema: z.object({ item: z.string(), ok: z.boolean() }),
  resumeSchema: z.object({ ok: z.boolean() }),
  execute: async ({ inputData, resumeData, suspend }) => {
    if (resumeData === undefined) return await suspend({ item: inputData.item })
    return { item: inputData.item, ok: resumeData.ok }
  },
})

export const batchApproval = createWorkflow({
  id: 'batch-approval',
  inputSchema: z.array(z.object({ item: z.string() })),
  outputSchema: z.array(z.object({ item: z.string(), ok: z.boolean() })),
})
  .foreach(approve, { concurrency: 3 })
  .commit()
```

```typescript
await run.resume({ step: 'approve', resumeData: { ok: true }, forEachIndex: 1 })
await run.resume({ step: 'approve', resumeData: { ok: false }, forEachIndex: 0 })
// Omit forEachIndex to resume every remaining item with the same data.
```

---

## 4. Recovering a failed run with time travel

```typescript
const workflow = mastra.getWorkflow('myWorkflow')
const run = await workflow.createRun()

const failed = await run.start({ inputData: { value: 1 } })

if (failed.status === 'failed') {
  // Fix the cause (for example an expired credential), then re-run from step2
  const recovered = await run.timeTravel({
    step: 'step2',
    inputData: { step1Result: 5 },
  })
  console.log(recovered.status)
}
```

Stream the re-run instead:

```typescript
const output = run.timeTravelStream({ step: 'step2', inputData: { step1Result: 5 } })
for await (const event of output.fullStream) console.log(event.type)
const result = await output.result
```

Supply `context` with prior step results to test one step without running the steps before it.
