# Spike: automated identity onboarding for bring-your-own agents

A team wants to bring its own agent and MCP server onto the shared kagent and
agentgateway platform. Today that costs a person: someone creates the Entra
objects by hand, renders a policy and a route, and merges the GitOps change.
This spike is the plan to automate it. **Nothing here is built yet.**

## What is already proven, and what that leaves

| Piece | State |
|---|---|
| The isolation boundary once a lane exists | Proven on `red`, 2026-09-16, 38 gates |
| Microsoft-issued identity enforced by the lane policies | Proven locally and then end to end on `red`, 2026-09-22 ([`profiles/aks-entra/LOCAL-REHEARSAL.md`](profiles/aks-entra/LOCAL-REHEARSAL.md)) |
| Turning a team's request into that lane | **Not built.** Manual `az` plus a hand-rendered policy |
| `infra/byo-kagent/` pipeline | A target-state proposal: CRDs, Kyverno policies and an Argo Events flow, with no controller or renderer proven |

So the runway exists at both ends. The missing middle is provisioning.

## What onboarding a team actually has to produce

The `red` run makes the list concrete. Per team, per lane:

1. **An Entra identity**: an application and service principal for the team's
   client, an app role on the platform API application per lane, and the role
   assignment. The run needed **two** roles for one team, because an agent's
   identity to its own tools is a separate credential from the caller's
   identity to the agent.
2. **A credential**: a client secret, or better a federated credential bound
   to the team's Kubernetes service account, so nothing long-lived is stored.
3. **Gateway objects**: a listener, an `HTTPRoute`, and an
   `AgentgatewayPolicy` carrying that tenant, audience and role.
4. **Cluster objects**: namespace, RBAC, NetworkPolicy, and the
   `ReferenceGrant` for any cross-namespace backend reference.
5. **kagent objects**: the `Agent` or `SandboxAgent`, its `ModelConfig`
   reference, and a `RemoteMCPServer` pointing at the gateway's MCP lane with
   its token.
6. **A receipt**: the positive call plus the negative probes, so the lane is
   demonstrably isolated the day it is created.

## Proposed flow

```
Team PR (request.yaml)
  → validate: schema, naming, requested lanes, quota
  → plan: render the Entra objects and the cluster objects, post the diff
  → approve: platform review, plus identity approval if a new app role is needed
  → provision: Graph API creates app, SP, role assignment, federated credential
  → render: gateway + cluster + kagent manifests into the GitOps repo
  → apply: Flux reconciles; admission enforces the existing guardrails
  → verify: run the lane's gate subset, attach the receipt to the PR
```

The first three steps and the last are ordinary CI. Only **provision** needs a
privileged identity, which is the crux of the design.

## The decision that gates everything: who may create app registrations

Graph needs `Application.ReadWrite.OwnedBy` (or `.All`) and
`AppRoleAssignment.ReadWrite.All`. That is a powerful identity for a pipeline
to hold. Three options, in increasing order of what platform teams usually
accept:

| Option | How it works | Trade-off |
|---|---|---|
| **A. Pipeline service principal** | CI holds a narrow Graph identity and creates apps under its own ownership | Fully automated; a compromised pipeline can mint identities. Pair with owned-by scoping, an approval gate and alerting on every creation |
| **B. Pre-provisioned pool** | Identity team creates N lane identities up front; onboarding assigns a free one | No privileged pipeline; onboarding is instant until the pool empties |
| **C. Ticketed step** | The pipeline renders the exact `az` commands; identity runs them and returns the IDs | Least automated but often the only acceptable answer at first; still removes every hand-authored YAML |

**Recommendation: start at C, design for A.** Make the provisioning step a
single interface with two implementations, so moving from a ticket to a
pipeline identity later changes one component and nothing else.

## Credentials: prefer federation over secrets

A client secret has to be created, stored, rotated and revoked. A **federated
credential** on the team's app, bound to the team namespace's service account
issuer and subject, means the agent Pod exchanges its projected token for an
Entra token with no stored secret at all.

If secrets are unavoidable, the pattern already proven in this repository
applies: Key Vault plus External Secrets, as in
[`../agent-substrate/aks-hardened/byo-secrets/`](../agent-substrate/aks-hardened/byo-secrets/),
never a secret in git.

This spike has tested neither federation for agent Pods nor MCP token refresh.
Both need a proof before they are designed in.

## Offboarding, which is the half that gets forgotten

Onboarding automation is only safe if removal is equally automatic: delete the
role assignment, delete or disable the application, remove the policy, route
and NetworkPolicy, and revoke any issued tokens. Access after a team leaves is
the risk that an approver will ask about first. Build the teardown in the same
change as the provisioning.

## Thin slice to build first

One team, one lane, no UI:

1. `request.yaml` with team, namespace, agent name, MCP service and lanes.
2. A renderer that outputs the gateway, cluster and kagent manifests from that
   request, with a `--dry-run` that only prints the diff.
3. A provisioning interface with the ticketed implementation first: it prints
   the exact `az` and Graph calls, and reads back the resulting IDs.
4. `entra-tokens.sh` (already written) for the verification step.
5. A verifier that runs the lane's gates: the positive call, no token, wrong
   role, cross-lane token, and a direct network probe. It reuses the existing
   `scripts/verify.sh` logic rather than a second implementation.
6. A receipt written next to the request.

Done means: a PR containing only `request.yaml` results in a working,
policy-enforced lane and a receipt, with one human approval and no
hand-authored YAML.

## Open questions for the platform and identity teams

- Which option above for app registration, and who owns the pipeline identity?
- Naming and audience conventions for applications, roles and scopes.
- One platform API application with a role per lane, as the `red` rehearsal
  used, or an application per team? The former keeps audiences simple; the
  latter keeps blast radius smaller.
- Federated credentials or client secrets for agent Pods?
- Which approvals are mandatory, and which can be policy checks in CI?
- Is `Microsoft Agent 365` licensing available, if per-agent Entra Agent ID
  identities are wanted later? Agent ID would replace step 1 of the flow and
  leave the rest intact.
- Where does the request repository live, and does Flux already reconcile it?
