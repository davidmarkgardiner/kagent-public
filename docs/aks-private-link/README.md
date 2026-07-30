# AKS + Azure Private Link

Notes and a verified reference architecture for exposing applications running in AKS privately —
to other VNets, other subscriptions, other tenants, and to Azure Databricks — with **no public endpoint**.

Verified against Microsoft Learn as of **2026-07-30**.

## Verdict

**Deployable today with first-party Azure services only.** No custom components, no third-party products,
nothing to build. Traffic is **not** dropped after five minutes — the timers on the path are *idle*
timeouts, not lifetime caps, and active connections stay up indefinitely (see trap 4).

Not yet validated live. Every claim is sourced to Microsoft Learn, but a small proof-of-concept — one PLS,
one Databricks NCC rule, one query end to end — is what turns this from sourced to proven.

## TL;DR

- The pattern is **Private Endpoint → Private Link Service (PLS) → Standard internal load balancer → Istio ingress gateway → Pods**.
- It is **100% first-party Azure**. No open-source or third-party product is required for the network path. The PLS is created declaratively from Kubernetes via `service.beta.kubernetes.io/azure-pls-*` annotations.
- **Azure Databricks serverless can consume a customer PLS** via a Network Connectivity Configuration (NCC) private endpoint rule, so Databricks jobs, notebooks, SQL warehouses and model serving can call an AKS-hosted API privately.
- **PLS is L4** (TCP/UDP, IPv4). Host/SNI routing belongs to Envoy/Istio, not to Private Link.
- Control plane and data plane are separate problems. A private cluster does not make your apps private, and private apps do not require a private cluster.

## Read this first

**[REVIEW.md](./REVIEW.md)** — the verified deep dive. Contains:

| Section | Contents |
|---|---|
| §1–2b | Correction tables for each draft below — 27 errors and material omissions, each with the authoritative source |
| §3 | Diagrams: control plane vs data plane, target Databricks→AKS architecture, build-order sequence |
| §4 | Provider-side build — the four supported ways to attach a PLS, with working YAML |
| §5 | Databricks specifics — the three traffic directions, NCC constraints, and Databricks-shaped gotchas |
| §6 | First-party vs open-source component breakdown |
| §7 | Recommended architecture + pre-flight checklist |
| §8 | Candidate automated validation checks (proposals, not built) |

## Drafts

Working notes. Each contains errors corrected in `REVIEW.md` — read the review alongside them.

| File | Topic |
|---|---|
| [rm.md](./rm.md) | The four AKS private-connectivity patterns, multi-subscription and cross-tenant, DNS at scale |
| [isito.md](./isito.md) | Where Private Link terminates relative to the AKS Istio add-on; TLS options; multi-cluster |
| [pls.md](./pls.md) | Disambiguates "PLS Gateway"; establishes that SNI/Host routing belongs in Envoy. Most accurate of the three |

## The traps worth knowing before you start

1. **`azure-load-balancer-internal` alone does not create a PLS.** You also need `service.beta.kubernetes.io/azure-pls-create: "true"`. Nothing creates a PLS implicitly.
2. **Private-use TLDs are rejected by Databricks.** `.internal`, `.localhost`, `.test` are not accepted in NCC private endpoint rules. Use a registered domain in a private DNS zone.
3. **PLS is unsupported when the AKS load balancer backend pool type is `nodeIP`.** Stay on the default `nodeIPConfiguration`. The incompatibility is silent.
4. **Idle timeouts — worth understanding, not worth fearing.** These are *idle* timeouts, not connection lifetime caps: they only close sockets where no data has flowed either way for the window, and active traffic resets the timer continuously. Request/response, pooled and streaming traffic never hit them. The real risk case is a long-running request where the server computes silently for minutes, so the socket *looks* idle. Two timers apply, and the load balancer's is tighter at defaults — LB rule **4 minutes (240s)**, tunable via `azure-load-balancer-tcp-idle-timeout`; PLS **~5 minutes (300s)**, **fixed**. Design against ~240s. Every fix is managed-service config — client pool idle eviction below the timeout, app-level keepalive, raise the LB annotation, enable TCP reset, retry idempotent calls on reset. Nothing to build; document it in consumer onboarding.
5. **No DNS zone is created for you.** Azure PaaS private endpoints get DNS integration free; customer-PLS private endpoints do not. You own the A record → private endpoint IP, per consumer VNet, for its lifetime.
6. **The source IP is always the PLS NAT IP.** Recovering the real client IP needs PROXY protocol v2, which breaks any backend — including health probes — that does not parse it. Derive identity from mTLS or JWT, not from the network.
7. **`azure-pls-*` is not in the Istio add-on's documented annotation set** for its managed ingress gateway Service. Use Gateway API `spec.infrastructure.annotations`, a self-managed gateway Service, or create the PLS out-of-band. See §4.

## Not candidates today

- **Application Gateway for Containers** — public frontends only; no private/internal frontend, no Private Link support.
- **Cilium Gateway API on managed AKS** — Azure CNI Powered by Cilium does not expose Gateway API; AKS owns the config. Requires BYO CNI.
- **ingress-nginx** — upstream maintenance ended March 2026; the AKS application routing add-on's NGINX is patched by Microsoft through November 2026 only.
- **Azure Front Door** — supports AKS internal load balancers as a private-link origin, but Front Door is a public edge and does not support mTLS to private-link origins. Wrong tool for Databricks→AKS.

## Scope

Documentation review and architecture design. **No live Azure validation was performed** — every claim is
sourced to Microsoft Learn or `cloud-provider-azure` docs, cited inline in `REVIEW.md`. The validation
checks in §8 are proposals, not implemented tooling.
