# BLAST-FEEDBACK — Kagent Triage Deployment Models Review

Review of `WORK-KAGENT-TRIAGE-DEPLOYMENT-MODELS.html` against the repo's existing
triage architecture docs, the skeptical-boss security question, and public-safety
rules. This file is the review record for the artifact; the artifact itself is the
HTML page.

---

## 1. What the artifact covers

A single public-safe HTML briefing that contrasts two kagent triage deployment models:

- **Path A — worker-local kagent.** Event fires in the worker cluster, the local
  agent triages it, LLM traffic still egresses through the management-cluster
  agentgateway, and the result lands in GitLab or ServiceNow as the same issue,
  MR, incident, or workflow handoff the central path would create.
- **Path B — management-cluster kagent.** Worker events route through Confluent
  Kafka / Azure Event Hub, Argo Events/Sensor receives them, the management agent
  triages and uses AKS-MCP to reach back into the worker cluster, output to GitLab
  or ServiceNow.

The page has: short verdict, two flow diagrams with a highlight toggle, an
Architecture tab with a side-by-side network/port drawing, a seven-row blast-radius
comparison table, pros/cons, six controls, a recommended position, a copyable boss
briefing, and repo anchors.

---

## 2. Security framing check — does it answer the skeptical boss?

The central concern is "runaway agents and security loopholes." The artifact answers
it with one load-bearing claim, repeated in the header, the blast-radius callout, and
the briefing:

> **Blast radius is permission-bound, not pod-location-bound.**

Specific checks against the brief:

| Requirement | Status | Where |
|---|---|---|
| Do **not** claim worker-local is always safer | Met | Verdict hedges with "can be"; table row 1 shows Path A is only scoped "if RBAC is local and namespace-bound" |
| Path B with central admin AKS-MCP = same destructive reach | Met | Blast-radius callout + Cons list ("Remote AKS-MCP credentials can create the same worker-cluster blast radius") |
| One central UAMI over management-scope clusters = larger aggregate blast radius | Met | Table row 1 "larger if one UAMI reaches every cluster in management scope" + Recommended Position "Do not grant blanket admin" |
| Same GitLab / ServiceNow triage output in both models | Met | Short verdict + Architecture notes + Triage output table row + copyable briefing |
| Path A smaller surface only when read-only, local-intake, not exposed, egress-limited | Met | Path A flow + Pros list + Controls 1/2/4 |
| Write actions via GitLab MR / ServiceNow / Argo Workflow with human approval | Met | Control 2 "Split agent front door from execution"; briefing closing paragraph |
| agentgateway stays on management cluster for LLM routing/tokens/policy/audit | Met | Control 5 + both flow diagrams keep LLM egress through management agentgateway |

**Verdict:** the boss's "can this thing go rogue" question is addressed honestly. The
answer is not "we put it in the safe cluster" — it is "the damage ceiling is the RBAC
and tool grants, and here are the six controls that bound it in both models."

---

## 3. Balance check

The brief explicitly warns against a one-sided pitch. The artifact stays balanced:

- Path A is framed as *can be* the smaller surface for worker-internal namespaces,
  not as universally safer. Its cons (more deployments, per-worker config drift,
  local SA scoping risk) are listed.
- Path B is framed as valuable for fleet-level correlation and application namespaces
  already on Kafka/Event Hub, with the explicit caveat that broad central admin
  credentials or one broad management-scope UAMI are the dominant risk.
- The recommended position is a **hybrid**, not a winner, which matches the source
  docs (`PRODUCTION-READINESS.md` §5 lists central / per-cluster / hybrid as open
  options, not a settled decision).

---

## 4. Alignment with source docs

| Source | What the artifact reuses | Accurate? |
|---|---|---|
| `observability/PRODUCTION-READINESS.md` §5–6 | Central MCP = single point of failure + cross-cluster auth + UAMI; self-healing gap when mgmt cluster is down | Yes — table rows "Self-healing" and "Write blast radius" track §5 directly |
| `observability/ENGINEERING-ROLLOUT.md` | Worker-cluster namespaces with no EventHub dependency (cert-manager, external-secrets, kro, kyverno, reloader, monitoring, ingress-nginx) | Yes — reproduced verbatim in Recommended Position |
| `observability/confluent-cloud-pipeline/README.md` | Confluent Kafka / Event Hub as the management-side ingestion bus; Alloy + Alertmanager producers | Yes — Path B flow matches the two-producer / consumer model |
| `observability/prometheus-alertmanager/KAGENT-ALERT-TRIAGE-ARCHITECTURE.md` | agentgateway as LLM gateway (routing/fallback/cost), AKS-MCP as structured K8s access, read-only triage vs read-write remediation split | Yes — Controls 1, 2, 5 mirror the two-agent pattern and gateway role |
| `agents/kagent-triage/API-REFERENCE.md` | The actual read vs write MCP tool split that must be enforced by policy | Yes — Control 1 lists read tools to attach and write tools (apply/patch/delete/exec/label/annotate) to withhold; matches the tool table |

