# Restrict which Pods can reach agentgateway and its backends

This is a **desired-state and verification contract** for in-cluster traffic. It
extends the [tenant-isolation rehearsal](../PHASE1-WORK-EVIDENCE.md); it is not a
receipt from the work cluster. The examples in [`examples/`](examples/) are
sanitized design inputs, **not apply-ready overlays**. Check the installed CNI,
Cilium CRDs, gateway Pod labels and ServiceAccounts, listener ports, and all
existing policies before turning them into private GitOps changes.

## Why add this layer?

The red lab deliberately let a rogue Pod reach the gateway so gate `N09` could
prove JWT rejection. It already used default-deny team namespaces and blocked
direct MCP/controller calls. The current [renderer](../scripts/render.py) does
**not** make the dedicated gateway data-plane Pods reachable only by selected
callers. Its Agent egress rule also selects the whole gateway namespace rather
than the named gateway Pods. A work deployment can narrow both, while retaining
JWT denial tests from an *admitted* source.

Network policy answers **which Pod identity may open a connection to which Pod
and port**. Agentgateway still answers **which signed token, A2A route, MCP
identity, and MCP tool may be used**. A gateway `401` or `403` means the packet
reached the gateway; it is not evidence of network denial.

## Desired state

| Connection | Network allow | Everything else |
| --- | --- | --- |
| Caller application → A2A listener | Exact caller namespace and dedicated ServiceAccount to the dedicated gateway Pods on its A2A port (event example `8081`) | Other namespaces, ServiceAccounts, listeners and direct Agent/Controller paths denied |
| Agent/token holder → MCP listener | Exact agent namespace and dedicated ServiceAccount to the same gateway Pods on its MCP port (event example `8082`) | Other Pods and listener ports denied |
| Gateway → Agent | Platform gateway Pod identity to the approved Agent Pod on its service port (`8080` in the direct-route AKS pilot) | Other sources denied; any required kagent controller traffic has a separate, named rule |
| Gateway → MCP | Platform gateway Pod identity to the approved MCP Pod on port `8080` | Other sources and direct Service calls denied |

The gateway namespace has default-deny ingress for the dedicated gateway Pods.
Every team namespace has default-deny ingress and egress, followed by explicit
allows for required DNS, Entra/JWKS, model, controller/session, A2A, and MCP
flows. The platform owns the Gateway, policies, listener ports and reserved
access labels, and approves which workloads may use privileged ServiceAccounts.
A namespace administrator must not be able to create a Pod using an approved
ServiceAccount or copy a reserved label to obtain network access. Admission
must check Pods **and controller Pod templates**, including
Deployments; the existing [label-spoof gate `N18`](../TEST-MATRIX.md) shows why.

