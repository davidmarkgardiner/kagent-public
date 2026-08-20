# SRE guide: reviewing agent triage output and closing the feedback loop

## Purpose

The triage agents are producing reports and GitLab issue drafts about possible
problems across the cluster fleet. Producing that output is not the end of the
process. An SRE must decide whether each finding is real, useful, duplicated,
or noise, and record what happened.

This guide establishes a lightweight operating loop so that:

- credible incidents receive an owner and an appropriate response;
- repeated reports are grouped instead of creating an ignored queue;
- false positives and low-value alerts are reduced at their source; and
- feedback improves the agent's tools, prompts, context, and evidence quality.

The agent output is a lead, not proof that a cluster is broken. The receiving
SRE remains responsible for validating it against current system evidence.

## Feedback is a GitOps change, not a ticket to another team

**The SRE who reviews the output is also the SRE who changes the system.**
Feedback is not filed to a platform or engineering backlog and waited on. Every
tunable part of this pipeline is a manifest in Git:

| Layer | What you change there |
|---|---|
| **Alloy** | which namespaces and workloads are collected at all |
| **Vector** | which signals are admitted, redaction, dedupe key, burst suppression |
| **Argo** | per-route sensor filters, rate limits, concurrency, claim window |
| **Agent system prompt** | how the agent reasons, what it must check, what it must not claim |
| **Agent skills / tools** | which diagnostics it can run and which runbook knowledge it has |

The reviewing SRE raises a merge request against the GitOps repo, gets it
reviewed, merges it, and the reconciler applies it. The improvement is live on
the cluster in minutes — on the same day the noise was observed, not next
quarter. If a finding cannot be turned into a Git change, it is not yet a
finding; it is an observation that still needs a root cause.

