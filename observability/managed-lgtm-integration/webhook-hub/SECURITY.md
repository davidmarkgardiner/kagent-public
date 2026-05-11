# Webhook Hub — Security Model

Scope of this document: **the receiver end only.** Everything from the inbound HTTPS request hitting our Istio Gateway through to the Workflow finishing. Upstream-side concerns (managed Grafana auth, egress proxy, Contact Point RBAC) are out of scope — that's the platform team's domain.

> **Trust boundary:** *the network packet arriving at our cluster's Istio ingress LB.* Everything before that boundary is the platform team's responsibility. Everything after is ours.

---

## Defence-in-depth — what's enforced today

The Hub uses **four** independent security layers. An attacker has to defeat all four to make a meaningful impact.

### Layer 1 — Network: Istio Gateway + source IP allow-list

- TLS terminated at the shared wildcard Gateway in `aks-istio-ingress`. Cert lifecycle owned by platform.
- `AuthorizationPolicy` (`05-istio-authorization-policy.yaml`) restricts traffic to:
  - **Method:** `POST` only
  - **Path:** `/inbound` or `/inbound/` only
  - **Source IP:** allow-list of upstream sender egress NATs (managed Grafana / managed AlertManager only)
- Default `DENY` policy on the EventSource pod — anything not matching the explicit ALLOW is rejected at the sidecar before reaching the application.

### Layer 2 — Authentication: bearer token presence (Istio)

- Same `AuthorizationPolicy` requires `Authorization: Bearer *` header to be present.
- Istio enforces presence; the *exact* token value is checked at Layer 3.
- Reason: keeps token value out of YAML; the policy can be applied via GitOps without leaking the secret.

### Layer 3 — Authentication: bearer token exact match (Argo Events)

- `EventSource.spec.webhook.inbound.authSecret` (in `03-eventsource.yaml`) verifies the **exact** token value in the `Authorization: Bearer <token>` header against the `webhook-hub-token` Secret's `token` key.
- Mismatch → Argo Events rejects with 401 before the event hits the EventBus.

### Layer 4 — Authorisation: Sensor filters + RBAC

- Sensors filter inbound events by labels (`status: firing`, `severity`, `team`). Anything not matching a Sensor's filter is dropped at the EventBus subscription stage.
- `argo-events-sa` ServiceAccount RBAC (`02-rbac.yaml`) is scoped to:
  - `pods/log`, `events`, `configmaps` read (for triage diagnostics)
  - `workflows`, `workflowtemplates` create in `argo-events` namespace only
  - **No write access to anything else.** No node access, no secret reads outside argo-events.

---

## Threat model

What we defend against, what mitigates each, and the residual risk.

| Threat | Mitigation | Residual risk |
|---|---|---|
| **Unauthorised webhook caller spoofing alerts** | Layers 1+2+3 all required to deliver a payload | Negligible — would require IP spoofing AND token leak AND Istio bypass |
| **Token leak (e.g. accidental commit)** | Token in Vault via ExternalSecret; not in YAML; rotation supported | Anyone with the token can fire alerts. Detection: anomalous Sensor trigger rate. Response: rotate via ExternalSecret, redeploy. |
| **Replay of legitimate webhook calls** | Sensor rate limits (5/min for AI triage); idempotent Workflow design (workflows are observability, not state-changing) | Bounded. Replay creates duplicate Mattermost posts and GitLab issues — annoying, not damaging |
| **Payload bombs (huge alert array, deeply nested JSON)** | EventSource has body size limit (configurable, default 1MB); jq runs in a container with CPU/memory limits | Workflow OOM possible if limits are too high — set body size limit to 256KB explicitly |
| **DoS via alert flood (1000s of alerts/min)** | Sensor `rateLimit`; circuit-breaker pattern; Workflow pod-level resource limits; namespace ResourceQuota | Workflow queue can backlog — set Sensor rate-limit per-subscriber, not just global |
| **SSRF — alert content used to construct outbound URL** | Workflow URLs read from in-cluster ConfigMaps only; alert payload **never** used to build a URL or hostname | None — verified by code review of `06-workflow-template-triage.yaml` |
| **Command injection — alert content in shell argument** | Workflow scripts use `jq -n --arg` for safe JSON construction; no `eval`, no shell-format alert content (memory: lesson learned for special chars in heredoc JSON) | Low — but every new Workflow step needs the same review. Add a check to PR template |
| **Prompt injection — alert content manipulates kagent** | kagent has read-only tools (no `kubectl delete`, no `kubectl apply`, no `kubectl exec`); recommendations are advisory only | Bounded — worst case is a hallucinated remediation in Mattermost. Humans must verify before acting. **kagent must stay read-only forever.** |
| **Cross-team alert leakage via overly broad Sensor filter** | Convention: every Sensor must filter on `commonLabels.team` matching its owning team | Currently convention-only, not enforced. **Action:** Kyverno admission policy (see Gaps below) |
| **Compromised kagent leaking alert content externally** | kagent runs locally (qwen3-14b in-cluster); no external LLM call; NetworkPolicy on kagent pods restricts egress | None — verified, nothing leaves the cluster |
| **Compromised Workflow pod escalating** | Pods run as non-root, drop ALL capabilities, seccomp RuntimeDefault, no hostNetwork/hostPID; namespace under restricted PSA | Bounded — pod is a script-runner with curl/jq, no shell tools beyond that |
| **Audit gap — alert handled but no record** | Argo Events controller logs every webhook receipt + Sensor trigger + Workflow run. GitLab issue created per triage. | Logs live in cluster — **gap:** not yet forwarded to central audit (see Gaps) |

