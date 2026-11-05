# Launch checklist

## 1. Frame the job
- [ ] Users, inputs, and correct outcomes written down
- [ ] Five or more test cases with `must` and `mustNot`
- [ ] Agent vs workflow decision recorded
- [ ] Actions with side effects listed

## 2. Scaffold
- [ ] ESM project, ES2022 `tsconfig`
- [ ] Model ID verified, provider key in `.env`, names in `.env.example`
- [ ] Studio runs locally

## 3. First slice
- [ ] One primitive works end to end on a real input
- [ ] Registered on `new Mastra({...})`

## 4. Context
- [ ] Instructions hold only stable behavior
- [ ] Per-request data flows through messages or `RequestContext`
- [ ] Memory configured only where multi-turn is required, with `resource` and `thread` per call
- [ ] Retrieval in place for knowledge that does not fit in instructions

## 5. Control and safety
- [ ] `maxSteps` and `modelSettings.timeout` set
- [ ] Approval on every side-effecting tool
- [ ] Input guardrails (prompt injection, PII) and output guardrails on user-facing agents
- [ ] Model fallbacks for critical paths

## 6. Eval loop
- [ ] Dataset registered in Mastra
- [ ] Judge scorer from a different provider
- [ ] Baseline experiment recorded
- [ ] Each change compared against the baseline

## 7. Observability
- [ ] Tracing enabled with an exporter or Studio
- [ ] Tokens and latency per request reviewed
- [ ] Logs structured with a logger, not `console.log`

## 8. Integrate
- [ ] API protected by auth
- [ ] Frontend uses `MastraClient` or AI SDK UI helpers
- [ ] User identity mapped to memory `resource`

## 9. Deploy and operate
- [ ] Production storage adapter configured
- [ ] Regression eval runs in CI and blocks deploy
- [ ] Secrets in the platform's secret store
- [ ] Alerts on error rate and cost
- [ ] Process for adding production failures to the dataset
