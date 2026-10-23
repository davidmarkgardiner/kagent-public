# Authenticated front-door verification

Date: 2026-09-16

## Offline evidence

Run from the repository root after the repair-review disposition:

```text
python3 work-agent-bundles/cluster-health-assessment-plan/workplace-bundle/scripts/verify.py
PASS: Workplace cluster-health bundle verification passed

bash work-agent-bundles/cluster-health-assessment-plan/verify-all.sh
PASS: 28 health tests, 5 assessor tests, 1 reconciler test, Fox mesh checks,
workplace render/security checks, Go tests and package verification

git diff --check
PASS

bash -n workplace-bundle/scripts/verify-live.sh workplace-bundle/scripts/verify-running.sh
PASS

python3 -m json.tool fixtures/test-values.json
python3 -m json.tool values.example.json
PASS
```

The security verifier includes malicious value cases for JWT audience, issuer
and MCP target injection. Each must be rejected before a manifest is written.
It also performs exact structural checks for the route, JWT policy, reference
grant, namespace inventory, RBAC subjects/rules and NetworkPolicy peers.

## Independent review

- Architecture challenge: GLM-5.3, completed without fallback, `REVISE`; all
  material findings dispositioned.
- Final review: Claude, completed without fallback, `REVISE`; all findings
  repaired or explicitly gated.
- One permitted repair review: Claude, completed without fallback, `REVISE`;
  its High injection finding and offline Medium findings were repaired and
  regression-tested. The unchanged review and the post-review disposition are
  retained beside this file.

The review status is not represented as approval. This branch is suitable for
a human-reviewed merge request, not for automatic merge or deployment.

## Not run

No target cluster was available. The following remain promotion blockers:

- installed AgentgatewayPolicy schema and strict server-side dry-run;
- actual Gateway listener, Service target port, generated pod labels and
  NetworkPolicy additivity;
- JWT 401/403/positive controls and fixed-route probes;
- kagent controller tool discovery and Agent Ready/invocation;
- effective MCP RBAC across every namespace and override-flag rejection;
- Kafka produced-and-consumed proof, daily dedupe, fault/recovery and soak;
- GitLab writer create/update/replay proof in a disposable project.

Nothing was deployed or merged as part of this verification.
