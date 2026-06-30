# Work Order / Skills Statement: kagent + Agentic Harness Delivery

## Scope

Deliver and operate the agentic remediation platform: **kagent** (agent CRDs, MCP
tool servers, agent skills) plus the **agentic harness** that feeds it —
observability events normalised through Vector, transported on Confluent Kafka,
routed by Argo Events/Workflows into the correct agent or escalation path,
running on hardened AKS.

This is not one discipline. It spans platform, streaming, observability, LLM/agent
safety, and security. Below is the skill set required to build and run it safely,
and the concrete risk per gap.

## Skills Required

| # | Skill area | What they do on this platform | Risk if we lack it |
|---|---|---|---|
| 1 | **AKS / Kubernetes platform engineering** | Hardened node pools (Azure Container Linux, Trusted Launch, Secure Boot/vTPM, NodeImage upgrade channel), RBAC, service accounts, secrets, namespace boundaries. | Insecure or non-upgradeable clusters; broken node image lifecycle; over-privileged service accounts running write-capable remediation. Hard constraints already apply (AKS 1.34+, no SecurityPatch channel, no Gen1 VMs) and need someone who understands why. |
| 2 | **Event streaming (Kafka / Confluent Cloud)** | Topic design, retention, consumer groups, partitioning, SASL/TLS auth, read-vs-write ACL separation, replay from raw topics. | Credential sprawl (one principal doing read+write), lost replay/audit, duplicate floods, no least-privilege boundary. |
| 3 | **Argo Events + Argo Workflows** | EventSource/Sensor filters, workflow templates, rate limits, retry strategy, passing the normalized contract into workflows correctly. | Events silently dropped or mis-routed; routing fields computed then discarded; runaway workflow churn; no rate limiting on remediation. |
| 4 | **Observability pipeline (Vector + Alertmanager/Grafana/Alloy/Prometheus)** | Vector VRL (remap/filter/dedupe), normalisation contracts, time-bounded dedupe, internal metrics, baseline capture for MTTA/MTTR. | Filter/dedupe missing from deployed config, no dedupe window, no metrics to prove value. Noise reaches agents; nobody can measure benefit. |
| 5 | **Agentic / LLM systems (kagent, MCP)** | Agent CRD design (`kagent.dev/v1alpha2`), MCP tool servers, read-only vs write agent boundaries, skill scaffolds, prompt/tool governance. | Agents given the wrong tools (e.g. `k8s_apply_manifest` on a read-only triage agent); no governance over what an agent can act on. |
| 6 | **Security & automation governance** | Gating `automation_allowed` behind explicit allowlists, treating alert labels as untrusted, secret handling, the final write gate in Argo. | Highest-consequence gap. Untrusted alert labels triggering automated write/remediation = self-inflicted outage or attack surface. A safety control, not a feature. |
| 7 | **SRE / incident operations** | Runbooks per auto-remediated alert, MTTA/MTTR baselines, on-call ownership, "what happens when Vector is down" procedures. | Automation with no runbook, no baseline, no rollback story. Can't prove it reduces incidents; may increase them. |
| 8 | **GitOps / IaC delivery** | Sanitised manifests, config parity between tested and deployed configs, CI for the test suite, no secrets in repo. | Tested config ≠ deployed config. "It passed in test" means nothing. |

## Risk Summary If These Skills Are Absent

1. **Safety risk (severe):** automated, write-capable remediation triggered by
   untrusted inputs. An agent acting on a mislabelled or spoofed alert can take
   destructive action on production. Requires skills #5 and #6.
2. **Reliability risk:** deployed config silently differs from tested config; no
   dedupe window; single points of failure with no health probes. Outages and
   duplicate floods. Skills #3, #4, #8.
3. **Security / compliance risk:** shared Kafka credentials, no ACL separation,
   secret handling. Skills #2, #6.
4. **Unmeasurable value:** no baseline, no metrics — cannot demonstrate this
   reduces incidents/MTTA/MTTR, so the investment cannot be justified later.
   Skills #4, #7.
5. **Platform debt:** AKS hardening constraints mishandled → clusters that cannot
   upgrade or do not meet the security baseline. Skill #1.

## Staffing Recommendation

Realistically **2–3 engineers**, not one generalist:

- **1 Platform / SRE engineer** — AKS hardening, Argo, Kubernetes security
  (skills 1, 3, 7).
- **1 Data / streaming + observability engineer** — Kafka/Confluent, Vector,
  observability contracts (skills 2, 4).
- **1 Agentic / security engineer** (can be shared / part-time) — kagent agent
  design + automation governance (skills 5, 6, 8).

A single engineer covering all eight is a key-person risk: if they leave, the
platform is unmaintainable and the automation is unauditable.
