# Kagent and agentgateway tenant isolation bundle

This bundle rehearses a platform-owned agent front door for two application teams, one platform-owned Agent Substrate specialist, and one hostile peer namespace. It therefore demonstrates both ordinary kagent Declarative Agents with MCP tools and a snapshot-backed SandboxAgent through the same agentgateway policy plane.

The platform owns the shared Gateway, HTTPRoutes, AgentgatewayBackends, AgentgatewayPolicies, ReferenceGrants, RBAC, admission policy, and NetworkPolicies. Application teams own their Agent, prompt fragments, skill source, MCP Deployment, and MCP Service. A custom application-editor Role is used instead of Kubernetes' built-in `admin` role because the built-in role can delegate RBAC.

## Pinned releases

| Component | Pin | Release evidence |
| --- | --- | --- |
| agentgateway | `v1.5.0` | https://github.com/agentgateway/agentgateway/releases/tag/v1.5.0 |
| kagent | `v0.10.1` | https://github.com/kagent-dev/kagent/releases/tag/v0.10.1 |
| Agent Substrate workplace target | `v0.0.9` | https://github.com/kagent-dev/substrate/releases/tag/v0.0.9 |
| Gateway API | `v1.6.2` experimental install | https://github.com/kubernetes-sigs/gateway-api/releases/tag/v1.6.2 |

The checked chart digests are recorded in `platform/versions.lock`; the installer pulls each chart and refuses to continue unless the OCI manifest digest matches the lock.

## Red result

The final integrated `red` run at `2026-09-16T18:44:09Z` passed every implemented gate. Both application-team A2A-to-MCP paths completed and incremented only their own MCP counters. The authenticated Substrate path returned the required security-review headings, then suspended its actor with a new snapshot. The rogue namespace was denied at JWT, tool, network, RBAC, admission, Pod Security, and ReferenceGrant boundaries. The durable receipt is `evidence/red/2026-09-16-summary.tsv`; `evidence/red/2026-09-16-runtime.md` records the live versions and limits.

## Use cases

`team-event` receives a dummy incident webhook from a labelled in-cluster event-source Pod. Its adapter calls the `incident-adviser` A2A route. The Agent must use the `lookup_incident` MCP tool before answering. A real external event source needs an organization-approved ingress, TLS, and caller-authentication layer; the bundle deliberately does not expose the adapter publicly.

`team-chat` accepts an interactive A2A prompt. Its `release-adviser` Agent must use the `lookup_release` MCP tool before answering.

The `substrate-a2a` listener exposes only the platform-owned `kagent/machinist-security-review` SandboxAgent. The specialist restores an isolated actor from its golden snapshot, answers with a fixed review contract, and suspends it to a new snapshot. It deliberately has no MCP tool: this lane demonstrates yesterday's Agent Substrate lifecycle beside the two tenant MCP use cases without giving application teams ownership of the shared sandbox controller.

`team-rogue` has its own application-editor identity. It has no accepted route, usable cross-tenant claim, ReferenceGrant, or direct network path. The verification suite attempts real API and data-plane bypasses from that identity.

Red currently runs the historical shared kagent `0.10.0-beta7` and Substrate `0.0.8` pair for this specialist. The standalone workplace target remains kagent `0.10.1` plus Substrate `0.0.9`, as validated by the 2026-09-15 credential-free canary. The bundle does not claim that red is a live 0.10.1/0.0.9 integrated pair.

## Run on a disposable or rehearsal cluster

The `red` profile installs parallel controller releases but shares cluster-scoped CRDs. Read `RED-RUNBOOK.md` before applying it.

For a completely new cluster, do not use the red upgrade path. Start with
[`profiles/fresh-cluster/README.md`](profiles/fresh-cluster/README.md) and hand
[`profiles/fresh-cluster/WORK-AGENT-PROMPT.md`](profiles/fresh-cluster/WORK-AGENT-PROMPT.md)
to the deployment agent. That profile creates the cluster baseline, pins the
six Helm charts, preserves non-overlapping kagent controller ownership, and
keeps the Agent Substrate workplace promotion gates explicit.

