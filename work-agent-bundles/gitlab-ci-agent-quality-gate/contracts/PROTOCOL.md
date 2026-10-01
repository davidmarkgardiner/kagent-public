# Evaluation bridge contract v1

The bridge is a target-owned service, exposed through an existing TLS Gateway.
A VirtualService is routing, not authentication. Validate GitLab CI OIDC JWT
signature, expiry, issuer, audience and allowlisted authority project/ref at the
bridge or an enforced ingress auth layer. Istio RequestAuthentication alone
allows absent JWTs; pair it with AuthorizationPolicy requiring a valid principal
and the expected claims. Bind policy to the actual enforcing workload. Prove
unauthenticated and wrong-project requests are rejected. Restrict the hostname
to this bridge; do not expose the whole kagent controller. No automatic POST
retries: timeout may leave an agent running.

## Submit

POST /v1/evaluations using an Authorization header with the CI identity.
Request fields: schema_version=1, project_id (positive integer), mr_iid
(positive integer), expected_head_sha (full 40-character SHA), and
pipeline_id (authority pipeline ID string). These are untrusted selectors.

The bridge queries its approved GitLab host for the project and open MR,
checks target branch and source-project policy, resolves current diff head and
base SHAs, and compares expected_head_sha. Never accept a caller-supplied URL,
prompt, model, shell command or project outside the allowlist. Resolve runner
ownership via CI identity and API, not pipeline_id alone. Forks require explicit
policy; initially reject them. Bound files, diff bytes, logs and tool responses;
truncation that removes required review context yields BLOCK.

Reserve a durable evaluation keyed by project, MR, head SHA, policy version,
model profile and test-harness version. Repeated submit reuses status rather
than starting another task. Preserve kagent task IDs and use tasks/get;
timeout is not cancellation. Work queues have finite deadlines and call/token
budgets. Agent errors/unknown states never count as PASS.

Response HTTP 202: {"evaluation_id":"opaque-safe-id","status":"pending"}.
Do not return arbitrary poll URLs. Client polls GET /v1/evaluations/<id> at the
same approved host with the same authentication. IDs match [A-Za-z0-9_-]{1,128}.
Authorize every GET to the submitter scope. Incomplete response: status=pending
or running. Completed response has status=completed and result as below.

## Completed result

Required: schema_version=1, project_id, mr_iid, head_sha, verdict=PASS|BLOCK,
review={verdict:PASS|BLOCK,artifact:string}, tests=[...].
Each test evidence object contains kind=positive|negative|regression,
outcome=pass|fail, candidate_sha matching head_sha, artifact (authority-owned
immutable evidence reference), and harness_version. Require at least one test
of each kind for the initial bug-fix profile; other profiles need separately
reviewed gate policy, never ad hoc model-selected exemptions.
Regression entries also require baseline_outcome=expected_failure,
baseline_sha (full SHA distinct from candidate), and baseline_artifact.
The artifact must show the intended assertion failed on the baseline, not an
infrastructure, dependency, compilation or unrelated test error.

The bridge checks executor artifacts and real exit codes before assembling
this result. Agents can propose cases and findings, not author PASS evidence.
Use an operator-owned test harness and isolate baseline/candidate runs.
Before completion re-read MR head and require it still matches. Mandatory
GitLab gate publisher must check it again immediately before publishing and
bind status to that head SHA. Keep findings, model/agent versions, call IDs,
latency, truncation and execution evidence with bounded retention. Omit secrets.
The CLI validates the fields but cannot prove artifacts exist: authority ownership
and artifact verification are bridge responsibilities.

## kagent integration

Use the repository helper scripts/kagent-a2a-invoke.sh for target smoke checks.
In the bridge, implement A2A JSON-RPC message/send with kind:text message parts
and a trailing slash /api/a2a/<namespace>/<agent>/. Poll durable returned task
IDs using tasks/get; verify installed controller behavior. Inspect the actual
Agent CRD before building reviewer and test-design agents. Agents use existing
ModelConfig and read-only RemoteMCPServer tools; no Kubernetes write tools,
repository commit tools or merge tools. Treat diff/comments as untrusted data,
not instructions. Review prompt requires file/line, severity, concrete issue,
evidence, suggested test, and structured verdict. Test-design prompt returns
bounded test files, expected assertions and baseline rationale. Neither runs
arbitrary code on the agent service.

## Failure semantics

Unauthorized, stale SHA, non-open MR, invalid inputs and non-allowlisted project:
reject before model invocation. Transport timeout, partial context, unavailable
model, incomplete tests, malformed JSON or stale artifact: BLOCK / failed CI.
A deliberate BLOCK produces a completed result with evidence, not HTTP success
that the client interprets as approval. Rate-limit requests and retain status
so another pipeline can observe prior work without replaying it.
