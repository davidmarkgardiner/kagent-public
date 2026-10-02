# Review: cluster-health authenticated-access hardening

I could only review the diff text. The working directory has no repo checkout, so none of these findings has been run against the code. Nine findings block approval: three High issues break the manifests or the kagent runtime, and several more gaps mean `verify.py` passing does not prove the acceptance criteria.

## Blocking

### 1. [High] The diff is missing the files that carry the security controls
**Where:** `manager/kustomization.yaml:5-6`, `worker/kustomization.yaml:7-8`, `scripts/verify.py:~324`, `README.md` link.

**Evidence:** The diff adds these to the kustomizations and scripts, but none of them appear in the "complete diff":
- `agentgateway.yaml`
- `approved-namespaces.yaml`
- `mcp-rbac.yaml`
- `mcp-rolebindings.yaml`
- `render-mcp-rbac.py`
- `AUTHENTICATED-ACCESS.md`

Those files hold the HTTPRoute, AgentgatewayPolicy (issuer, audiences, JWKS, match expressions, targetRefs), ReferenceGrant, both ClusterRoles and the node-read ClusterRoleBinding. Acceptance criteria 1, 2 and 5 depend on them.

**Fix:** Regenerate the diff including untracked files (`git add -N` then `git diff origin/feat/cluster-health-daily-summary`) and resubmit.

### 2. [High] The rendered NetworkPolicy port is a string, so the manager manifest will not apply
**Where:** `manager/network-policies.yaml:76`, `scripts/verify.py:311`

**Evidence:** The template has `port: "{{AGENTGATEWAY_PORT}}"`, and the verifier asserts the output is `port: '18080'`. `NetworkPolicyPort.port` accepts either an integer or a string. A string is treated as a *named* port, and a named port must contain at least one letter. So `"8080"` fails API validation and the server dry-run or apply is rejected. The verifier locks this bug in.

There is a second problem. NetworkPolicy matches the destination **pod** port. The URL uses the **Service** port. `values.example.json:5` sets `"80"`, and gateway deployers often remap privileged listener ports (80 → 8080), so the policy would drop the traffic even with a valid integer.

**Fix:**
- Use an integer sentinel plus a `render.py` regex substitution, the same pattern already used for 31443 and 9092.
- Add a separate `AGENTGATEWAY_TARGET_PORT` for the policy.
- Change the verifier to expect `port: 18080` (integer).
- Have `verify-live.sh` compare the Service `targetPort`.

### 3. [High] The kagent agent pod is reachable directly, bypassing the gateway
**Where:** `manager/network-policies.yaml:87-89`

**Evidence:** The ingress policy only selects `app.kubernetes.io/component: controller`. The kagent declarative runtime also creates a separate agent Deployment and Service (`cluster-health-investigator.kagent`), and the controller just proxies A2A calls to it. Nothing restricts ingress to that pod. Any pod in the cluster can POST A2A there with no JWT, which breaks "only the exact Workflow ServiceAccount can invoke."

**Fix:**
- Add a NetworkPolicy on the agent pods that allows ingress only from the controller pods, using `podSelector` together with `namespaceSelector`.
- Add a live test from an unrelated pod that confirms both the agent Service and the controller are denied.

### 4. [High] Gateway-only controller ingress likely breaks the kagent runtime
**Where:** `manager/network-policies.yaml:91-95`, `scripts/verify.py:160`

**Evidence:** kagent agent pods call back to the controller on port 8083 (`KAGENT_URL`) for sessions and tasks, and the UI also calls the controller. The policy only admits the agentgateway namespace. The verifier makes this worse: it fails if `"kagent"` appears anywhere in the ingress peers. The Agent can report Ready while every invocation fails, and no end-to-end test has run, so nothing would catch it.

**Fix:**
- Allow ingress from the agentgateway proxy pods (pod + namespace selector) and from the investigator agent pod (and the UI if needed).
- Replace the string check in `verify.py` with structural checks on each peer.

### 5. [High] The offline verifier does not prove "Strict JWT + exact subject"
**Where:** `scripts/verify.py:72-92`