Use **namespace + dedicated ServiceAccount + port** as the primary Cilium
selector. A second, platform-protected Pod label may make the role legible, but
the label alone is not a trustworthy identity if a tenant can set it. Standard
Kubernetes NetworkPolicy can select only Pod and namespace labels; it cannot
select annotations or a ServiceAccount. Cilium exposes a ServiceAccount-derived
endpoint label for its policy selectors. An annotation such as
`azure.workload.identity/client-id` configures identity acquisition; it is not
a network selector. See the [Kubernetes NetworkPolicy guide](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
and [Cilium's ServiceAccount selector example](https://docs.cilium.io/en/stable/security/policy/kubernetes/).

## Example configuration

- [`examples/cilium-networkpolicies.yaml`](examples/cilium-networkpolicies.yaml)
  contains four namespaced Cilium policies: approved caller → A2A listener,
  approved agent → MCP listener, gateway → Agent, and gateway → MCP. It is the
  preferred shape **if** Cilium policy CRDs and ServiceAccount endpoint labels
  are available in the target AKS cluster.
- [`examples/portable-networkpolicies.yaml`](examples/portable-networkpolicies.yaml)
  shows the Kubernetes NetworkPolicy fallback, including a gateway ingress
  default deny. Its access labels require an enforced platform-owned admission
  rule; otherwise any Pod creator could imitate an approved caller.
- [`examples/mcp-serviceaccount.yaml`](examples/mcp-serviceaccount.yaml) is the
  proposed dedicated MCP ServiceAccount. The private Deployment overlay must
  also set `spec.template.spec.serviceAccountName: incident-tools`.

In Cilium's normal policy-enforcement mode, a gateway endpoint selected by
these ingress policies becomes default-deny for other ingress. Verify the
installed mode is `default` or `always`, not `never`, and audit every other
allow rule that selects the endpoint; Cilium allow rules combine. See
[policy enforcement modes](https://docs.cilium.io/en/stable/security/policy/intro/).

The Cilium examples assume these deliberate workload changes:

```yaml
# Illustrative Pod-template fields, not a complete Deployment.
# The existing event-adapter already uses a dedicated ServiceAccount.
spec:
  serviceAccountName: event-adapter
---
# Give the MCP Deployment a new dedicated ServiceAccount instead of default.
spec:
  serviceAccountName: incident-tools
---
# The approved Agent/token-holder ServiceAccount must be confirmed from
# the installed kagent-generated Pod, not guessed from the Agent CR name.
spec:
  serviceAccountName: "{{AGENT_SERVICE_ACCOUNT}}"
```

Create the `incident-tools` ServiceAccount as a platform-reviewed object, set
`serviceAccountName` on the MCP Deployment, and verify the gateway data-plane
ServiceAccount and actual Pod labels. Replace
`{{GATEWAY_SERVICE_ACCOUNT}}` and `{{AGENT_SERVICE_ACCOUNT}}` in a private
overlay. Restrict who can select these ServiceAccounts, change the gateway
namespace, edit network policy, or set reserved labels. The existing lab MCP
Deployment uses the `default` ServiceAccount, so the proposed Cilium MCP
policy would not select it until that change is made.

**Complete the egress half before promotion.** Narrow caller egress to the
gateway Pod identity and its A2A port; narrow agent egress to the gateway Pod
identity and MCP port; narrow gateway egress to the Agent/MCP targets. Preserve
the exact additional dependencies used by each workload (DNS, Entra token
endpoint and JWKS, model gateway, kagent session/controller, metrics and health
checks). The examples focus on ingress to avoid inventing an environment's
egress contract. Applying an incomplete default-deny egress policy can break
token acquisition or the agent session path; the [AKS pilot](../poc/azure-agent-id/AKS-FULL-E2E-EVIDENCE-2026-09-25.md)
found that omission in its first run.

## Verify the result on the target cluster

First read back the actual gateway Pod labels/ServiceAccount, the caller and
backend Pod identities, all Gateway listener ports, and **every**
`NetworkPolicy`, `CiliumNetworkPolicy`, and cluster-wide Cilium policy selecting
them. Allow rules are additive: one broader allow can reopen a path that a
narrower policy appears to close. Check the rendered GitOps diff and server
dry-run against the installed CRDs, then test from real workload Pods or a
controlled probe with the exact same namespace, ServiceAccount and labels.
Do not use a generic debug Pod and assume it represents the real caller.
Compare the complete running-Pod inventory against the owner-approved allowlist:
every Pod identity outside it must have no permitted path to a gateway listener.

```bash
kubectl get pods -A -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,SA:.spec.serviceAccountName,LABELS:.metadata.labels'
kubectl get networkpolicy -A
kubectl get ciliumnetworkpolicy -A
kubectl get ciliumclusterwidenetworkpolicy
```

Run the Cilium commands only where those CRDs are installed. Inspect the
gateway Service's exposure and the observed source identity too: an external
load balancer, node or mesh proxy may not appear as the original caller Pod.

| Gate | Probe | Expected observation |
| --- | --- | --- |
| `NET-01` | Approved caller to its A2A listener with a valid token | TCP connects, gateway accepts, named Agent responds |
| `NET-02` | Same caller, missing/wrong-audience/role token | TCP connects; gateway returns `401`/`403`; Agent counter unchanged |
| `NET-03` | Different ServiceAccount in same namespace to A2A listener | No TCP connection; Cilium policy-drop verdict; no gateway request |
| `NET-04` | Same ServiceAccount name in another namespace | Network denied; namespace is part of the identity match |
| `NET-05` | Pod copying the approved *ordinary* label but using a different ServiceAccount | Network denied under the Cilium variant; admission denies any protected-label spoof |
| `NET-06` | Approved caller to wrong listener port | Network denied |
| `NET-07` | Approved agent/token holder to its MCP listener and tool | TCP connects; token/tool policy passes; MCP counter increments once |
| `NET-08` | Other Pod to MCP listener or direct Agent/MCP Service | Network denied; backend counter unchanged |
| `NET-09` | Gateway Pod to the named Agent and MCP backends | Both required connections work; record the full set of backends reachable from this shared gateway identity |
| `NET-10` | Agent session, DNS, Entra/JWKS, model path and monitoring after policy rollout | Required dependencies still work; no fail-open policy gap after restart |
| `NET-11` | Remove one approval in a controlled test, then use a **new** connection | New connection is denied; record policy revision and flow verdict |

Record, per probe: source namespace/Pod/ServiceAccount and relevant labels,
destination Pod/port, Cilium `FORWARDED` or `DROPPED` verdict, gateway HTTP
decision where reached, and Agent/MCP backend counter. Never record raw access
tokens. Hubble can show the network verdict, for example:

```bash
hubble observe --pod tenant-gateway-system/{{GATEWAY_POD}} --since 5m
hubble observe --pod tenant-gateway-system/{{GATEWAY_POD}} --verdict DROPPED
```

Check Hubble availability and the installed CLI syntax first; see [Cilium's
Hubble CLI guide](https://docs.cilium.io/en/stable/observability/hubble/hubble-cli/).
A timeout alone could be DNS, routing, or policy failure. Pair it with a
policy-drop verdict and an admitted positive control. A `401`/`403` proves
gateway reachability and belongs to the **JWT** test, not `NET-03`–`NET-06`.
On clusters where a load balancer or mesh changes the observed source, validate
the actual in-cluster path separately from external ingress.

## Definition of done

The platform and CNI owners can sign off when the approved source inventory
matches the effective policy, `NET-01`–`NET-11` pass with recorded Cilium and
gateway/backend evidence, all necessary control-plane/model/identity flows
remain healthy, and a newly created unapproved Pod cannot acquire access by
copying labels or choosing an approved ServiceAccount. Re-run the gate after a
gateway upgrade, listener/route change, new tenant onboarding, or policy
change. Keep the exact identities, token claims and runtime receipts in the
approved private system rather than this public repository.

## Limits and promotion decision

One shared gateway data plane has one network identity and legitimately reaches
multiple approved Agent/MCP backends. Network policy can restrict which Pods
reach that gateway and which backend Pods accept it; it cannot infer which
HTTPRoute or MCP tool a request should use. Keep the exact HTTPRoutes,
ReferenceGrants, JWT role-and-object-ID checks, and MCP tool policy. If the
requirement is **separate gateway-to-backend network identity per team**, use
separate platform-owned gateway data planes/ServiceAccounts per trust boundary
and retest the operational cost.

This design becomes a work-cluster claim only after the identity and policy
read-backs, the complete positive/negative matrix, and Cilium flow evidence
pass on that cluster. The red lab's `N09` result remains a valid JWT test for
its original topology; it is not evidence that only selected Pods could open a
connection to the gateway.
