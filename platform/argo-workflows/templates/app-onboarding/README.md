# App Onboarding System

Universal application onboarding for Kubernetes. Three input modes, all getting the same platform guardrails, deterministic execution, and post-deploy validation.

| Mode | Input | Best For |
|------|-------|----------|
| **Payload-driven** | JSON payload (form, curl, API) | New apps, greenfield |
| **Manifest-driven** | Git repo with YAML / inline files | Existing apps with raw YAML |
| **Helm-driven** | Helm chart + values | Existing apps using Helm |

## Architecture

```
Three input paths:
  Form → JSON payload        (Mode 1)
  Git repo → YAML manifests  (Mode 2)
  Helm chart → values.yaml   (Mode 3)
         |
    POST /onboard-app (webhook)
         |
    Argo Events EventSource (port 12000)
         |
    Sensor → Argo WorkflowTemplate (DAG)
         |
    ┌────┴─────────────────────────────────────┐
    |  Platform (always)     App (varies)       |
    |  - Namespace           Mode 1: templates  |
    |  - ResourceQuota       Mode 2: kubectl    |
    |  - NetworkPolicy       Mode 3: helm       |
    |  - SA + WI                                |
    |  - RBAC                Azure (ASO opt-in) |
    |  - Labels              - Identity         |
    |                        - FedCred          |
    |                        - RoleAssignments  |
    └───────────────────────────────────────────┘
         |
    Testing (3 layers)
    - Common: HTTP 200, DNS, port, health endpoint
    - Platform: replicas, endpoints, no crashes
    - App: team-provided smoke tests
         |
    KAgent validates deployment
         |
    Notification (Teams/Slack)
```

## Quick Start

### 1. Deploy RBAC + WorkflowTemplate + payload schema

```bash
kubectl apply -f app-onboarding-rbac.yaml
kubectl apply -f app-onboarding-template.yaml
kubectl apply -k schemas/   # generates golden-path-payload-schema ConfigMap
```

The `schemas/` kustomization bakes `golden-path-payload.schema.json` into a `ConfigMap` named `golden-path-payload-schema` in the `argo` namespace. The WorkflowTemplate mounts it (optional volume) into the `validate-payload` step, which fails the workflow with a clear schema error before any cluster state is mutated. If the ConfigMap is missing, validation will surface a "schema not mounted" error — apply the kustomization to fix.

### 2. Deploy Sensor

```bash
kubectl apply -f app-onboarding-sensor.yaml
```

### 3. Update EventSource (adds /onboard-app endpoint)

```bash
kubectl apply -f ../argo-events/04-eventsource.yaml
```

### 4. Test with curl

```bash
# Port forward to EventSource
kubectl port-forward -n argo-events svc/namespace-onboarding-webhook-eventsource-svc 12000:12000

# Submit minimal payload
curl -X POST http://localhost:12000/onboard-app \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $WEBHOOK_TOKEN" \
  -d @sample-payloads/minimal.json

# Submit full app payload
curl -X POST http://localhost:12000/onboard-app \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $WEBHOOK_TOKEN" \
  -d @sample-payloads/app-only.json
```

### 5. Direct workflow submission (without Argo Events)

```bash
# Port forward to Argo Server
kubectl port-forward -n argo svc/argo-server 2746:2746

# Submit workflow directly
PAYLOAD=$(cat sample-payloads/minimal.json | jq -c .)
curl -X POST https://localhost:2746/api/v1/workflows/argo/submit \
  -H "Content-Type: application/json" \
  -k \
  -d "{
    \"namespace\": \"argo\",
    \"resourceKind\": \"WorkflowTemplate\",
    \"resourceName\": \"app-onboarding-template\",
    \"submitOptions\": {
      \"parameters\": [\"payload=${PAYLOAD}\"]
    }
  }"
```

## Payload Schema

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `metadata.name` | string | Unique onboarding request name |
| `metadata.swc` | string | Service/cost center code |
| `metadata.environment` | enum | `DEV`, `STAGING`, `PROD` |
| `metadata.owner` | string | Team or group owning this namespace |
| `metadata.requestedBy` | string | Email of the person requesting |
| `metadata.requestedAt` | string | ISO 8601 timestamp (`2026-01-15T10:00:00Z`) |
| `namespace.name` | string | Target namespace (max 63 chars, RFC 1123) |

### Optional Metadata

| Field | Type | Description |
|-------|------|-------------|
| `metadata.costCenter` | string | Cost center code if different from `swc` |

### Optional Sections (skipped if absent)