---

## Gaps — what we MUST add before production

### G1. ExternalSecret + Vault for the bearer token

**Today:** `01-secrets.yaml` has the ExternalSecret block commented out; the deploy script generates a random token and stores it in a static Secret.
**Risk:** rotation is manual; if the static Secret is exfiltrated, the token is valid forever.
**Fix:** uncomment the ExternalSecret block, point at the Vault path, set `refreshInterval: 1h`. Token rotates on a documented cadence (recommend 90 days).

### G2. Audit log forwarding

**Today:** Argo Events / Workflow logs are stdout, captured by the cluster log collector, retained per cluster's default (often 7–30 days).
**Risk:** no long-term audit trail for compliance (SOC 2 / ISO 27001 / banking-sector requirements).
**Fix:** forward logs from `argo-events` namespace to central log store with ≥90 day retention. Document the search query for "all alerts received in the last X days" in this doc.

### G3. Body size limit on the EventSource

**Today:** Argo Events default body limit applies (typically generous).
**Risk:** large payloads consume Sensor + Workflow memory.
**Fix:** add `maxPayloadSize: 256k` (or equivalent) to the EventSource webhook config. Reject larger requests at ingress.

### G4. Kyverno (or Gatekeeper) policy for Sensor team-scoping

**Today:** Sensor authors are trusted to filter on their own team's `commonLabels.team`.
**Risk:** an over-broad filter (no team match, or `team=~".+"`) lets a Sensor see other teams' alerts.
**Fix:** admission policy that rejects any Sensor in `argo-events` whose dependency filters don't include a `team` match scoped to the Sensor's namespace label.

### G5. Outbound NetworkPolicy on Workflow pods

**Today:** Workflow pods can egress to anywhere reachable from the cluster.
**Risk:** compromised Workflow pod could exfiltrate alert content (which may include PII from log lines).
**Fix:** Istio `ServiceEntry` + outbound `AuthorizationPolicy` allow-listing only:
- `kagent` service (in-cluster)
- `mattermost` service (in-cluster)
- GitLab API (single external host)
- Loki API (in-cluster, optional — for re-querying logs during triage)
Everything else: DENY.

### G6. Self-monitoring alert (the Hub's own health)

**Today:** if the Hub goes dark, no one knows.
**Risk:** silent triage failure.
**Fix:** PrometheusRule that fires on:
- `up{namespace="argo-events", job=~"webhook-hub.*"} == 0` for 2m
- Sensor pod absence
- Argo Events EventBus health
**Routing:** *to BigPanda*, intentionally — BP is the right path for "the Hub itself is broken."

---

## What we WON'T do — explicit non-goals

These are bright lines. Crossing them changes the threat model materially and requires a separate review.

### Auto-remediation (no `kubectl delete/apply/exec` from kagent)

The Hub is **advisory only.** kagent reads cluster state and recommends; humans decide.
The moment we add an auto-remediation path, **prompt injection becomes a real exploit** — an attacker who can plant a log line on a triaged pod can manipulate the LLM into running destructive commands. Today they can only manipulate the LLM into making a wrong recommendation in Mattermost, which a human must explicitly act on.
**Auto-remediation is a separate system, separate review, separate threat model.**

### External LLM calls

kagent uses qwen3-14b running in-cluster. We do not send alert content to OpenAI / Anthropic / any external LLM. Alert payloads can contain PII (customer IDs, email addresses in error logs); sending that to an external service is a regulatory event, not a feature change.

