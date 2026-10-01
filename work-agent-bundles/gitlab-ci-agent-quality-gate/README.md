# GitLab CI agent quality gate

Status: implementation handoff and offline-tested gate client. No endpoint,
agent deployment, isolated test executor, or workplace merge gate is claimed.
This is separate from the issue-board SDLC rig. GitLab CI is assumed; Istio is
an optional ingress pattern. Nothing here installs or modifies that rig.

## Workflow

MR pipeline -> trusted evaluation authority -> HTTPS VirtualService ->
evaluation bridge -> kagent review/test-design agents -> GitLab read-only MCP.
The bridge returns structured evidence; isolated CI workers execute proposed
tests. GitLab requires a successful gate on the current MR head plus human
approval. Agents and the bridge have no merge permission.

The bridge is a required target implementation, not supplied executable code.
Its contract is in contracts/PROTOCOL.md. scripts/gate.py is executable client
code for that contract. Do not route this client straight to kagent: the
controller speaks A2A JSON-RPC, not the evaluation bridge protocol.

## Deliverables

- ci/authority-job.yml: trusted-authority CI job template, fails closed.
- scripts/gate.py: bounded asynchronous client and strict result validation.
- contracts/PROTOCOL.md: bridge, authentication, SHA and test evidence contract.
- ingress/virtualservice.yaml: exact-path bridge route behind existing TLS Gateway.
- WORK-AGENT-START-PROMPT.md: implementation and target verification instructions.
- CHECKLIST.md: merge-blocking target proofs.
- tests/test_gate.py: stale SHA, missing evidence, expected-failure and HTTP checks.

## Required target configuration

Supply these outside public Git: GitLab API URL and allowed project IDs;
protected evaluator repository/ref; approved pinned runner image; bridge DNS,
namespace/service/port; existing TLS Gateway; CI identity issuer and audience;
model route; kagent agent namespace/names; corporate CA/proxy; secret references;
allowlisted test paths and trusted test harness. The bridge holds a read-only
GitLab identity. CI uses a short-lived endpoint identity, not a GitLab PAT.
An optional MR note writer is a separate identity and never decides acceptance.

The existing custom GitLab MCP can supply repository reads, pipeline reads and
traces, but cannot provide arbitrary diff/archive operations today. Add small
bounded read tools or let the bridge fetch immutable snapshots using the REST
API. Expose only read tools to reviewer/test-design agents. The board rig's
Developer credential and builder tools are unnecessary for this gate.

## Merge enforcement

Protect the target branch and require successful pipelines and human approval.
The agent gate must be mandatory, never allow_failure, manual-optional or
skippable. Authors must not be able to remove it by editing source-project CI.
Use an enforced CI policy if available, or a trusted evaluator plus mandatory
external status check where supported. A pinned include by itself is not an
enforcement boundary: a contributor can remove the include.

For multi-project pipelines use trigger strategy mirror on GitLab 18.2+;
validate the installed version and older depend behavior before adapting.
Resolve upstream project/MR/head server-side; downstream CI_COMMIT_SHA refers
to the authority repository, not the submitted code. Never use it as candidate
SHA. contracts/PROTOCOL.md specifies the independent head checks.

## What tests mean

Positive: valid behavior produces the expected result. Negative: invalid input
is rejected with the expected error; that test must PASS. Regression: test fails
on the known-bad baseline and passes on the candidate. Mutation: a relevant
seeded defect is caught by the test. A generic process failure is not evidence
that a negative/regression test worked. Missing evidence blocks merge.

Generated test source is untrusted executable code. Execute in disposable,
resource-bounded jobs with no PAT, model credential or privileged mounts and
restricted egress. Install dependencies from approved pinned mirrors. Fetch
snapshots before entering the executor. Agents may return test proposals or a
separate test-only branch; never silently edit the candidate while evaluating.
New commits invalidate previous review and tests. Tests become permanent code
only through a separately reviewed commit and a fresh gate.

## Other pipeline workflows

| Workflow | Trigger | Useful result / gate |
|---|---|---|
| Peer review | MR update | SHA-bound findings; blockers resolved before merge |
| Test design | Behavior/API change | Positive, negative and regression cases executed by CI |
| Failure triage | Failed CI | Bounded log diagnosis and proposed fix; advisory |
| Documentation drift | API/config change | Missing README/runbook/API updates; optional mandatory check |
| IaC review | Terraform/Kubernetes change | Agent explanation plus deterministic plan/schema/policy checks |
| Dependency review | Lockfile change | License, vulnerability and compatibility findings; scanner evidence wins |
| Release preparation | Approved release | Draft changelog and rollback/verification plan; separate release approval |

Start with peer review plus one language-specific test executor. Expand only
when each workflow has target evidence. Do not use agent review as a substitute
for compilers, linters, security scanners, or human approval.

## Offline verification

Run python3 -m unittest discover -s tests -v from this folder.
CI, Istio schema, DNS/TLS/authentication, model/MCP invocation and GitLab merge
blocking require the target environment; offline tests prove only client logic.

## Official references

https://docs.gitlab.com/user/project/merge_requests/status_checks/
https://docs.gitlab.com/user/project/merge_requests/auto_merge/
https://docs.gitlab.com/ci/pipelines/downstream_pipelines/
https://docs.gitlab.com/ci/yaml/
https://istio.io/latest/docs/reference/config/security/request_authentication/

See CHECKLIST.md before claiming readiness.
