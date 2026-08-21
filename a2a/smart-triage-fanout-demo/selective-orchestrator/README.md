# Selective read-only SRE orchestrator

This POC evolves the existing smart-triage Alertmanager/Argo Events path into a
deterministic selective investigation. Argo Workflows owns target validation,
budgets, concurrency and failure boundaries. Existing kagent specialists remain
the optional A2A reasoning plane. The POC creates no specialist Deployment and
contains no Kubernetes write tool.

```mermaid
flowchart LR
    A[Alertmanager or human report] --> E[Argo Events]
    E --> W[Argo Workflow]
    W --> T{Exact approved target?}
    T -->|No| B[BLOCKED_TARGET_CONTEXT<br/>zero kubectl calls]
    T -->|Yes| C[One request-specific<br/>credential preparation plan]
    C --> R[Deterministic allow-listed routing]
    R --> S[1-3 selected specialists<br/>or bounded full audit]
    S --> V[Validate Finding v1]
    V -->|invalid| F[SPECIALIST_CONTRACT_FAILED]
    V -->|valid| Y[PROVEN evidence]
    F --> P[Partial synthesis with UNKNOWN boundary]
    Y --> P
    P --> L[Issue 85 lifecycle decision]
    L --> G[One GitLab-ready report<br/>existing human alert preserved]
```

## Target boundary

An incident must resolve one approved registry row and provide an approved
namespace and stable workload unless it is explicitly cluster-scoped.
Conflicts or ambiguity produce `BLOCKED_TARGET_CONTEXT` before credentials or
kubectl.

The plan records exactly one command equivalent to:

```text
az aks get-credentials --subscription PROTECTED_RUNTIME_VALUE \
  --resource-group <approved-rg> --name <approved-cluster> \
  --file /tmp/aks-triage/<run-id>.kubeconfig --overwrite-existing
```

`--admin`, shared kubeconfig use, `az account set` and `kubectl config
use-context` are forbidden. The public fixture records the plan but does not
execute Azure or Kubernetes commands. A work-environment adapter must resolve
the protected subscription reference and execute the preparation once before
selected specialists run.

## Routing

| Signal | Selected capabilities |
|---|---|
| CrashLoop/OOM/ImagePull/NotReady | Kubernetes workload plus bounded log/metrics evidence |
| FailedScheduling/capacity | Kubernetes, deployment/placement and metrics evidence |
| Certificate/workload identity | Policy/identity plus Kubernetes evidence; no Secret/token retrieval |
| Job/CronJob | Kubernetes and deployment/controller evidence |
| Network/DNS/ingress | Network, Kubernetes and metrics evidence |
| Deployment/Flux/Helm | Deployment, GitOps draft and cited knowledge |
| Explicit full-health audit | All eight existing capabilities, concurrency capped at three |

Ordinary incidents are capped at three specialists. The deterministic fixture
measures three selected path calls for CrashLoop routing (two specialist steps
plus synthesis), compared with nine for unconditional eight-way fan-out plus
synthesis. Fixture mode makes zero model calls; live mode records the selected
specialist and commander A2A/model calls separately.

## Contracts and failure containment

- Every selected specialist result must satisfy the checked-in
  `smart-triage-finding/v1` runtime contract from issue #85.
- Invalid JSON or schema output becomes `SPECIALIST_CONTRACT_FAILED`.
- Timeout or access denial becomes an `UNKNOWN` evidence boundary and a
  `PARTIAL_EVIDENCE` report, never a false all-clear.
- Per-specialist output is capped at 4096 bytes and total synthesis evidence at
  16384 bytes. Truncation emits `TOOL_OUTPUT_TRUNCATED` with original and
  retained sizes and a narrowing instruction.
- Incident fields, logs and annotations are untrusted evidence. Prompt-like or
  credential-like input is detected and is not copied into finding evidence.
- Lifecycle `notify=false` suppresses all specialist and synthesis calls.
- `STATE_UNAVAILABLE` preserves the report/human-alert path and keeps ticket
  action at `NONE`.

## Modes

`fixture` is the public-safe default. It exercises real routing, contract
validation, concurrency, lifecycle calls, report generation and metrics using
deterministic specialist findings.

`live` sends A2A JSON-RPC only to selected existing specialist endpoints. Any
free-text or otherwise invalid response is rejected as
`SPECIALIST_CONTRACT_FAILED`; live agents must return one JSON Finding v1.
Neither mode executes remediation.

See [HOMELAB-EVIDENCE-2026-08-20.md](HOMELAB-EVIDENCE-2026-08-20.md) for the
Alertmanager-to-Workflow runs, routing/call-count measurements, blocked-target
proof and the Sensor integration defect found during live testing.

## Validate

```bash
sh a2a/smart-triage-fanout-demo/selective-orchestrator/verify.sh
kubectl apply --dry-run=server \
  -k a2a/smart-triage-fanout-demo/selective-orchestrator
```

## Install in the POC namespace

Install issue #85 first, then the selective WorkflowTemplate and updated
Sensor:

```bash
kubectl apply -k a2a/smart-triage-fanout-demo/finding-lifecycle
kubectl apply -k a2a/smart-triage-fanout-demo/selective-orchestrator
kubectl apply -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
```

Do not set `execution_mode=live` until the existing specialist Agents are
Ready, their prompts return Finding v1 JSON, the target-preparation adapter is
connected to the approved AKS-MCP flow, and the work environment has verified
read-only Azure/Kubernetes authorization.