### Tenant teams writing arbitrary code in Sensors

Sensors trigger Workflows. Workflows are admin-reviewed templates. Subscriber teams pick *which* template to trigger; they don't write the script that runs. This keeps the Workflow review surface bounded.

### Webhook receivers other than Grafana / managed AlertManager

The source-IP allow-list is the boundary. New senders require explicit IP allow-list entry — not implicit acceptance because they have a token.

---

## Operational security

### Token rotation

Documented procedure when wired to ExternalSecret:
1. Update Vault secret value
2. ExternalSecret refreshes within 1 hour (or run `kubectl annotate externalsecret webhook-hub-token force-sync=$(date +%s)` for immediate)
3. Argo Events EventSource picks up the new value within ~30s (controller watches Secret)
4. Hand new token to upstream sender's config (Grafana Contact Point or AlertManager `webhook_configs`)
5. Old token continues to work until upstream is updated (no flip cutover required because authSecret is read at request time, not pod start)

### Incident response — token suspected leaked

1. Rotate via ExternalSecret + Vault (G1)
2. Audit Argo Events logs for unexpected webhook receipt patterns (anomalous source IP, anomalous time of day)
3. Audit Sensor trigger logs for triage workflows from suspicious labels
4. If misuse detected, file standard security incident; downstream actions are Mattermost posts and GitLab issues, both reversible
5. Post-mortem: how did the token leak? Tighten rotation cadence if a process gap caused it.

### What to do when the Hub is down

The Hub being down ≠ alerts being lost. BigPanda continues to route alerts via its own path (incident management). The Hub being down only means **AI triage is paused**.
1. The self-monitoring rule (G6) fires to BigPanda → on-call paged
2. Incident response: restore Argo Events controllers, EventBus, EventSource pod
3. NATS JetStream replays buffered events on recovery (configurable retention)
4. No re-fire required from upstream — alerts that fired during the outage may or may not be replayed depending on JetStream config (decide per-environment)

---

## Compliance considerations

| Concern | Status |
|---|---|
| **Data residency** — alert payloads stay in our cluster, in-region | ✅ Yes (no external LLM, no external services beyond GitLab/Mattermost which are already in-region) |
| **Audit trail** — who saw which alert, who acted | ⚠️ Partial — logged in cluster, gap is central log forwarding (G2) |
| **PII handling** — alert annotations may include customer-identifying info | ⚠️ Document which alerts carry PII; route those to a private Mattermost channel, not the team default |
| **Encryption in transit** — TLS to ingress, mTLS in mesh | ✅ Yes |
| **Encryption at rest** — Secret values, Vault | ✅ Vault when wired (G1); etcd encryption depends on cluster config (verify with platform) |
| **Token rotation** — documented and automatable | ⚠️ Planned via ExternalSecret (G1) |
| **Approved alerting channel** (banking / regulated sectors) | ⚠️ Document the Hub's role as *additive automation*, BigPanda remains the canonical incident channel |

---

## Pre-prod review checklist

Before this leaves PoC and becomes load-bearing:

- [ ] **G1** — ExternalSecret + Vault wired for `webhook-hub-token`
- [ ] **G2** — Argo Events / Workflow logs forwarded to central log store, ≥90 day retention
- [ ] **G3** — EventSource body size limit set to 256KB
- [ ] **G4** — Kyverno policy enforcing per-team Sensor scoping
- [ ] **G5** — Istio ServiceEntry + outbound AuthorizationPolicy on Workflow pods
- [ ] **G6** — PrometheusRule for Hub self-health, routed to BigPanda
- [ ] Image pinning by digest (no `latest` tags)
- [ ] Pod Security Admission set to `restricted` for `argo-events` namespace
- [ ] Resource limits on every Workflow step verified
- [ ] PR review template includes shell-injection / SSRF checks for new Workflow templates
- [ ] Runbook documented for "Hub is down" + "Token suspected leaked"
- [ ] Penetration test or threat model walkthrough with security team

---

## What this document is not

This covers the **receiver end only**, per the agreed scope split. It does not cover:

- Grafana RBAC / Contact Point governance — platform team owns
- Egress proxy auth on the upstream side — platform team owns
- Loki/Mimir Ruler API security — platform team owns
- Network path from the upstream egress proxy to our Istio ingress — shared (TLS owned by us at the Gateway)

If the platform team raises concerns about *their* end, that's a different conversation with a different document.