**Evidence:**
- `any(expected_subject in value ...)` is a substring check. An extra expression such as `true`, or a `startsWith("system:serviceaccount:argo-events:")` alongside it, still passes. Allow expressions are OR'd, so either would open the route.
- Nothing checks that the JWT provider's issuer, audiences and JWKS match `MANAGER_OIDC_ISSUER` and `AGENTGATEWAY_AUDIENCE`.
- Nothing checks that the policy's `targetRefs` attach to this route. A policy attached to nothing still passes.
- Only `rules[0]` and `matches[0]` are inspected. An extra rule with a `PathPrefix /` match passes.
- The `backendRefs` (must be `kagent-controller:8083`), `parentRefs` and the ReferenceGrant's scope are never checked.

**Fix:** Assert the structure exactly:
- one rule, one match, one backendRef;
- exactly one match expression, equal to `jwt.sub == "system:serviceaccount:argo-events:cluster-health-investigation-workflow"` (and preferably also `jwt.iss == <issuer>`);
- one provider whose issuer, audiences and JWKS equal the rendered values;
- `targetRefs` equal to this HTTPRoute;
- the ReferenceGrant `to` names only the controller Service.

### 6. [High] The RBAC checks use a denylist, and wildcards get through
**Where:** `scripts/verify.py:125-131`

**Evidence:**
- A rule like `apiGroups:["*"], resources:["*"], verbs:["get","list","watch"]` passes, yet grants Secrets and ConfigMaps.
- `verbs:["*"]` passes.
- `pods/proxy`, `services/proxy` and `nodes/proxy` with `get` pass.
- The node-read ClusterRole and its ClusterRoleBinding are never checked offline, so "narrow node-read only" is unproven.
- RoleBinding subjects are only checked for `kind == ServiceAccount`. Name and namespace are not compared to `AKS_MCP_SERVICE_ACCOUNT_*`.

**Fix:**
- Compare against an exact allowlist of apiGroup/resource/verb tuples, and reject `*`, `nonResourceURLs` and any `*/proxy` resource.
- Require the node role to be exactly `[{apiGroups:[""],resources:["nodes"],verbs:["get","list","watch"]}]`, with one ClusterRoleBinding and one subject.
- Check that subject name and namespace equal the configured values.

### 7. [Medium] The authorization boundary is the ServiceAccount, not the Workflow
**Where:** `manager/argo.yaml:153-160`, `AUTHENTICATED-ACCESS` (not in the diff)

**Evidence:** Anyone who can do any of the following in `argo-events` can mint a token with the right audience and call the agent:
- create Workflows or Pods with `serviceAccountName: cluster-health-investigation-workflow`;
- `create serviceaccounts/token` on that ServiceAccount.

The live script does not inventory who holds these permissions.

**Fix:**
- Move the investigation Workflow to a dedicated namespace, or set `workflowRestrictions.templateReferencing: Strict` on the Argo controller.
- Add live gates listing who can `create pods`, `create workflows` and `create serviceaccounts/token` in that namespace, and fail on any unexpected subject.
- Document this residual risk.

### 8. [Medium] The live gates have no positive control and an incomplete inventory
**Where:** `scripts/verify-running.sh:124-148`, `:36-58`

**Evidence:**
- The 401 readiness loop and the 403 test using the `default` ServiceAccount would both pass if the gateway denied everything, or if a Gateway-level policy returned 401 on all paths. That doesn't prove "the Workflow reaches only the fixed agent" (QUICKSTART step 5).
- There are no scripted checks for GET, a path suffix, or the old `/api/a2a/...` path, even though the TEST-PLAN lists them.
- There is no cross-issuer test (a worker-cluster token for the same ServiceAccount name and audience).
- There is no inventory of other AgentgatewayPolicies attached to the Gateway, whose Allow rules could be merged in.
- RBAC is spot-checked in only the first namespace plus `default`.

