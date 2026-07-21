# Adding Namespace Agents

How to add new namespace-specific AI agents to the kagent triage pipeline.

---

## Overview

Each Kubernetes namespace can have its own AI diagnostic agent with **domain-specific knowledge**. For example:
- A `cert-manager` agent knows about Certificate, Issuer, and ACME challenges
- A `monitoring` agent knows about Prometheus, Grafana, and alerting
- A `prod-apps` agent knows about your application's specific failure modes

Three methods are available — choose based on your audience:

| Method | Best for | Output |
|--------|----------|--------|
| [Method 1: Interactive Builder (KAgent UI)](#method-1-interactive-builder-kagent-ui) | Any team — expert or newcomer | Agent CRD via chat interview |
| [Method 2: Claude Code Skill](#method-2-claude-code-skill) | Platform engineers in Claude Code | Agent CRD via Claude interview |
| [Method 3: Script automation](#method-3-using-the-openclaw-skill-script) | Known namespace, fast generation | Agent CRD + Sensor + test manifest |
| [Method 4: Manual YAML](#method-4-manual-yaml-creation) | Full control | Raw YAML |

---

## Method 1: Interactive Builder (KAgent UI)

Two builder agents are deployed on the cluster and accessible via the KAgent UI or A2A API.

**`byoa-builder-expert`** — for engineers who know Kubernetes. Fast 3-round interview, generates YAML, can apply directly.

**`byoa-builder-guided`** — for teams new to the platform. Plain-English 7-topic flow, output goes via PR review.

```bash
# Chat with the expert builder. The helper handles the port-forward, JSON-RPC
# framing, required trailing slash, and reply extraction; use --raw when you
# need the builder's structured question payload.
scripts/kagent-a2a-invoke.sh --agent byoa-builder-expert \
  --text 'Build me a triage agent for my namespace'
```

See [BYOA-SELF-SERVICE.md](./BYOA-SELF-SERVICE.md) for the full guide including the onboarding contract, routing, and testing.

---

## Method 2: Claude Code Skill

In Claude Code, invoke the `byoa-agent-builder` skill. It runs the same structured interview and generates a validated Agent CRD.

```
/byoa-agent-builder
```

or just describe what you need in natural language. The skill lives at `agents/skills/byoa-agent-builder/`.

---

## Method 3: Using the OpenClaw Skill Script

The `create-agent.sh` script automates manifest generation, deployment, and testing.

**Location:** `agents/skills/kagent-namespace-agent/scripts/create-agent.sh` (run from the repo root)

### Generate Manifests Only

```bash
agents/skills/kagent-namespace-agent/scripts/create-agent.sh \
  --namespace cert-manager \
  --description "TLS certificate lifecycle management using cert-manager. Handles Certificate, Issuer, ClusterIssuer, CertificateRequest resources. Common issues: failed ACME challenges, expired certificates, issuer not ready, secret not found."
```

**Output:**
```
🤖 Creating kagent agent for namespace: cert-manager
   Description: TLS certificate lifecycle management...

✅ Generated: ./cert-manager-agent.yaml
✅ Generated: ./cert-manager-sensor.yaml
✅ Generated: ./cert-manager-test-error.yaml

📁 Files created in: .
```

### Generate, Deploy, and Test

```bash
agents/skills/kagent-namespace-agent/scripts/create-agent.sh \
  --namespace cert-manager \
  --description "TLS certificate lifecycle management using cert-manager" \
  --deploy \
  --test
```

This will:
1. Generate the three YAML files
2. Apply them to the cluster (`--deploy`)
3. Port-forward to kagent controller
4. Find the agent ID
5. Send a test diagnostic query (`--test`)

### Script Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--namespace` | ✅ | — | Target K8s namespace |
| `--description` | ✅ | — | Domain description for the system prompt |
| `--context` | | `{{CLUSTER_NAME}}` | kubectl context |
| `--kagent-ns` | | `kagent` | Namespace where kagent is installed |
| `--model-config` | | `default-model-config` | ModelConfig CR to reference |
| `--deploy` | | `false` | Deploy to cluster after generation |
| `--test` | | `false` | Run E2E test (implies `--deploy`) |
| `--output-dir` | | `.` (current dir) | Where to save generated files |

### Examples

```bash
# Monitoring stack
./create-agent.sh \
  --namespace monitoring \
  --description "Observability stack: Prometheus, Grafana, Loki, Alloy. Common issues: high cardinality, scrape target down, storage full, OOM on Prometheus."

# Application namespace
./create-agent.sh \
  --namespace prod-apps \
  --description "Production application workloads. Spring Boot microservices with PostgreSQL. Common issues: database connection pools exhausted, health check failures, memory leaks."

# Argo namespace
./create-agent.sh \
  --namespace argo \
  --description "Argo Workflows controller and server. Common issues: workflow pods stuck, executor errors, artifact storage failures, workflow timeouts."

# Custom output and context
./create-agent.sh \
  --namespace istio-system \
  --description "Istio service mesh control plane" \
  --context aks-prod \
  --output-dir agents/kagent-triage/ \
  --deploy
```

---

## Method 2: Manual YAML Creation

If you prefer to craft manifests manually, follow these steps.

### Step 1: Create the Agent CR

Use `01-test-agent.yaml` as a template. Key fields to customise:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: cert-manager-agent                    # <namespace>-agent
  namespace: kagent
  labels:
    app.kubernetes.io/name: cert-manager-agent
    app.kubernetes.io/part-of: kagent
    kagent-triage: enabled
    managed-namespace: cert-manager            # Used by find-agent step
spec:
  description: "Diagnostic agent for cert-manager namespace"
  type: Declarative
  declarative:
    a2aConfig:
      skills:
        - id: cert-manager-diagnostics
          name: Cert Manager Diagnostics
          description: "Diagnose certificate, issuer, and ACME challenge issues"
          tags: [cert-manager, tls, certificates]
          examples:
            - "Why is my Certificate not ready?"
            - "Debug ACME challenge failure"
    deployment:
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          cpu: 500m
          memory: 512Mi
    modelConfig: default-model-config          # Must exist in kagent ns
    systemMessage: |
      # Kubernetes Diagnostic Agent for cert-manager Namespace

      You are a Kubernetes diagnostic agent specialized in the cert-manager namespace.
      
      ## Your Domain
      TLS certificate lifecycle management using cert-manager. You handle:
      - Certificate resources and their status
      - Issuer and ClusterIssuer configuration
      - ACME challenges (HTTP-01, DNS-01)
      - CertificateRequest lifecycle
      - Secret management for TLS certificates
      
      ## Common Issues
      - Failed ACME challenges (DNS propagation, firewall rules)
      - Expired certificates (renewal failures)
      - Issuer not ready (missing credentials, wrong config)
      - Secret not found (namespace mismatch, name typo)
      - Rate limiting from Let's Encrypt
      
      ## Response Format
      - **🔍 Issue**: One-line summary
      - **📋 Affected Resource**: namespace/kind/name
      - **🔬 Root Cause**: What went wrong and why
      - **🛠️ Remediation**: Step-by-step fix
      - **⚠️ Risk Level**: Low/Medium/High
      - **✅ Verification**: How to confirm the fix worked
      
      ## Safety
      - Never delete certificates or secrets without confirmation
      - Prefer checking issuer status before modifying certificates
      - Stay within the cert-manager namespace unless investigating dependencies
    tools:
      - mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: kagent-tool-server
          toolNames:
            - k8s_get_resources
            - k8s_get_pod_logs
            - k8s_describe_resource
            - k8s_get_resource_yaml
            - k8s_get_events
            - k8s_check_service_connectivity
            - k8s_get_available_api_resources
            - k8s_get_cluster_configuration
            # Add write tools only if agent should remediate:
            # - k8s_patch_resource
            # - k8s_apply_manifest
            # - k8s_delete_resource
        type: McpServer
```

**Tips for the system prompt:**
- Be specific about the namespace's domain (what runs there, what CRDs exist)
- List common failure modes so the agent knows what to look for
- Include the response format for consistent output
- Add safety constraints relevant to the namespace

### Step 2: Create the Sensor

> **⚠️ REQUIRED SAFEGUARDS**: Every sensor MUST include PolicyViolation filter + rate limit.
> See [SENSOR-SAFEGUARDS.md](./SENSOR-SAFEGUARDS.md) for details on preventing cascade loops.

Create a sensor that filters events for the new namespace:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Sensor
metadata:
  name: kagent-triage-cert-manager          # kagent-triage-<namespace>
  namespace: argo-events
  labels:
    app: kagent-triage
    kagent-triage/namespace: cert-manager
spec:
  eventBusName: default
  dependencies:
    - name: k8s-events
      eventSourceName: k8s-warning-events    # Or azure-eventhub-events on AKS
      eventName: warning-events
      filters:
        data:
          - path: body.involvedObject.namespace
            type: string
            value:
              - cert-manager                 # Filter for this namespace
          - path: body.reason               # REQUIRED: prevent PolicyViolation cascade
            type: string
            comparator: "!="
            value:
              - "PolicyViolation"
  triggers:
    - template:
        name: kagent-triage-cert-manager
        argoWorkflow:
          operation: submit
          source:
            resource:
              apiVersion: argoproj.io/v1alpha1
              kind: Workflow
              metadata:
                generateName: kagent-triage-cert-manager-
                labels:
                  triggered-by: kagent-triage-sensor
              spec:
                serviceAccountName: argo-events-sa
                workflowTemplateRef:
                  name: kagent-triage
                arguments:
                  parameters:
                    - name: event-namespace
                      value: ""
                    - name: event-name
                      value: ""
                    - name: event-reason
                      value: ""
                    - name: event-message
                      value: ""
                    - name: resource-kind
                      value: ""
                    - name: resource-name
                      value: ""
          parameters:
            - dest: spec.arguments.parameters.0.value
              src:
                dataKey: body.involvedObject.namespace
                dependencyName: k8s-events
            - dest: spec.arguments.parameters.1.value
              src:
                dataKey: body.involvedObject.name
                dependencyName: k8s-events
            - dest: spec.arguments.parameters.2.value
              src:
                dataKey: body.reason
                dependencyName: k8s-events
            - dest: spec.arguments.parameters.3.value
              src:
                dataKey: body.message
                dependencyName: k8s-events
            - dest: spec.arguments.parameters.4.value
              src:
                dataKey: body.involvedObject.kind
                dependencyName: k8s-events
            - dest: spec.arguments.parameters.5.value
              src:
                dataKey: body.involvedObject.name
                dependencyName: k8s-events
      policy:
        allow:
          duration: 12s                      # Rate limit: 5/minute
```

### Step 3: Deploy

```bash
kubectl apply -f cert-manager-agent.yaml
kubectl apply -f cert-manager-sensor.yaml
```

### Step 4: Verify

```bash
# Gates on Accepted -> Ready -> listed by the controller API -> smoke reply,
# one PASS/FAIL line per gate
scripts/kagent-verify-agent.sh --agent cert-manager-agent \
  --smoke 'Check the status of all certificates in cert-manager namespace'

# Sensor pod running
kubectl get pods -n argo-events -l sensor-name=kagent-triage-cert-manager
```

### Step 5: Test

```bash
# Safe end-to-end fault test: pre-checks the sensor is idle, injects the
# fixture, waits for the triage workflow, and ALWAYS cleans up the fixture
scripts/kagent-e2e-fault-test.sh --namespace cert-manager --fixture cert-manager-test-error.yaml

# Or query the agent directly (the session/chat API is broken on kagent
# v0.8.0-beta4 — the helper uses the working A2A protocol)
scripts/kagent-a2a-invoke.sh --agent cert-manager-agent \
  --text 'Check the status of all certificates in cert-manager namespace'
```

---

## Agent Discovery Logic

The `find-agent` step in the WorkflowTemplate discovers agents using this priority:

1. **Name match:** Agent name contains the event namespace (e.g., `cert-manager-agent` for `cert-manager` events)
2. **Label match:** Agent has label `managed-namespace: cert-manager`
3. **Fallback:** Uses `k8s-agent` (cluster-wide generic agent)
4. **Last resort:** First available agent

To ensure your agent is discovered correctly, use **either** the naming convention (`<namespace>-agent`) **or** the `managed-namespace` label (or both).

---

## Template Reference

The skill uses three templates located at `agents/skills/kagent-namespace-agent/templates/`:

### `agent.yaml.tmpl`
- kagent Agent CR with placeholder system prompt
- Placeholders: `{{NAMESPACE}}`, `{{NAMESPACE_TITLE}}`, `{{KAGENT_NS}}`, `{{MODEL_CONFIG}}`, `{{DESCRIPTION}}`

### `sensor.yaml.tmpl`
- Argo Sensor with namespace filter and workflow trigger
- Placeholders: `{{NAMESPACE}}`

### `test-error.yaml.tmpl`
- Three test resources: ImagePullBackOff deployment, CrashLoopBackOff pod, OOMKilled pod
- Placeholders: `{{NAMESPACE}}`

---

## Suggested Namespace Agents

| Namespace | Description | Priority |
|-----------|-------------|----------|
| `cert-manager` | TLS certificate lifecycle, ACME challenges, issuer config | High |
| `monitoring` | Prometheus, Grafana, Loki, Alloy — observability stack | High |
| `argo` | Argo Workflows controller, executor pods, artifacts | Medium |
| `argo-events` | EventSource, Sensor, EventBus health | Medium |
| `ingress-nginx` / `traefik` | Ingress controller, routing, TLS termination | Medium |
| `external-secrets` | ESO, SecretStore connectivity, sync failures | Medium |
| `kube-system` | CoreDNS, kube-proxy, system components | Low (noisy) |

**Warning:** `kube-system` generates many events. Use aggressive rate limiting or filter by specific reasons to avoid workflow floods.

---

## Removing a Namespace Agent

```bash
# Remove sensor first (stops triggering workflows)
kubectl delete sensor kagent-triage-cert-manager -n argo-events

# Remove agent
kubectl delete agent cert-manager-agent -n kagent

# Clean up test resources (if deployed)
kubectl delete -f cert-manager-test-error.yaml
```
