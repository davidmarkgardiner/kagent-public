# Agent platform work stream — start here

Three capabilities, in the order they should be proven on a work cluster:
Agent Substrate, then agent and MCP isolation behind agentgateway, then Entra
identity. Each step has a receipt from the home lab; none has been run on a
work cluster yet.

| Step | Bundle | Status |
|---|---|---|
| 1. Install kagent and Substrate, hardened for admission safeguards | [`agent-substrate/aks-hardened/`](agent-substrate/aks-hardened/README.md) | Boot-tested on kind; includes a proof-of-concept path that skips the optional parts |
| 2. Prove Substrate: suspend, restore and session memory | [`agent-substrate/demo/`](agent-substrate/demo/README.md) | One script, all 9 checks passed on the home lab 2026-09-22 |
| 3. Prove isolation: teams' agents and MCP servers behind agentgateway | [`kagent-agentgateway-tenant-isolation/PHASE1-WORK-EVIDENCE.md`](kagent-agentgateway-tenant-isolation/PHASE1-WORK-EVIDENCE.md) | 38 gates passed on the home lab 2026-09-16 |
| 4. Add Entra identity, with Agent ID as the target | [`kagent-agentgateway-tenant-isolation/profiles/aks-entra/LOCAL-REHEARSAL.md`](kagent-agentgateway-tenant-isolation/profiles/aks-entra/LOCAL-REHEARSAL.md) | Real Entra tokens proven locally and end to end through kagent 2026-09-22; **Entra Agent ID identities proven against the same policy 2026-09-23** ([`AGENT-ID-REHEARSAL.md`](kagent-agentgateway-tenant-isolation/profiles/aks-entra/AGENT-ID-REHEARSAL.md)) |
| 5. Self-service onboarding for teams | [`kagent-agentgateway-tenant-isolation/ONBOARDING-AUTOMATION-SPIKE.md`](kagent-agentgateway-tenant-isolation/ONBOARDING-AUTOMATION-SPIKE.md) | **Plan only. Not built.** |

Steps 3 and 4 need agentgateway, which this bundle configures through Gateway
API objects. Where the AKS Istio add-on is enabled those CRDs already exist, so
the step is installing agentgateway only — see "When Istio already owns the
Gateway API CRDs" in the evidence sheet before touching anything cluster-wide.

Steps 2 and 3 are **already built, run and recorded** in the home lab, with a
published video each. The work is repeating them in the work environment, not
designing them:

| | Video | Runbook to follow | Evidence to match |
|---|---|---|---|
| Substrate | https://www.youtube.com/watch?v=3BTzlDPiVfk | [`agent-substrate/demo/`](agent-substrate/demo/README.md), one script | [`agent-substrate/evidence/LIVE-RUN-2026-09-14.md`](agent-substrate/evidence/LIVE-RUN-2026-09-14.md) |
| Isolation | https://www.youtube.com/watch?v=eAJpU-oWUdg | [`kagent-agentgateway-tenant-isolation/RED-RUNBOOK.md`](kagent-agentgateway-tenant-isolation/RED-RUNBOOK.md): preflight, install, render, deploy, verify | [`.../evidence/red/2026-09-16-summary.tsv`](kagent-agentgateway-tenant-isolation/evidence/red/2026-09-16-summary.tsv), 38 gates |

Read [`PHASE1-WORK-EVIDENCE.md`](kagent-agentgateway-tenant-isolation/PHASE1-WORK-EVIDENCE.md)
first: it maps each question a reviewer will ask onto the gate that answers it,
and says which Gateway API version is actually required.

## What is not proven

- **Nothing has run on a work cluster.** Every receipt is from the home lab or
  a local kind cluster.
- **Entra at work:** no corporate tenant, app registrations, conditional
  access, PKCE with real users, token refresh across expiry, public hostname
  or external TLS. Whether the cluster can reach `login.microsoftonline.com`
  for JWKS is the first thing to check.
- **Onboarding automation:** step 5 is a plan. Provisioning a team's identity
  and lane is manual today.
- **`infra/byo-kagent/`** is a target-state proposal, not deployed or
  runtime-enforced. The isolation gates were proven with the tenant-isolation
  bundle's own policies.

## Images to mirror

[`agent-substrate/IMAGES.md`](agent-substrate/IMAGES.md) covers steps 1 and 2:
the minimum for kagent plus Substrate, with digests, split into required and
optional.

Steps 3 and 4 additionally need the following, which that list does not cover.
Digests resolved 2026-09-22; re-resolve before mirroring.

| Component | Image | Digest |
|---|---|---|
| agentgateway data plane | `cr.agentgateway.dev/agentgateway:v1.5.0` | `sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896` |
| agentgateway controller | `cr.agentgateway.dev/controller:v1.5.0` | `sha256:319489cb86b7f901a52a3fc532ad07f136c92756f88cf02a4040909e20001120` |
| kagent Python ADK runtime, for ordinary team agents | `ghcr.io/kagent-dev/kagent/app:0.10.1` | `sha256:d39d5c948386a4777f4b704cc151bf5bf193ce85c47a8a8e8642644243197f41` |
| rehearsal fixture | `docker.io/curlimages/curl:8.16.0` | `sha256:463eaf6072688fe96ac64fa623fe73e1dbe25d8ad6c34404a669ad3ce1f104b6` |
| rehearsal fixture | `docker.io/library/python:3.13-alpine` | `sha256:79e7a9b9ff1cbceff819f856fb374477792a5967759d94df266de7b7b4120e6f` |

Gateway API and the agentgateway charts are manifests and OCI charts rather
than images; their pinned versions and chart digests are in
[`kagent-agentgateway-tenant-isolation/platform/versions.lock`](kagent-agentgateway-tenant-isolation/platform/versions.lock).

## Receipts to produce at work

Each step writes its own receipt. Keep them: a work-cluster receipt is what
moves these gates from "proven in a home lab" to "proven here".

1. `verify-render.sh` output, then the install.
2. `run-memory-demo.sh` receipt directory.
3. `scripts/verify.sh` receipt from the isolation bundle.
4. The Entra gate results, using `profiles/aks-entra/entra-tokens.sh`.