**Fix:**
- Positive control: POST a harmless JSON-RPC `tasks/get` for a nonexistent ID with a correct token, and expect a JSON-RPC error rather than 401 or 403 (this doesn't invoke the model).
- Assert 404 or 405 for GET, the suffix variant and the old path.
- Assert 401 for a worker-issued token.
- List every AgentgatewayPolicy that targets the Gateway or route.
- Loop over `kubectl get ns` and assert `can-i get pods` is `yes` exactly when the namespace is in the inventory.

### 9. [Medium] Whole files are now exempt from the public-safe scan
**Where:** `public-safe-scan.allowlist:22-24`

**Evidence:** The exemption covers all of `argo.yaml`, `verify-running.sh` and `TEST-PLAN.md`, which are the files holding the security configuration, just to allow one header line. A real token or private endpoint added to any of them later would not be caught.

**Fix:** Remove the three entries. Avoid the literal header in code, for example:
```bash
printf 'Authorization: Bearer %s\n' "$(cat /var/run/secrets/agentgateway/token)" | curl -H @- ...
```
Or add pattern-scoped allowlisting to `verify.py`.

## Non-blocking

### 10. [Medium] The split-cluster MCP identity guidance is contradictory
**Where:** `WORK-AGENT-START-PROMPT.md:78`, `scripts/verify.py:115`

**Evidence:**
- The prompt says "in-cluster context only," but a manager-hosted AKS-MCP running in-cluster reads the **manager** cluster.
- The worker RoleBinding's ServiceAccount subject only authenticates if the MCP server runs on the worker. In that case the manager → worker MCP endpoint has no ingress policy or authentication in this diff.
- `verify.py` hard-requires a ServiceAccount subject, which blocks the Entra-identity mapping a split topology would need.

The known limitation discloses this, but the work-agent prompt still reads as portable.

**Fix:**
- In the prompt, say to stop unless AKS-MCP is colocated on the worker.
- Add an MCP Service ingress NetworkPolicy that admits only the agent path.
- Parameterise the subject kind.

### 11. [Medium] Prompt injection could leak the MCP token through kubectl flags
**Where:** `manager/argo.yaml:248`, `manager/agent.yaml:98`

**Evidence:** Alert text is embedded in the prompt, and `call_kubectl` passes arguments through. A crafted alert could steer a call such as `--server=https://attacker`, `--token`, `--kubeconfig` or `get --raw`. Nothing in the diff limits the MCP pod's egress or proves AKS-MCP rejects these global flags.

**Fix:**
- Add an MCP pod egress NetworkPolicy allowing only the worker API CIDR and DNS.
- Add a TEST-PLAN case confirming AKS-MCP rejects `--server`, `--token`, `--kubeconfig`, `--as` and `--raw`.

### 12. [Low] Token handling in the Workflow step is fragile
**Where:** `manager/argo.yaml:155,250-252`

**Evidence:**
- `test -s` succeeds on an unreadable file. With mode 0400 in multi-container Argo pods, the token can be root-owned. `$(cat)` then fails without aborting the script, and curl sends an empty bearer.
- The token also appears in curl's argv.

**Fix:**
- Use `test -r`.
- Pipe the header through `-H @-` (see finding 9).
- Set pod-level `runAsUser`/`fsGroup` in the template.

### 13. [Low] The new Sensor Role's sufficiency is unproven
**Where:** `manager/argo.yaml:~103-111`

**Evidence:** With `workflowTemplateRef` validation, an `argoWorkflow`/`argo submit` trigger may also need `get` on workflowtemplates. The Role grants only `create` and `get` on workflows, and the live script has no `can-i` check for the Sensor ServiceAccount.

**Fix:** Add `can-i` gates for the Sensor ServiceAccount and a trigger smoke test to `verify-running.sh`.

### 14. [Low] `values.example.json` and payload-pinning nits
- **`values.example.json:8`:** the ServiceAccount name `aks-mcp` is probably the chart's default ServiceAccount, which carries the broad binding. Use `aks-mcp-cluster-health`, matching the fixture.
- **`values.example.json:34`:** AKS issuer URLs end in `/`, so `{{MANAGER_OIDC_ISSUER}}/openid/v1/jwks` becomes `//openid`. Use a separate placeholder.
- **`values.example.json:2`:** the `api://{{AGENTGATEWAY_APP_ID}}` audience suggests an Entra app, but the credential is a Kubernetes ServiceAccount token. Clarify in the docs.
- **`manager/argo.yaml:211`:** `.cluster.mcp_target` is not pinned to `MCP_CLUSTER_TARGET`. Pin it so an invalid target fails validation, as the TEST-PLAN expects.

## Acceptance criteria
- **Criteria 1, 2, 5:** unverifiable (finding 1), and the verifier doesn't prove them (5, 6).
- **Criterion 3:** broken (2) and bypassable (3, 4).
- **Criterion 4:** met (`call_az` removed).
- **Criterion 6:** partly met (8).
- **Criterion 7:** weakened by the scan exemptions (9).
- **No-deployment claim:** met; the live gates are clearly marked NOT RUN.

REVIEW_STATUS: REVISE
