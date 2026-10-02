**Assessment:** The repair fixed most of the 14 earlier findings, and the manifests now match what the design says. One High issue still blocks approval: the values file is not strictly validated. A value can inject extra settings into the JWT policy or turn the Workflow's alert check into one that always passes, and no offline check looks at the real render. There are also 8 Medium findings. No live cluster claims are made, and none were checked.

I read the full diff and the worktree `/private/tmp/kagent-public-auth.lQZH8n` (branch `feat/cluster-health-authenticated-front-door`); its changed-file list matches the diff. I only rendered in memory to test the injection and wrote nothing. I did not re-run Codex's verification suite.

`WB` = `work-agent-bundles/cluster-health-assessment-plan/workplace-bundle`

## High

**H1. Values are not strictly validated, so text can be injected into the JWT policy and the jq alert check.** Offline blocker.
- **Where:** `WB/scripts/render.py:87-92` and `:140`, `WB/manager/argo.yaml:217`, `WB/manager/agentgateway.yaml:69-76`, `WB/scripts/verify.py:375`.
- **The flaw:** `validate()` checks the issuer and JWKS URI only with `urlparse` (https plus a hostname) and the audience only with `startswith("api://")`. `MCP_CLUSTER_TARGET` is only checked to be non-empty. `render()` then does a plain text replace into YAML and into a jq program.
- **Proof 1, JWT audience:** `AGENTGATEWAY_AUDIENCE="api://cluster-health-agentgateway'\n        - 'https://kubernetes.default.svc.cluster.local"` passes `validate()`. The rendered AgentgatewayPolicy parses with `audiences: ['api://cluster-health-agentgateway', 'https://kubernetes.default.svc.cluster.local']`, so every API-server-audience token would pass the audience check.
  - In this one case the second use of the audience (`argo.yaml:165`) breaks the file's indentation, so the apply would fail.
  - The issuer and JWKS URI are used only once and accept the same quote and newline characters, so injection through them would not break anything else.
