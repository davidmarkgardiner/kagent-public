# Target acceptance

- [ ] Installed CRD and Istio schema validation; GitLab CI lint on target version.
- [ ] Runner -> bridge DNS, TLS, CA/proxy; bridge -> kagent/model/GitLab.
- [ ] Missing/invalid/expired identity and wrong project/ref rejected before calls.
- [ ] Non-allowlisted MR/fork and oversized context rejected before calls.
- [ ] Real A2A review/test-design calls and read-only MCP invocation recorded.
- [ ] Same request reuses durable evaluation; timeout does not replay agent work.
- [ ] Positive and negative assertions pass on candidate.
- [ ] Regression intended assertion fails on baseline and passes on candidate.
- [ ] Crashed executor/unrelated baseline error cannot produce expected_failure.
- [ ] New MR head invalidates review, tests and published gate.
- [ ] Missing test artifact/model outage/timeout/malformed response blocks merge.
- [ ] Known defect blocks; repaired defect passes with immutable evidence.
- [ ] Removing source CI include cannot remove mandatory gate.
- [ ] Test jobs have no credentials, privileged mounts or unrestricted egress.
- [ ] Protected branch and independent human approval enforced; no auto merge.
- [ ] Evidence records actual versions, SHAs, job IDs, model/tool calls and limits.