```sh
./scripts/preflight.sh red
./scripts/render.py --profile red
./scripts/install-control-planes.sh red
./scripts/deploy.sh red
./scripts/verify.sh red
```

Rendered files go to `.rendered/`. Generated signing material and raw cluster receipts go to operating-system temporary directories by default. Set `TENANT_EVIDENCE_DIR` to an approved external evidence location when the raw receipts must be retained. Only manually curated, sanitized receipts belong under `evidence/red/`; no private key or bearer token is written under the bundle.

## Team workflow

Each legitimate team changes only its directory under `teams/`:

1. Edit `prompt.yaml` to change role, safety rules, and local context.
2. Edit the `Agent` metadata, A2A skill card, and selected tool name in `agent.yaml`.
3. Replace the dummy MCP image and Service in `workload.yaml`.
4. Put executable skill content under `skill/`, publish it as an OCI artifact, and pin its digest in `spec.skills.refs` when a registry is available.
5. Submit the files and the small platform contract change for review.

The example keeps the executable skill reference disabled because the rehearsal has no approved OCI registry. The prompt fragments and A2A skill metadata are live. `a2aConfig.skills` advertises capabilities but does not load executable skills.

## Authentication profiles

The red profile uses a disposable RSA key and short-lived JWTs. It proves strict issuer, audience, claim, and signature enforcement without claiming Entra parity.

The AKS overlay in `profiles/aks-entra/` follows the native Entra MCP discovery pattern for interactive MCP clients, including the MCP and two OAuth discovery route matches. Kagent-to-MCP is a service-to-service call, so it uses a separately acquired workload token. Native MCP OAuth discovery does not mint or refresh that runtime token. The official distinction is documented at https://agentgateway.dev/docs/kubernetes/latest/documentation/mcp/auth/setup/ and the Entra configuration is documented at https://agentgateway.dev/docs/kubernetes/latest/documentation/mcp/auth/entra/.

`profiles/aks-entra/substrate-a2a-policy.yaml` gives the specialist a separate Entra application role and A2A audience. The red disposable JWT profile proves the equivalent issuer, audience, subject, tenant, and purpose checks; it is not evidence of a live workplace Entra flow.

## Security contract

- Every public route has strict JWT validation and claim authorization.
- A2A and MCP use different audiences and subjects.
- Each MCP backend uses one typed Service reference and fails closed.
- MCP tool authorization names the one dummy tool each team is allowed to call.
- Routes live with their policies in the platform namespace. Team roles cannot mutate them.
- Cross-namespace backend references require exact ReferenceGrants.
- Team namespaces start with default-deny ingress and egress.
- Direct Agent, kagent controller, and MCP Service access is denied by NetworkPolicy.
- `RemoteMCPServer` URLs are platform-created and point only at the team's gateway listener.
- Native ValidatingAdmissionPolicy constrains team-owned RemoteMCPServer and Agent cross-namespace references, permits only Declarative Agents in the shared lane, and reserves kagent-managed Deployment and Pod labels for the relevant controllers. A Kyverno alternative is described in `ARCHITECTURE.md` but is not used on red because its Kyverno webhooks are inactive.

`ReferenceGrant` authorizes a typed cross-namespace reference. It is not runtime authentication. `allowedNamespaces` on kagent resources controls CR references. It is not a network boundary.

## Evidence standard

An Accepted resource is not a working path. A rejected request is not proof that the backend was untouched. The verifier records exact resource counts and conditions, HTTP status, response body category, total MCP request counters, allowed and forbidden tool counters, RBAC denials, and direct-Service timeouts with a positive control.

See `ARCHITECTURE.md` for the selected design and `TEST-MATRIX.md` for the full expected proof.

Use `AKS-SUBSTRATE-PROMOTION.md` with `profiles/aks-entra/README.md` when moving the integrated design from red to AKS.