| Section | What It Creates |
|---------|----------------|
| `serviceAccount` | SA with optional workload identity |
| `rbac` | RoleBinding for AD group |
| `application` | Deployment + ConfigMap |
| `networking.service` | ClusterIP or LoadBalancer |
| `networking.istio` | VirtualService + CORS |
| `azure` | ASO: Identity + FedCred + RoleAssignments |

### Sample Payloads

| File | Scenario |
|------|----------|
| `sample-payloads/minimal.json` | Namespace + quota + netpol only |
| `sample-payloads/app-only.json` | + deployment + service |
| `sample-payloads/istio-enabled.json` | + Istio VirtualService |
| `sample-payloads/full-stack-with-azure.json` | + ASO Azure resources |

## DAG Flow

```
parse-payload → validate-payload
  → create-namespace (when createIfNotExists)
    → create-quota
    → create-netpol
    → create-service-account (when serviceAccount present)
    → create-rbac (when rbac present)
    → create-configmap (when configMap present)
      → create-deployment (when application present)
        → create-service (when service present)
          → create-virtualservice (when istio.enabled)
        → validate-deployment (KAgent)
  → create-managed-identity (when azure.enabled)
    → wait-for-identity
      → create-federated-credential
      → create-role-assignments
  → store-config-gitops
  → send-notification (exit handler)
```

## Files

| File | Purpose |
|------|---------|
| `app-onboarding-template.yaml` | Master WorkflowTemplate (DAG) |
| `app-onboarding-rbac.yaml` | ServiceAccount + ClusterRole + Binding |
| `app-onboarding-sensor.yaml` | Argo Events Sensor for /onboard-app |
| `schemas/golden-path-payload.schema.json` | JSON Schema (Draft 2020-12) for the payload contract |
| `schemas/kustomization.yaml` | Generates `golden-path-payload-schema` ConfigMap from the schema file |
| `sample-payloads/*.json` | Test payloads for each scenario |
| `BACKLOG.md` | Prioritised backlog from 7-agent software factory review |

## Golden Path Pipeline

This template is **Phase 2** of a 5-phase application onboarding pipeline:

```
Phase 1: app-intake-agent           → writes _phase1_intake into payload
Phase 2: app-onboarding-template    ← THIS TEMPLATE — writes _phase2_infrastructure
Phase 3: app-hardening-agent (PR)   → writes _phase3_hardening
Phase 4: app-release-template       → writes _phase4_deployment
Phase 5: certify-app-<name>         → writes _phase5_certification (AppCertificationV1 KRO RGD)
```

Each phase appends a `_phaseN_*` block to the shared payload — never overwrites earlier phases. The payload schema at `schemas/golden-path-payload.schema.json` is the cross-phase contract. The Phase 5 cert RGD lives at `infra-stack/kro-stack/definitions/app-certification-v1.yaml`.

## Key Design Decisions

- **Three input modes** — payload, manifests, or Helm. Meet teams where they are.
- **Deterministic at runtime** — templates execute from parameters. No LLM generates YAML at deploy time.
- **Agents extend the library, not the runtime** — template factory agent builds + tests + PRs new templates offline. Human reviews. Then it's deterministic.
- **Conditional DAG** — `when:` clauses skip branches; `depends:` with `.Skipped` handling for correct cascading
- **Idempotent** — all templates use `kubectl apply`, safe to re-submit
- **ASO opt-in** — `azure.enabled` defaults to `false` (cost protection)
- **Tests encouraged** — platform offers common checks (HTTP 200, DNS, port, health); teams add their own smoke tests

## Agent Touchpoints

### Build Time (offline, PR-based)

| Agent | Role |
|-------|------|
| `template-factory` | Builds new templates for unknown resource kinds, tests on dev cluster, creates PR |
| `template-updater` | Monitors API version changes, proposes template updates |
| `import-agent` | Scans existing YAML/Helm/namespace, generates onboarding payload |

### Runtime (during/after onboarding)

| Stage | Agent | Role |
|-------|-------|------|
| Pre-submit | `onboarding-advisor` | Guides form, suggests common tests, pre-fills for imports |
| Pre-submit | `policy-checker` | Validates against org policies |
| Mode 2/3 | `manifest-validator` | Policy gate for team-provided YAML/Helm |
| Post-deploy | `sre-triage-agent` | Validates deployment health via KAgent A2A |
| On failure | `sre-triage-agent` | Diagnoses why onboarding failed |
| Ongoing | `drift-detector` | Compares live vs stored config |

**Agents provide intelligence. Templates do the work.**
