# Phase 1 for the work cluster: what is already proven, and what to re-run

Phase 1 answers two questions: **can a team run its own agent and MCP server
so nobody else can reach them**, and **does Agent Substrate work**. Both were
proven in the home lab. Entra ID is deliberately out of scope; agentgateway
is **in** scope.

This is an evidence sheet, not a plan. The work is re-running it on the work
cluster.

## The two runs behind this

| Run | Date | Environment | Receipt |
|---|---|---|---|
| Tenant isolation, full gate suite | 2026-09-16 | `red`: kagent `0.10.1`, agentgateway `v1.5.0`, **Gateway API v1.4**, Substrate specialist on `0.0.8` | [`evidence/red/2026-09-16-summary.tsv`](evidence/red/2026-09-16-summary.tsv) — 38 gates, all PASS; runtime detail in [`evidence/red/2026-09-16-runtime.md`](evidence/red/2026-09-16-runtime.md) |
| Substrate session continuity | 2026-09-22 | `red`: kagent `0.10.1`, Substrate `0.0.9` | [`../agent-substrate/demo/`](../agent-substrate/demo/README.md) — 9 checks, all PASS |

## Gateway API: you need it, but probably not v1.6.2

**The whole isolation suite passed on Gateway API v1.4.** agentgateway is
configured through Gateway API kinds (`Gateway`, `HTTPRoute`) plus its own
`AgentgatewayPolicy` and backend CRDs, so some Gateway API version must be
installed, but not the pinned experimental one.

The single thing that needed **v1.6.2 experimental** was the Entra route
overlay, which uses the v1.6 experimental CORS filter
(`spec.rules[0].filters[0].cors`). On red that overlay was expected to fail
and did; see [`evidence/red/2026-09-16-entra-schema-dry-run.md`](evidence/red/2026-09-16-entra-schema-dry-run.md).
It belongs with the Entra work in phase 2.

So, first check on the work cluster:

```sh
kubectl get crd gateways.gateway.networking.k8s.io \
  -o jsonpath='{.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}{"\n"}'
kubectl get crd | grep -E 'gateway\.networking\.k8s\.io|agentgateway'
```

If Gateway API is already installed (common where Istio or app routing is in
use), phase 1 adds only the agentgateway CRDs and controller, not a
cluster-wide Gateway API install. If it is absent, install the **standard**
channel at the version your platform team accepts, and keep v1.6.2
experimental as a phase-2 item.

### When Istio already owns the Gateway API CRDs

This is the good case: the prerequisite is met and phase 1 installs only the
agentgateway CRDs and controller. Three things still need care, because those
CRDs are cluster-scoped and now shared.

**Do not apply the v1.6.2 experimental manifest over them.** The
[`../agent-substrate/aks-hardened/`](../agent-substrate/aks-hardened/README.md)
sibling profile and [`profiles/fresh-cluster/README.md`](profiles/fresh-cluster/README.md)
assume an empty cluster, where installing Gateway API is safe. On a cluster
where Istio owns those CRDs, applying a different version or channel is a
cluster-wide change that lands on Istio too. Use what is installed. If the
Entra CORS overlay later needs v1.6.2 experimental, that is a coordinated
change with whoever owns the service mesh, not a step in this bundle.

**Check what the CRDs actually serve**, not just the bundle version:

```sh
kubectl get crd gateways.gateway.networking.k8s.io \
  -o jsonpath='{.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}{"\n"}'
kubectl api-resources --api-group=gateway.networking.k8s.io
```

`entra-jwks.yaml` declares `BackendTLSPolicy` as `gateway.networking.k8s.io/v1`,
which is what red served on v1.4. Older Gateway API versions serve that kind
under an alpha group version, so if the second command shows something else,
change the `apiVersion` in that file to match. ReferenceGrant, which gate
`N13` uses, is standard-channel and present either way.

**Expect two controllers on the same objects.** agentgateway runs with its own
`GatewayClass` (`tenant-agentgateway`) and controller name
(`agentgateway.dev/tenant-isolation`), plus namespace discovery selectors, so
it only reconciles its own Gateway. But `HTTPRoute` and policy status then
carries more than one ancestor, and red already saw this with an older shared
agentgateway controller: the receipt reads the **dedicated controller's status
ancestor**, not the first one in the list. Any status check written at work
must do the same, or it will read Istio's entry and report the wrong answer.

Note that Substrate itself already runs agentgateway as a plain sidecar with a
config file, with no Gateway API involved. That is the `atenet-router` in
[`../agent-substrate/IMAGES.md`](../agent-substrate/IMAGES.md), and it is
unrelated to the front door.

## Tokens in phase 1

Red proved the **disposable JWT profile**: locally issued tokens against the
same five `AgentgatewayPolicy` objects. Phase 2 swaps the issuer for Entra and
adds discovery, PKCE, app roles and token refresh. The policy model, the lane
separation and every rejection below are already proven with real tokens; only
the issuer changes.

kagent ran with `AUTH_MODE=trusted-proxy` behind the authenticated gateway
path. Set `controller.auth.mode: trusted-proxy` when the gateway fronts
kagent. The chart default is `unsecure`, which trusts an `X-User-Id` header
and is only safe when nothing else can reach the controller.