- **Proof 2, alert validation:** `MCP_CLUSTER_TARGET='worker-a" or true or "'` renders as `... and .cluster.mcp_target == "worker-a" or true or "" and ...`. In jq, `and` binds tighter than `or`, so the whole filter is always true. I confirmed this with jq. That silently skips the namespace-subset, freshness and workflow-name checks.
- **Why nothing catches it:** `verify.py` runs `validate_access_boundary` only against `fixtures/test-values.json`, never against the operator's real values.
- **Fix:**
  - Use full-match allowlists per field:
    - issuer and JWKS URI: `^https://[A-Za-z0-9.-]+(:[0-9]+)?(/[A-Za-z0-9._~%-]+)*/?$`
    - audience: `^api://[A-Za-z0-9._-]+$`
    - `MCP_CLUSTER_TARGET` and `CLUSTER_ID`: DNS label
  - Reject `'`, `"`, `\` and control characters in every value.
  - Pass the target into jq with `--arg` instead of text substitution.
  - After rendering, parse the output and run `validate_access_boundary(values=<real values>)` inside `render.py`, or make `verify-live.sh` run it.

## Medium

**M1. Any pod in the agentgateway namespace can reach the kagent controller without a JWT.** `WB/manager/network-policies.yaml:93-94`
- The controller ingress peer is a namespace selector only. Any pod in `agentgateway-system` (control plane, any other workload) can call `:8083/api/a2a/kagent/<any-agent>/` without a token and without the fixed path rewrite.
- The earlier review asked for a pod selector plus a namespace selector.
- **Fix:**
  - Add a `podSelector` for the Gateway's proxy pods, for example `gateway.networking.k8s.io/gateway-name: {{AGENTGATEWAY_GATEWAY_NAME}}` (confirm the label on the live cluster).
  - Update the expected peers in `verify.py`.
  - Add a live probe from a non-proxy pod in that namespace.

**M2. The route is not pinned to a listener or hostname.** `WB/manager/agentgateway.yaml:26-35`
- There is no `sectionName` and no `hostnames`, so the route attaches to every listener on the shared Gateway. If the proxy Service is a LoadBalancer (common for provisioned proxies), the agent route may be reachable from outside the cluster. The JWT check still applies, but the unauthenticated rate-limit problem in M3 would be exposed too.
- **Fix:**
  - Pin `sectionName` to an internal listener.
  - Set `hostnames: [{{AGENTGATEWAY_SERVICE_NAME}}.{{AGENTGATEWAY_NAMESPACE}}.svc.cluster.local]`.
  - Assert both exactly in `verify.py`.
  - Check the Service type or internal-load-balancer setting in `verify-running.sh`.

**M3. The rate limit of 2 per minute can block the daily call and break the live verifier.** `WB/manager/agentgateway.yaml:82-86`, `WB/scripts/verify-running.sh:147-181`
- If the limit is counted before authentication (not verified), unauthenticated requests can use it up. The Workflow's `curl --fail` has no retry, so that day's investigation is silently lost.
- `verify-running.sh` sends four route requests within seconds (no token, wrong audience, wrong subject, positive), so the third or fourth would likely get 429 and fail the script for no real reason.
- **Fix:**
  - Confirm the policy evaluation order on the live cluster.
  - Add a bounded retry on 429 in the Workflow.
  - Space out or rate-aware the probes, and assert that no response is 429.

**M4. The new NetworkPolicies cut off kagent's own traffic.** `WB/worker/mcp-network-policy.yaml:12-20`, `WB/manager/network-policies.yaml:81-99`
- MCP ingress allows only the investigator pod. The kagent controller also connects to the RemoteMCPServer to discover tools, so the Agent may never become Ready. This fails closed, but it blocks the only end-to-end path.
- The controller policy selects the shared controller, so it also blocks the kagent UI, other agents' calls back to the controller, and metrics.
- If a permissive NetworkPolicy already selects the controller, the new policy adds nothing and no check notices.
- **Fix:**
  - Add a controller peer on the MCP port and update `verify.py`.
  - Narrow the selector with `app.kubernetes.io/name: kagent`.
  - Document the effect on other kagent users.
  - Add a live inventory of every NetworkPolicy that selects the controller, agent or MCP pods, plus a probe from an unrelated namespace.

**M5. The offline RBAC checks still miss ways to broaden access.** `WB/scripts/verify.py:170`, `:230`
- RoleBinding checks compare only `roleRef.name`, not kind or apiGroup.
- The node ClusterRoleBinding's `roleRef` is never checked, so pointing it at `cluster-admin` still passes.
- `aggregationRule` on the two ClusterRoles is not rejected.
- There is no scan for other bindings in the rendered docs whose subjects include the MCP ServiceAccount or its groups (`system:serviceaccounts[:ns]`, `system:authenticated`).
- **Fix:** Compare the full `roleRef` exactly, reject `aggregationRule`, and scan all bindings by subject.

**M6. The live negative RBAC checks are incomplete.** `WB/scripts/verify-running.sh:41-42`
- Secret and ConfigMap reads, and pod creation, are checked only in the first namespace.
- Missing checks:
  - cluster-wide `list/watch secrets`;
  - reads on `roles`/`clusterroles`;
  - `create serviceaccounts/token`, `pods/attach`, `pods/ephemeralcontainers`;
  - `create nodes/proxy`.
- **Fix:**
  - For every namespace, check get/list/watch on Secrets and ConfigMaps, and create on pods, `pods/exec`, `pods/attach` and `pods/portforward`.
  - Add the cluster-scope checks above.

**M7. The list of bypass paths to inventory is incomplete.** `WB/AUTHENTICATED-ACCESS.md:57-62`
- It covers only who can create pods, workflows or tokens in `argo-events`.
- It leaves out who holds any of these in `kagent`, `agentgateway-system` and `aks-mcp`:
  - `pods/portforward` (port-forward traffic is not subject to NetworkPolicy);
  - `services/proxy` or `pods/exec`;
  - pod creation;
  - write access on the Agent, RemoteMCPServer, HTTPRoute, AgentgatewayPolicy or ReferenceGrant.
- **Fix:** Add these to the documented inventory and to a scripted `auth can-i` gate.

**M8. The docs do not all stop a split-cluster deployment.** `WB/README.md:15-30`, `:171`, `:182`, `WB/TEST-PLAN.md`
- The README still presents separate worker and manager clusters and a two-context run with no stop note. TEST-PLAN has none either. Disposition item 10 claims all operator docs stop a split deployment.
- **Fix:**
  - Add the stop note to README and TEST-PLAN.
  - Make `verify-live.sh` and `verify-running.sh` exit if the `kube-system` namespace UID differs between the two contexts.

## Low
- `verify-running.sh:164,171,178,191` pass 10-minute bearer tokens on the curl command line, and the positive-control token can invoke the agent. Use `-H @-` as the Workflow does.
- `network-policies.yaml:89,115`: the selector `app.kubernetes.io/component: controller` may match other controller pods in the kagent namespace.
- `verify-live.sh:12`: `kubectl explain` only proves the two policy fields exist, not their nested shape. Pass `--validate=strict` to the server dry-run explicitly.
- `public-safe-scan.allowlist:22` exempts the whole evidence file. Pin it by sha256.
- Ports `8083` and `8080` are hard-coded and not checked live against the real Service and container ports. `argo-events` and `kagent` are hard-coded even though namespace variables exist; a mismatch fails closed.

## Prior findings: repaired?
| # | Status |
|---|---|
| 1 Complete diff | ✅ New files present; worktree status matches the diff |
| 2 Numeric ports | ✅ `kubectl kustomize` rewrites ports into a form the regex matches; integers render; target port checked live |
| 3 Agent runtime ingress | ✅ (pod label must be confirmed on the live cluster) |
| 4 Controller peers | ⚠️ Partial: namespace-wide peer (M1) |
| 5 Exact route/policy check | ⚠️ Exact, but only against the test fixture (H1) |
| 6 RBAC allowlists | ⚠️ Partial (M5) |
| 7 Sensor/token residual risk | ✅ Documented as a gate |
| 8 Live positive/negative tests | ⚠️ Mostly (M3, M6) |
| 9 Scan allowlist | ✅ (Low) |
| 10 Split-cluster docs | ⚠️ Partial (M8) |
| 11 MCP NetworkPolicy | ⚠️ Blocks controller tool discovery (M4) |
| 12 Token handling | ✅ |
| 13 Sensor can-i | ✅ |
| 14 Values | ⚠️ Target pinned but injectable (H1) |

## Offline blockers vs target-cluster gates
- **Offline, fixable now:**
  - H1 (blocks approval);
  - M1, M2, the controller-peer and selector parts of M4;
  - M5, M8, and the script and doc parts of M6 and M7.
- **Target-cluster gates, correctly documented as NOT RUN:**
  - server dry-run and CRD schema;
  - JWT tests (401, 403, positive control) and rate-limit ordering;
  - whether the CNI enforces the policies, including the API-server ipBlock;
  - kagent pod labels and ports, and RemoteMCPServer tool discovery;
  - AKS-MCP rejecting override flags, and denial of the Azure credential actions;
  - leftover chart RBAC, the token-issuance inventory, and the Kafka end-to-end proof.

REVIEW_STATUS: REVISE
