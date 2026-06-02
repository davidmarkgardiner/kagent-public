# Codex Review — Smart Triage Integration Spike Pack

Review scope:

- `README.md`
- `spike-1-alert-ingestion.md`
- `spike-4-trace-context.md`
- `spike-5-deployment-state.md`
- `spike-6-policy-security-context.md`
- `spike-8-knowledge-runbook-retrieval.md`

## Verdict

Ready for the next planning owner. Do not start implementation until the selected
spike gets its own build-specific review and environment values are resolved.

## Findings Resolved In This Review

1. Alert ingestion namespace/RBAC ambiguity.
   The original alert plan reused an `argo-events` Sensor while the smart-triage
   workflow and service account live in `argo`. The plan now requires an explicit
   Phase 0 namespace decision and adds a cross-namespace submit RBAC artifact if
   the Sensor remains in `argo-events`.

2. Read-only validation false positives.
   Deployment-state and policy/security plans originally grepped the whole Agent
   manifest for mutating verbs. That would fail when the `systemMessage`
   correctly says those verbs are forbidden. The checks now inspect `toolNames`
   only.

3. Official GitLab MCP overclaim.
   The knowledge spike originally pointed too directly at the official GitLab MCP
   endpoint. The local live proof showed static header auth returned
   `Unauthorized`, while the lite MCP shim created the sandbox MR successfully.
   The plan now uses the proven shim for the first sandbox proof and treats the
   official GitLab MCP path as pending approved OAuth/auth.

4. Local-only workflow reference.
   The master README referenced a local assistant workflow note. The portable
   handoff now says to run a separate Codex review pass without depending on
   local-only profiles.

## Remaining Review Notes

- Spike 4 remains intentionally highest risk because no application trace
  backend is present in this repo. Build it last unless the work environment
  already has Tempo, Jaeger, or equivalent wired through Grafana.
- Spike 8 should choose one retrieval path for the first proof. The review agrees
  with the plan's recommendation: start with doc2vec/querydoc MCP, then compare
  BM25 only if needed.
- Spike 1 should be built first. It has the most existing repo reuse and changes
  the demo from synthetic input to a real alert trigger without adding write
  power.

## Recommended Next Step

Hand `spike-1-alert-ingestion.md` to the next agent for a build-specific plan.
Require it to decide the namespace/RBAC shape before writing manifests.