## Question 1: isolated agents and MCP servers

All of these passed on red on 2026-09-16.

**Positive paths — each team reaches only its own backend**

| Gate | Proves |
|---|---|
| `S01`–`S03` | Five dedicated listeners, two MCP backends and five policies all accepted with resolved references |
| `P01` | An in-cluster event source reaches its team's agent and MCP tool; that team's backend counter increments |
| `P02` | The chat team's agent reaches its own MCP tool; its own counter increments |
| `P03` | A valid runtime token reaches only its allowed MCP tool |

**Token boundary — the front door**

| Gate | Proves |
|---|---|
| `N01`–`N03` | No token, wrong audience and expired token are all rejected |
| `N04` | Correctly signed token carrying a rogue tenant claim is rejected |
| `N05`, `N06` | One team's MCP or A2A token is useless on another lane |
| `N07` | A known but un-granted MCP tool is blocked before the backend |
| `N09` | A rogue Pod reaches the policy boundary but never a backend |
| `N17` | Six rejected requests never reached the MCP backend, by counter |

**Network and RBAC boundary — no side doors**

| Gate | Proves |
|---|---|
| `N08` | A rogue Pod calling both teams' MCP Services directly is refused |
| `N15` | A rogue Pod calling the kagent controller directly is refused |
| `N10` | A rogue namespace admin cannot create RBAC, read a cross-team Secret, or mint a token |
| `N11` | A rogue admin cannot create an HTTPRoute |

**Admission boundary — tenants cannot widen their own access**

| Gate | Proves |
|---|---|
| `N12` | An MCP server cannot open itself to all namespaces |
| `N16` | An Agent cannot reference another namespace's MCP server |
| `N13` | A cross-namespace reference without an exact grant stays unresolved |
| `N18` | A tenant cannot forge the reserved kagent label through a Deployment template, which the NetworkPolicy identity selector depends on |
| `N19` | A tenant cannot run an arbitrary image in the shared lane; it is Declarative Agents only |
| `N14` | A privileged Pod in a team namespace is rejected |

## Question 2: Agent Substrate

| Gate | Proves |
|---|---|
| `S04` | SandboxAgent, generated ActorTemplate and WorkerPool healthy: Ready, one golden template, workers 3/3 |
| `P04` | An authenticated call through the fifth listener completes in the Substrate specialist with the required headings |
| `N20`–`N22` | That listener rejects no token, another lane's token, and rogue claims |
| `N23` | A rogue Pod calling the SandboxAgent endpoint directly is refused |
| `S05` | After the call the actor suspends with a **new** external snapshot |
| `T01` | The workplace target contract and image lock are consistent; 16/16 digests resolve |
| Substrate demo `R00`–`P04` | 2026-09-22: marker stored, actor suspends, the same session restores it and returns the marker, a second session gets a different actor |

`R01` additionally showed the 13 pre-existing HTTPRoutes still Accepted after
the shared CRD upgrade — a scoped regression check, not a guarantee for every
pre-existing app.

## Deferred to phase 2

| Item | Why |
|---|---|
| Entra ID issuer, app registrations, API scopes, A2A and MCP app roles | Red has no workplace Entra tenant. `E01` shows the JWKS backend and five JWT policies pass server-side schema validation only. Since then a local rehearsal has proven the same policies against real Entra tokens: [`profiles/aks-entra/LOCAL-REHEARSAL.md`](profiles/aks-entra/LOCAL-REHEARSAL.md) |
| Gateway API v1.6.2 experimental | Only the Entra route overlay needs it, for the v1.6 CORS filter |
| Live discovery, PKCE, app-role denial, workload-token refresh across expiry, external TLS | Needs a real tenant and hostname |

## Order of work at work

1. **Install:** [`../agent-substrate/aks-hardened/`](../agent-substrate/aks-hardened/README.md),
   including its proof-of-concept section. That covers kagent, Substrate and
   the hardening your safeguards require.
2. **Substrate:** run [`../agent-substrate/demo/run-memory-demo.sh`](../agent-substrate/demo/run-memory-demo.sh)
   and keep the receipt. No gateway needed.
3. **Check Gateway API**, as above, and agree the version with the platform
   team.
4. **Isolation:** install agentgateway `v1.5.0`, deploy this bundle's
   rehearsal and run `scripts/verify.sh`. Use the disposable JWT profile, not
   the `aks-entra` overlay. Start from [`AKS-SUBSTRATE-PROMOTION.md`](AKS-SUBSTRATE-PROMOTION.md)
   and [`RED-RUNBOOK.md`](RED-RUNBOOK.md).
5. Keep each receipt. A work-cluster receipt is what promotes these gates from
   "proven in a home lab" to "proven here".

## What this evidence is not

- It is a home-lab result. No gate above has been observed on the work
  cluster.
- The red run used Substrate `0.0.8` for the live specialist. The work target
  is the canaried kagent `0.10.1` plus Substrate `0.0.9` pair.
- `T01` proves the source images resolve, not that they are mirrored or
  admitted in the work registry.
- Isolation here means these tested boundaries. It is not a completed security
  assessment, and suspension is not deletion.