See [Applying feedback via GitOps](#applying-feedback-via-gitops) for the exact
files, knobs, verification, and the reload gotchas.

## The operating loop

```mermaid
flowchart LR
    A[Agent output or GitLab draft] --> B[Named SRE reviews it]
    B --> C{Already tracked?}
    C -->|Yes| D[Link to canonical issue\nand add occurrence evidence]
    C -->|No| E[Create or claim tracking issue]
    D --> F[Validate against live evidence]
    E --> F
    F --> G{Outcome}
    G -->|Real and actionable| H[Prioritise, remediate, verify]
    G -->|Real but not actionable| I[Document risk and disposition]
    G -->|Duplicate| J[Improve grouping or deduplication]
    G -->|False positive or noise| K[Tune source, rule, or agent]
    H --> L[Record outcome and agent feedback]
    I --> L
    J --> L
    K --> L
    L --> N{Needs a system change?}
    N -->|No| M[Review trends]
    N -->|Yes| O[Raise GitOps MR\nAlloy / Vector / Argo / agent]
    O --> P[Review and merge]
    P --> Q[Reconciler applies to cluster]
    Q --> R[Verify with fixture or live signal]
    R --> M
    M --> A
```

The right-hand side of that loop is the point of the exercise. A review that
ends at "recorded the outcome" has not reduced anything.

## Minimum team commitment

Assign an SRE reviewer for each review period. The reviewer does not have to
fix every issue personally, but must make sure each new output is acknowledged,
deduplicated, classified, and either owned or explicitly closed with evidence.

Agree these values with the SRE team rather than leaving them implicit:

| Decision | Team value |
|---|---|
| Review queue or GitLab project | `{{TRIAGE_QUEUE_OR_PROJECT}}` |
| Review frequency | `{{FOR_EXAMPLE_EACH_WORKING_DAY}}` |
| First-review target | `{{TARGET_DURATION}}` |
| Critical escalation route | `{{ON_CALL_OR_INCIDENT_ROUTE}}` |
| Agent-feedback owner | `{{PLATFORM_OR_AGENT_OWNER}}` |
| Noise-review cadence | `{{FOR_EXAMPLE_WEEKLY}}` |

Severity and escalation must follow the existing incident-management process.
This guide does not replace on-call escalation for an active high-impact event.

## What the reviewing SRE does

### 1. Acknowledge and establish ownership

For each new agent output:

1. Check whether a canonical issue already exists for the same stable
   workload, symptom, cluster, namespace, and likely cause.
2. If it exists, link the new occurrence to it. Do not create another issue
   solely because a pod name, timestamp, or generated message changed.
3. Otherwise, create or claim a GitLab issue in the agreed project.
4. Assign an owner and record the next review time or target date.
5. Escalate immediately through the normal incident process when the supplied
   impact warrants it; do not wait for the feedback meeting.

An unassigned issue is not an accepted handover.

### 2. Validate the finding

Read the agent's routing, evidence, likely cause, tool audit, access failures,
and confidence labels. Then compare them with current authoritative evidence.
Use the exact subscription, cluster, kube context, namespace, and workload;
never assume the agent targeted the right place merely because its output looks
plausible.

At minimum, answer:

- Does the affected object or condition still exist?
- Did the agent query the intended cluster and namespace?
- Is there user, service, SLO, capacity, security, or operational impact?
- Does the evidence establish the claimed cause, or only correlate with it?
- Is this a new problem, an expected transient condition, planned work, a test,
  or another occurrence of an existing problem?
- Did permissions, missing context, stale data, or tool failure prevent a valid
  conclusion?

Do not mark a report as confirmed based only on the agent's prose. Record the
live evidence or existing incident/change record that supports the decision.

### 3. Choose one outcome

Use one primary outcome so the results can be measured consistently:

| Outcome | Meaning | Required action |
|---|---|---|
| `CONFIRMED_ACTIONED` | Real issue; a response or fix was required | Link the change/incident, record verification and any rollback |
| `CONFIRMED_TRACKED` | Real issue; accepted backlog, risk, or observation | Record owner, priority, reason, and review date |
| `VALUABLE_NO_ACTION` | Correct and useful context, but no action was appropriate | Explain the value and why no action was needed |
| `DUPLICATE` | Same underlying condition is already tracked | Link the canonical issue and add occurrence evidence |
| `EXPECTED_TRANSIENT` | Real but expected to recover within an agreed window | Link the runbook/change and confirm recovery |
| `FALSE_POSITIVE` | Agent conclusion was unsupported or wrong | Identify the faulty evidence, reasoning, context, or tool behaviour |
| `NOISE_SOURCE` | Input should not have entered triage at this frequency or severity | Create an alert/log-source tuning action |
| `BLOCKED_VALIDATION` | Access, routing, retention, or missing evidence prevented a decision | Assign the unblock action and re-review date |

“Closed”, “not a problem”, and “ignored” are not sufficient outcomes without a
reason and supporting evidence.

### 4. Record whether the agent helped

Review the agent separately from the underlying incident. A real incident can
have a poor agent report, and a false alarm can still demonstrate good agent
reasoning.

Record:

- whether the target subscription, cluster, context, and namespace were right;
- whether the evidence was current, bounded, relevant, and safely redacted;
- whether the diagnosis separated proven facts from hypotheses;
- what the agent found faster or more clearly than the normal investigation;
- which important check, tool, context, or runbook it missed;
- whether any command was unnecessary, unsafe, too broad, or unsuccessful;
- whether the recommended human actions were safe and useful; and
- one specific improvement, or `NO_AGENT_CHANGE` when none is justified.

Avoid feedback such as “agent was bad”. Prefer testable statements, for example:

> The agent diagnosed application failure from one restarted pod but did not
> inspect the Deployment or sibling replicas. Require workload-level health
> evidence before claiming service impact.

### 5. Feed the result back as a GitOps change

Add the completed review to the canonical issue, then change the file that
caused the problem. Each finding maps to one layer:

| Finding | Change this | Layer |
|---|---|---|
| Signal should never have entered triage | Vector `incident_signals` condition (drop the reason or log pattern) | Vector |
| Whole namespace or workload is not worth triaging | Alloy namespace scope **and** the matching Sensor `body.namespace` filter | Alloy + Argo |
| Right signal, far too often | Vector `delivery_key` / `suppress_exact_repeats`, Sensor `rateLimit`, claim window | Vector + Argo |
| Too many concurrent tickets during a burst | `triage-workflow-concurrency` semaphore value | Argo |
| Duplicate tickets for the same condition | `delivery_key` and `dedupe_key` fingerprint composition | Vector + Argo |
| Agent missed a check it should always do | Agent `systemMessage` | Agent prompt |
| Agent lacks domain knowledge or a runbook | Agent skill under `agents/skills/<skill>/` | Agent skill |
| Agent used the wrong tool, or could not see enough | Agent `spec.declarative.tools[].toolNames` allowlist | Agent tools |
| Agent claimed a cause the evidence did not prove | Evaluation agent criteria + a new evaluation fixture | Agent + evaluation |
| Agent had too much access | `toolNames` allowlist, Azure RBAC, Kubernetes RBAC | Agent + RBAC |
| Wrong or ambiguous target cluster | Cluster registry / caller input contract | Routing |
| Evidence was missing entirely | Alloy collection scope, or a workload observability change | Alloy |

Turn repeatable agent failures into an evaluation case **before** changing the
agent. Retain a sanitized example input, expected behaviour, and the
unacceptable behaviour. Re-run that case after the change so improvement is
demonstrated, not assumed.

## Applying feedback via GitOps

### Which pipeline this applies to

The current triage pipeline is **Alloy → Vector → Kafka → Argo Events → kagent
→ GitLab**. The canonical, end-to-end-verified implementation is:

```
work-agent-bundles/homelab-verified-triage-replication/
```

Its `config/` directory is the set of files an SRE edits. A newer extension,
`work-agent-bundles/aks-platform-triage-specialists/`, routes the same Kafka
topic to four domain specialists (platform health, infrastructure outage,
scheduling/placement, identity/certificates) using a `triage_domain` label and
one Sensor plus one consumer group per domain — so a single domain can be
paused without affecting the other three.

`agents/kagent-triage/aks-multi-subscription-triage/` is a **separate lane**:
a directly-invoked read-only agent for fleet-wide AKS incidents. It is not on
the Kafka path, so the Vector and Argo knobs below do not apply to it — only
the agent prompt, skill, and tool knobs do.

### The knobs, and where they live

All paths are relative to `work-agent-bundles/homelab-verified-triage-replication/`
unless stated otherwise.

| Knob | File | What it controls | Applies when |
|---|---|---|---|
| Namespace collection scope | `config/01-alloy.yaml` — `discovery.relabel.pod_logs` keep regex **and** `loki.source.kubernetes_events` `namespaces = [...]` | Whether anything is collected from a namespace at all | After Alloy restart |
| Log line pre-filter | `config/01-alloy.yaml` — `stage.drop` | Drops lines before they leave the worker | After Alloy restart |
| Signal admission (the tier filter) | `config/02-vector.yaml` — `transforms.incident_signals.condition` | Which event reasons and log patterns reach Kafka | After Vector restart |
| Redaction | `config/02-vector.yaml` — `redact(message, filters: [...])` | What evidence is allowed to leave the cluster | After Vector restart |
| Burst suppression / dedupe identity | `config/02-vector.yaml` — `.delivery_key` and `suppress_exact_repeats` | Collapses repeats of the same failure | After Vector restart |
| Per-route admission | `config/03-argo.yaml` — Sensor `dependencies[].filters.data` | Cluster, namespace, `signal_kind`, `automation_allowed` gates per route | ~1 min, controller recreates the Sensor pod |
| Trigger cadence | `config/03-argo.yaml` — `rateLimit: {requestsPerUnit: 5, unit: Minute}` | Max workflows started per route per minute | ~1 min |
| Concurrency | `config/04-workflow-concurrency.yaml` | Concurrent triage workflows (semaphore) | Next workflow submission |
| Which agent is called | `config/05-triage-evaluation-settings.yaml` (or `work-evaluation-overlay/`) | Swaps the triage agent without editing the WorkflowTemplate | Next workflow submission |
| Ticket dedupe window | `config/03-argo.yaml` — `claim-24h-window` template | How long one incident reuses one ticket | Next workflow submission |
| Agent reasoning | `a2a-evaluation-gate/homelab-evaluated-triage-agent.yaml` — `spec.declarative.systemMessage` | What the agent must check, prove, and never claim | Next agent call |
| Agent tools | same file — `tools[].mcpServer.toolNames` | Which diagnostics it may run | Next agent call |
| Agent quality bar | `a2a-evaluation-gate/evaluation-agent.yaml` | PASS/FAIL criteria the triage agent must satisfy | Next agent call |
| Agent skill | `agents/skills/<skill-name>/SKILL.md` + `references/` + `assets/` | Domain knowledge and runbook procedure | Next agent call after skill sync |

### Which layer owns which symptom

Ask one question: **at what point did this become wrong?**

| What you are looking at | Layer that owns it |
|---|---|
| This should never have been collected from that namespace or container | **Alloy** |
| Collected correctly, but is not an incident | **Vector** (admission) |
| Is an incident, but arrived 40 times | **Vector** (dedupe key) |
| Ticket contains something it should not | **Vector** (redaction) |
| Right signal, right volume, but too fast for the humans | **Argo** (rate limit / semaphore) |
| Agent reasoned badly, over-claimed, or skipped a check | **Agent system prompt** |
| Agent could not see what it needed | **Agent tools** |
| Agent did not know *our* procedure for this | **Agent skill** |

A wrong conclusion drawn from good evidence is never fixed by suppressing the
signal. A flood of correct tickets is never fixed by editing the prompt.

### Worked examples

All paths relative to `work-agent-bundles/homelab-verified-triage-replication/`.

---

#### 1. Alloy — a namespace that should never be triaged

**You see:** a steady trickle of tickets from `platform-test-app`, a sandbox
namespace where engineers deliberately break things. Every one is
`FALSE_POSITIVE` or `EXPECTED_TRANSIENT`.

**File:** `config/01-alloy.yaml` — and it must change in **three** places.

```diff
     rule {
       source_labels = ["__meta_kubernetes_namespace"]
-      regex = "aks-istio-ingress|...|platform-test-app|xxx-issuer-system|..."
+      regex = "aks-istio-ingress|...|xxx-issuer-system|..."
       action = "keep"
     }
```

```diff
   loki.source.kubernetes_events "events" {
-    namespaces = [..., "platform-test-app", "xxx-issuer-system", ...]
+    namespaces = [..., "xxx-issuer-system", ...]
```

Then remove it from the `body.namespace` value list on **both** Sensors in
`config/03-argo.yaml` (`red-log-triage` and `red-event-triage`), so the filter
list does not drift out of sync with what is actually collected.

**Effect:** nothing from that namespace is collected, shipped, or billed to
Kafka. **Verify:** restart Alloy, break something in that namespace on purpose,
confirm no Kafka record and no workflow.

---

#### 2. Alloy — one chatty container is producing most of the volume

**You see:** 80% of log-path tickets cite `istio-proxy` access-log lines
containing the word `error`, in namespaces you *do* want triaged.

**File:** `config/01-alloy.yaml`, `discovery.relabel "pod_logs"`. Add a drop
rule modelled on the existing self-drop rule:

```alloy
    // Istio sidecar access logs are high-volume and rarely the incident.
    // The app container in the same pod is still collected.
    rule {
      source_labels = ["__meta_kubernetes_pod_container_name"]
      regex = "istio-proxy"
      action = "drop"
    }
```

**Effect:** the sidecar is dropped, the workload container in the same pod is
untouched. Prefer this to widening the Vector filter, which would have hidden
real app errors too.

---

#### 3. Alloy — a real incident produced no evidence at all

**You see:** `BLOCKED_VALIDATION`. A genuine outage happened in a namespace the
agent never reported on, because Alloy was never watching it.

**File:** `config/01-alloy.yaml` — the reverse of scenario 1: add the namespace
to the keep regex **and** the `namespaces = [...]` list, and add it to both
Sensor `body.namespace` lists in `config/03-argo.yaml`.

Adding scope raises volume. Check the Vector tier is right for that namespace
before merging, and watch ticket count for a day after.

---

#### 4. Vector — turn off one event reason

**You see:** `Unhealthy` and `ProbeWarning` fire on every rolling deployment.
They are correct events and never actionable.

**File:** `config/02-vector.yaml`, `transforms.incident_signals.condition` —
remove them from the reason alternation:

```diff
- r'^(BackOff|Failed|FailedScheduling|OOMKilled|OOMKilling|Unhealthy|Evicted|...|ProbeWarning|FailedSync|...)$'
+ r'^(BackOff|Failed|FailedScheduling|OOMKilled|OOMKilling|Evicted|...|FailedSync|...)$'
```

**Effect:** stopped on the worker, before Kafka — costs nothing downstream.
This is the cheapest and most durable "turn that alert off" there is.

**Caution:** `Unhealthy` on a rollout is noise; `Unhealthy` sustained for 20
minutes on a production service is an incident. If you need the second one,
do not drop the reason — instead add a duration or `event_count` condition, or
route it to a lower-priority sensor, so the sustained case still fires.

---

#### 5. Vector — turn off a log pattern

**You see:** an application logs `connection refused` every 30s against an
optional cache. Correct, harmless, and it mints `log-availability` tickets.

**File:** `config/02-vector.yaml`. Prefer narrowing over deleting the keyword —
`refused` catches real outages elsewhere. Add a targeted exclusion in
`transforms.normalize` before the filter, or tighten the filter itself:

```diff
  incident_signals:
    type: filter
    inputs: [normalize]
-   condition: "... || (.signal_kind == \"log\" && match(...))"
+   condition: "... || (.signal_kind == \"log\" && !match(string!(.evidence.representative_log_lines), r'(?i)optional cache backend unavailable') && match(...))"
```

Record the exclusion string and a review date in a comment above it. A bare
negative match with no owner is how a pipeline goes quietly blind.

---

#### 6. Vector — one crashlooping pod created a dozen tickets

**You see:** `payments-api-7f85bd8ddc-ab123` crashlooped, was replaced by
`payments-api-7f85bd8ddc-cd456`, and each new pod name opened a **new**
ticket for the same failure.

**Cause:** in `config/02-vector.yaml` the incident identity is
`cluster:namespace:pod`:

```vrl
.dedupe_key = sha2(join!([.cluster, .namespace, .pod], ":"))
```

A replacement pod is a different pod name, so it is a different incident. This
is exactly the gap `NOISE-CONTROL-AND-CAPACITY.md` describes as fixed by a
derived `workload` identity — that derivation is **not** in this config yet.

**Fix:** derive a stable workload identity and key on it:

```vrl
# Deployment-style pod names: <workload>-<replicaset-hash>-<suffix>.
# Strip the two generated suffixes so a replacement pod reuses the ticket.
# Pods that do not match keep their full name as the identity.
parsed = parse_regex(.pod, r'^(?P<w>.+)-[a-z0-9]{6,10}-[a-z0-9]{5}$') ?? {}
.workload = string(parsed.w) ?? .pod
.dedupe_key = sha2(join!([.cluster, .namespace, .workload], ":"))
```

Keep the raw `.pod` in the envelope — the agent still needs it as evidence.

**Effect:** pod churn stops minting tickets. **Verify:** delete the pod during a
smoke run and confirm the second occurrence lands on the existing ticket, and
that `vector_component_discarded_events_total{component_id="suppress_exact_repeats"}`
advances.

---

#### 7. Vector — a ticket contained something it should not

**You see:** a GitLab issue quoting a log line with a database connection
string in it. This is a security finding, not a noise finding — raise it
through the normal process as well as fixing the pipeline.

**File:** `config/02-vector.yaml`, the `redact()` filter list:

```diff
  safe_message = redact(message, filters: [
    r'(?i)(password|passwd|pwd|token|api[_-]?key|secret|client_secret)\s*[=:]\s*[^\s,;]+',
    r'(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+',
-   r'(?i)(cookie|set-cookie)\s*[:=]\s*[^\r\n]+'
+   r'(?i)(cookie|set-cookie)\s*[:=]\s*[^\r\n]+',
+   # Connection strings: postgres://user:pass@host, mongodb+srv://..., amqp://...
+   r'(?i)\b[a-z][a-z0-9+.-]*://[^:\s/]+:[^@\s]+@[^\s]+'
  ])
```

Redaction runs before the envelope is built, so nothing unredacted has ever
reached Kafka, the agent, or GitLab from that point on. Existing tickets still
contain the leak — redact or delete them separately.

---

#### 8. Vector — every log ticket is titled `log-error`

**You see:** log-path tickets are unusable for grouping because they all carry
the same generic reason.

**File:** `config/02-vector.yaml`, the `.reason` category ladder. Add a branch
**above** the final `else`, most specific first:

```diff
    } else if match(safe_message, r'(?i)(unavailable|unreachable|connection refused|refused)') {
      "log-availability"
+   } else if match(safe_message, r'(?i)(certificate|x509|tls handshake|expired)') {
+     "log-certificate"
+   } else if match(safe_message, r'(?i)(disk|no space left|quota exceeded)') {
+     "log-capacity"
    } else if match(safe_message, r'(?i)(fatal|panic|critical|segfault)') {
```

Categories must stay small and stable — they become ticket titles, GitLab
labels, and part of the log-path `delivery_key`. Adding a category **splits**
existing dedupe groups, so expect a one-off bump in new tickets.

---

#### 9. Argo — right signal, right volume, arriving too fast

**You see:** a node drain produced 30 correct tickets in two minutes and buried
the queue.

**Files:** `config/03-argo.yaml` (`rateLimit`, per route) and
`config/04-workflow-concurrency.yaml` (semaphore):

```diff
-     rateLimit: {requestsPerUnit: 5, unit: Minute}
+     rateLimit: {requestsPerUnit: 2, unit: Minute}
```

```diff
  data:
-   red-agentic-triage: "5"
+   red-agentic-triage: "3"
```

**Be honest about what this does:** it slows arrival, it does not reduce
volume. A sustained flood still arrives, just later. Use it to protect the
agent backend and GitLab, not as a noise fix.

---

#### 10. Agent prompt — the agent over-claimed

**You see:** the agent declared "service outage" from a single restarted pod,
without ever looking at the Deployment or the sibling replicas.

**File:** `a2a-evaluation-gate/homelab-evaluated-triage-agent.yaml`,
`spec.declarative.systemMessage`. Add a **testable** instruction, not a
sentiment:

```diff
      You are a READ-ONLY incident triage agent. Never create, patch, delete,
      exec, scale, or remediate. Use the available Kubernetes diagnostic tools
      before making a conclusion.
+
+     Before claiming service-level impact, you MUST inspect the owning
+     Deployment/StatefulSet and its sibling replicas. If a majority of replicas
+     are Ready, describe the finding as a single-replica failure, not a service
+     outage. If you could not retrieve the owning workload, say so explicitly
+     and lower your confidence -- do not infer service impact from one pod.
```

Write it as something the evaluator can check. "Be more careful" is not a
prompt change; "inspect the owning workload before claiming X" is.

---

#### 11. Agent prompt — the agent recommended an unsafe action

**You see:** "Recommended next steps: delete the PVC and let it recreate."

Same file, same field. Constrain the shape of the output, not just the tone:

```diff
+     Recommended next steps must be read-only investigation steps, or changes
+     expressed as a GitOps diff for human review. Never recommend an imperative
+     destructive command (delete, drain, cordon, scale, rollout restart) as a
+     first step. If a destructive action is genuinely the only remedy, state the
+     precondition that must be verified first and who must approve it.
```

Then add the case to `fixtures/` so a regression is caught, and consider
tightening the PASS criteria in `a2a-evaluation-gate/evaluation-agent.yaml` so
an unsafe recommendation is rejected before the ticket is ever written.

---

#### 12. Agent tools — the agent could not see what it needed

**You see:** "I was unable to determine whether the node was under pressure."

**File:** same agent YAML, `spec.declarative.tools[].mcpServer.toolNames`. This
is an allowlist; anything absent simply does not exist to the agent:

```diff
          toolNames:
            - k8s_check_service_connectivity
            - k8s_get_events
            - k8s_describe_resource
            - k8s_get_resource_yaml
            - k8s_get_resources
            - k8s_get_pod_logs
+           - k8s_get_cluster_configuration
```

**Rule:** add read-only tools freely; never add `k8s_apply_manifest`,
`k8s_delete_resource`, `k8s_patch_resource` or `k8s_execute_command` to a
triage agent. The read-only boundary is enforced here and in RBAC, not by the
prompt.

---

#### 13. Skill — the agent does not know *our* procedure

**You see:** the diagnosis is technically correct but generic. For a
cert-manager renewal failure it suggests "check the Issuer", where your team
has a specific five-step check involving your internal PKI and a known
ClusterIssuer quirk.

This is not a prompt fix. A prompt is *how the agent reasons*; a skill is
*what your organisation knows*. Prompts stay short or the agent stops following
them — org procedure belongs in a skill.

**File:** `agents/skills/<skill-name>/SKILL.md`, plus `references/` and
`assets/`:

```markdown
---
name: cert-manager-renewal-triage
description: Diagnose cert-manager certificate renewal failures on our AKS clusters. Use when a Certificate is not Ready, an Order or Challenge is stuck, or a workload reports an expired or untrusted certificate.
---

# cert-manager renewal triage

## Check in this order

1. `Certificate` status conditions — `Ready`, and `Issuing` if a renewal is
   in flight.
2. The `CertificateRequest` for the current revision; a stuck request usually
   names the real error in its conditions.
3. The `Order` and its `Challenge` objects. A pending DNS-01 challenge on our
   internal zones is almost always the external-dns propagation delay below,
   not a cert-manager fault.
4. Our internal ClusterIssuer `{{INTERNAL_ISSUER_NAME}}` rate-limits to
   {{N}} issuances per hour per FQDN. A burst of renewals after a mass restart
   will queue; that is expected and self-resolves.
5. Only after 1-4 are clean, look at the workload's mounted Secret and whether
   Reloader restarted the consuming pod.

## Do not

- Do not recommend deleting the Certificate or Secret to "force renewal";
  on our issuer that consumes rate-limit budget and can extend the outage.
```

**Attach it** by adding the built image to the Agent's `spec.skills.refs`:

```diff
  spec:
+   skills:
+     refs:
+       - {{REGISTRY}}/platform/cert-manager-renewal-triage:v1
    declarative:
      modelConfig: default-model-config
```

`agents/skills/skills-as-images/README.md` explains why this repo prefers
image refs to `gitRefs` on AKS: image pulls use the **node's** CA trust store,
which already has the corporate root CA, while `gitRefs` runs `git clone`
inside a container that only trusts public CAs and fails against internal
GitLab/Gitea.

**Iterating on a skill is a version bump.** Edit `SKILL.md`, build and push a
new tag, bump the tag in the Agent manifest, merge. Never mutate a tag in
place — the agent's behaviour becomes untraceable and you lose the audit trail
that made the ticket reviewable.

---

#### 14. Evaluator — bad output keeps getting through

**You see:** several tickets where sections are filled with "N/A" or restate
the alert without evidence, yet the evaluation gate passed them.

**File:** `a2a-evaluation-gate/evaluation-agent.yaml`. Tighten the FAIL
criteria so the triage agent is forced to retry (it gets three attempts)
rather than the SRE catching it downstream:

```diff
+     FAIL if any required section is empty, "N/A", or restates the incident
+     input without citing a tool result. FAIL if "Likely cause" is asserted
+     without at least one tool output in "Evidence used". A correct BLOCKED or
+     low-confidence answer is a PASS; an unevidenced confident answer is not.
```

Add the failing output to `tests/` as a fixture first, so you can prove the
tightened criteria rejects it and that a good output still passes.

### Choosing the brake, when several would work

Escalate through the cheapest one that actually fixes the observed problem:

1. tighten the Vector `incident_signals` condition — stops at source;
2. widen the `delivery_key` / `dedupe_key` so more repeats collapse;
3. lower the Sensor `rateLimit` for that one route;
4. lower the semaphore in `config/04-workflow-concurrency.yaml`;
5. lengthen the claim window so one ticket covers a longer period.

Only 1 and 2 reduce volume. Options 3-5 delay work rather than remove it.
Narrow beats broad every time: one reason, one container, one namespace, one
route — never a tier downgrade for the whole fleet because one workload is
noisy.

### Making the change take effect

The reconciler applies the manifest. It does **not** always restart the pod
that reads it.

| Component | After merge |
|---|---|
| Alloy | **Restart required.** The config is a mounted ConfigMap and two env vars: `kubectl -n monitoring rollout restart deploy/alloy-vector-triage` |
| Vector | **Restart required.** `kubectl -n argo-events rollout restart deploy/vector-telemetry-triage` |
| Argo Sensor / EventSource | Automatic — the argo-events controller recreates the pod on spec change |
| WorkflowTemplate, semaphore, evaluation-settings ConfigMaps | Automatic — read at workflow submission, so the next incident uses the new value |
| kagent Agent (prompt, tools, skills) | Automatic — the kagent controller reconciles it; in-flight calls finish on the old prompt, the next call uses the new one |

If Reloader is installed on the cluster, annotate the Alloy and Vector
Deployments with `reloader.stakater.com/auto: "true"` and the two manual
restarts disappear. Until then, the restart is part of the change, not an
afterthought — a merged Vector filter that never restarted Vector has changed
nothing, and the queue will look identical.

### Verify the change, then close the loop

A green reconciliation is not evidence. Prove the new behaviour:

- **Suppression worked:** replay the signal from `fixtures/` (or wait for the
  next natural occurrence) and confirm no workflow is created. Watch
  `vector_component_discarded_events_total{component_id="suppress_exact_repeats"}`
  advancing and `vector_component_sent_events_total{component_id="kafka"}` not.
- **Detection still works:** run `scripts/smoke-test.sh` — a sustained or
  higher-impact failure of the same class must still create a workflow and a
  ticket. A suppression with no such test is an outage waiting to be silent.
- **Agent improved:** re-run the evaluation fixture that failed before the
  change and show it passing.

Then link the merge request and the verification evidence back onto the
canonical GitLab issue, and set the outcome. The issue is not closed until the
change is live and verified.

### Rules for suppression changes

1. Every suppression carries an owner, a rationale, and a review date in the
   commit message or the manifest comment.
2. Every suppression ships with a test proving a real failure still fires.
3. Never suppress a signal solely because nobody has been reviewing it.
4. Prefer the narrowest change that fixes the observed problem: one reason, one
   namespace, one route — not a tier downgrade for the whole fleet.
5. Revert is a merge request too. If a suppression hid a real incident, revert
   it and record that in the same issue.

## Copyable GitLab review template

Append this to the agent draft or use it in the canonical tracking issue:

```markdown
## SRE review

- Reviewer: @{{SRE_REVIEWER}}
- Reviewed at: {{ISO_8601_TIMESTAMP}}
- Canonical issue: {{THIS_ISSUE_OR_LINK}}
- Related incident/change: {{LINK_OR_NONE}}
- Outcome: {{ONE_OUTCOME_FROM_GUIDE}}
- Priority/severity: {{TEAM_CLASSIFICATION}}
- Owner: @{{ACTION_OWNER}}
- Re-review date: {{DATE_OR_NOT_REQUIRED}}

### Validation performed

- Target verified: {{YES_NO_AND_METHOD}}
- Current condition: {{PRESENT_RECOVERED_NOT_REPRODUCED_UNKNOWN}}
- Impact verified: {{EVIDENCE_OR_NONE}}
- Evidence checked: {{SANITIZED_COMMAND_RESULT_DASHBOARD_OR_RUNBOOK_LINKS}}

### SRE conclusion

{{WHAT_IS_ACTUALLY_HAPPENING_AND_WHY_THIS_OUTCOME_WAS_SELECTED}}

### Action and verification

{{ACTION_TAKEN_OR_TRACKED_OR_REASON_NO_ACTION_WAS_REQUIRED}}

### Agent assessment

- Targeting: {{CORRECT_INCORRECT_UNKNOWN}}
- Evidence quality: {{USEFUL_PARTIAL_POOR}}
- Diagnosis quality: {{CORRECT_PARTIAL_INCORRECT_UNPROVEN}}
- Recommendation quality: {{USEFUL_NEEDS_CHANGE_UNSAFE_NOT_APPLICABLE}}
- Time or effort saved: {{SHORT_DESCRIPTION_OR_NONE}}
- Agent improvement: {{ONE_SPECIFIC_CHANGE_OR_NO_AGENT_CHANGE}}
- Alert/source improvement: {{ONE_SPECIFIC_CHANGE_OR_NO_SOURCE_CHANGE}}

### GitOps change

- Change needed: {{YES_NO}}
- Layer: {{ALLOY_VECTOR_ARGO_AGENT_PROMPT_AGENT_SKILL_AGENT_TOOLS_NONE}}
- File and knob: {{PATH_AND_FIELD_OR_NONE}}
- Merge request: {{LINK_OR_NONE}}
- Restart required: {{ALLOY_VECTOR_NONE}}
- Applied at: {{ISO_8601_TIMESTAMP_OR_NOT_YET}}
- Verification evidence: {{FIXTURE_REPLAY_METRIC_OR_SMOKE_RESULT}}
- Detection still proven: {{YES_AND_HOW_OR_NOT_APPLICABLE}}
- Suppression owner / review date: {{OWNER_AND_DATE_OR_NOT_APPLICABLE}}
```

## Reducing repeated noise

Do not solve noise by silently ignoring the queue or broadly disabling useful
monitoring. Identify the source and preserve detection of genuine impact.

For repeated findings:

1. Group occurrences under one canonical issue using a stable fingerprint such
   as environment, cluster, namespace, stable workload identity, condition,
   and likely source. Avoid literal pod names because normal pod replacement
   changes them.
2. Measure occurrence count, duration, affected targets, and whether each event
   self-resolved or required action.
3. Determine whether duplication is introduced by the alert rule, log pipeline,
   event router, triage invocation, agent, or GitLab creation step.
4. Choose the narrowest safe treatment: aggregation window, cooldown,
   inhibition, stable deduplication key, severity adjustment, transient grace
   period, expected-change suppression, or routing correction. The concrete
   knobs and their files are listed in
   [Applying feedback via GitOps](#applying-feedback-via-gitops); prefer the
   Vector-side brakes, which remove volume, over the Argo-side brakes, which
   only slow it down.
5. Give every suppression an owner, rationale, review date, and a test showing
   that a sustained or higher-impact failure will still fire.
6. Validate the changed rule with real produced and received evidence. A valid
   manifest, a green reconciliation, or a successful deployment alone does not
   prove that noise stopped or that important alerts still work — and for Alloy
   and Vector it does not even prove the new config is loaded.

Never suppress an alert solely because nobody has been reviewing it.

## Weekly improvement review

Keep the meeting short and evidence-led. Review:

- new outputs, reviewed outputs, and still-unowned outputs;
- confirmed/actioned rate and false-positive rate;
- duplicate and repeated-occurrence rate;
- time to first SRE review and time to disposition;
- `BLOCKED_VALIDATION` causes;
- examples where the agent saved effort;
- top agent-quality failures and alert-source noise;
- overdue remediation, evaluation, or suppression-review actions;
- GitOps changes merged since the last review, and what each one measurably
  did to volume, duplicate rate, or agent quality;
- reviews that recorded a needed change but never raised a merge request; and
- one or two bounded improvements to make next.

Do not use raw issue volume as the success measure. The useful outcomes are
faster validated detection, safer investigation, reduced repeated noise, clear
ownership, and demonstrated improvements from completed feedback.

## Definition of done for an agent output

An output is complete only when:

- it has a named reviewer and canonical tracking location;
- the target and current condition were independently checked;
- one standard outcome and supporting evidence were recorded;
- any required operational action has an owner and verification criteria;
- agent quality and alert-source quality were assessed separately;
- concrete feedback was routed to the correct owner;
- any required system change was merged as a GitOps change, applied to the
  cluster (including the Alloy or Vector restart where one is needed), and
  verified against a fixture or live signal; and
- duplicate or noisy conditions have a tracked tuning decision rather than
  being left to fire indefinitely.

A recommendation that never became a merge request is not feedback. The whole
point of this loop is that the reviewing SRE can change the system on the same
day, without waiting on anyone else.