No claims in the artifact contradict the source docs. The one simplification: the
docs use `call_kubectl`/`call_helm` (AKS-MCP) while API-REFERENCE lists the
`k8s_*` tool-server tools. The artifact speaks generically about "evidence tools"
vs "apply/patch/delete/exec" so it is correct for both tool surfaces.

---

## 5. Public-safety sweep

```
GUID / subscription / tenant IDs ......... none
secrets / tokens / passwords / bearer .... none (only generic vocabulary: "token
                                           monitoring", "mTLS/token auth", "token
                                           budgets in agentgateway")
real hosts / internal domains / IPs ...... none
gitlab project IDs / internal emails ..... none
placeholders present ...................... {{WORKLOAD_KUBE_CONTEXT}}
binary artifacts added ................... none
```

Benign matches explained:

- Every `token`/`secret` hit is security-domain vocabulary describing controls, not a
  literal credential. No key material, no connection strings.
- Namespace names (`cert-manager`, `external-secrets`, `kro`, `kyverno`, `reloader`,
  `monitoring`, `ingress-nginx`) are upstream/community component names already
  published in `ENGINEERING-ROLLOUT.md`; they reveal no private topology.
- `{{WORKLOAD_KUBE_CONTEXT}}` is the approved placeholder convention from
  `CONTRIBUTING.md`.

Footer of the HTML already instructs adapters to replace environment-specific values
with placeholders before work use.

---

## 6. Validation results

| Check | Command | Result |
|---|---|---|
| HTML parses | `python3` `html.parser` feed | Parsed OK, no exceptions |
| Whitespace / conflict markers | `git diff --check` | Clean |
| Private-value sweep | `rg` GUID / secret / host / id patterns | No real values; only benign matches above |
| Browser render / interactivity | see §7 | See note |

---

## 7. Browser validation note

The page is self-contained (inline CSS + minimal vanilla JS, no external assets or
network calls). Interactivity is two pieces: the Path A / Path B / Compare both /
Architecture segmented selector and the "Copy as markdown" button. The path selector
is native radio inputs plus CSS sibling selectors, so it works even if the viewer
does not run inline JavaScript. The copy button still uses
`navigator.clipboard.writeText` with a select-text fallback.

Browser validation completed with a Chrome-backed Playwright render check before
the ServiceNow/UAMI wording update; the update is text-only and did not change the
selector mechanics:

- Page title loaded as `Kagent Triage Deployment Models`.
- H1 loaded as `Kagent triage: worker-local vs management-cluster routing`.
- Clicking `Path A` checked `path-worker`, highlighted the worker card, and dimmed the management card.
- Clicking `Path B` checked `path-management`, highlighted the management card, and dimmed the worker card.
- Clicking `Compare both` checked `path-both`, highlighted both path cards, and dimmed neither card.
- Clicking `Architecture` checked `path-architecture`, hid the flow cards, and displayed the network/port diagram.
- The boss briefing block rendered with 1448 characters.

The selector was then tightened from long action-style buttons ("Highlight Path A",
"Highlight Path B") into a CSS-backed segmented selector with short labels
(`Path A`, `Path B`, `Compare both`, `Architecture`) so it reads as a view selector
rather than a set of one-off actions. The Architecture tab emphasizes that both
models keep agentgateway and MCP services on the management cluster; the difference
is whether the event calls a worker-local agent first or exits to Kafka/Event Hub so
a management-cluster agent can triage and connect back to the worker through AKS-MCP.
It also explains that both paths can produce the same GitLab or ServiceNow output,
so the architectural difference is evidence collection and credential scope rather
than the final ticketing destination.

---

## 8. Suggested follow-ups (optional, not blocking)

- Add a one-line cross-link from the artifact to `PRODUCTION-READINESS.md` §5 so a
  reader can jump straight to the central-vs-per-cluster MCP decision (currently
  listed only in the Repo Anchors section — adequate).
- If/when the central-vs-per-cluster MCP decision is settled, update the Recommended
  Position from "hybrid is the safer rollout" to the chosen topology.

---

## 9. PR summary

**Changed files**

- `WORK-KAGENT-TRIAGE-DEPLOYMENT-MODELS.html` — public-safe boss briefing comparing
  worker-local (Path A) and management-cluster (Path B) kagent triage, framed around
  permission-bound blast radius rather than pod location. Includes a segmented
  Path A / Path B / Compare both / Architecture selector for explaining the flows and
  cross-cluster exposed surfaces. Clarifies that both paths can produce the same
  GitLab or ServiceNow output, while Path B's central UAMI/AKS-MCP can reach back
  into the worker and potentially other clusters in management scope.
- `BLAST-FEEDBACK.md` — this review record.

**Not touched** (out of scope): README navigation, manifests, RBAC,
kagent/agentgateway configs, Confluent assets, live deployment instructions. No
binary artifacts added.

**Validation:** HTML parses; `git diff --check` clean; private-value sweep clean
(only `{{WORKLOAD_KUBE_CONTEXT}}` placeholder and benign security vocabulary).

**Headline:** the artifact gives a skeptical reviewer a defensible answer — agent
blast radius is bounded by RBAC, tool grants, network paths, and human-approval
gates, not by which cluster the pod runs in. A central admin AKS-MCP identity or
broad UAMI reaching many management-scope clusters is the larger risk, in either
model.
