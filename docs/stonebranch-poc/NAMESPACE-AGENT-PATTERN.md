# Per-Namespace Agent Pattern

## Overview

Instead of shared cluster-wide agents or per-pod sidecars, deploy **one UAG agent per namespace** that opts in. This gives namespace-level isolation with platform-controlled deployment.

## How It Works

```
Platform team controls:           App team controls:
- Agent image version             - Opt-in annotation
- OMS address                     - Nothing else
- RBAC scope
- Resource limits

App team adds annotation ──→ Agent auto-deployed ──→ Registers with Controller
```

## Opt-In Mechanism

App teams add an annotation to their namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-alpha
  annotations:
    stonebranch.com/agent-enabled: "true"
  labels:
    stonebranch.com/agent-enabled: "true"   # for NetworkPolicy selectors
```

## What Gets Deployed Per Namespace

When a namespace opts in, the following resources are created:

### 1. ServiceAccount (namespace-scoped only)

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: uag-agent
  namespace: {{ namespace }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: uag-agent
  namespace: {{ namespace }}
rules:
  # Read-only by default — Controller jobs can only observe
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
  # Add exec only if needed (discuss with Stonebranch team)
  # - apiGroups: [""]
  #   resources: ["pods/exec"]
  #   verbs: ["create"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: uag-agent
  namespace: {{ namespace }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: uag-agent
subjects:
  - kind: ServiceAccount
    name: uag-agent
    namespace: {{ namespace }}
```

### 2. Agent Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uag-agent
  namespace: {{ namespace }}
  labels:
    app: uag-agent
    managed-by: platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app: uag-agent
  template:
    metadata:
      labels:
        app: uag-agent
    spec:
      serviceAccountName: uag-agent
      initContainers:
      - name: patch-config
        image: stonebranch/universal-agent:8.0.0.0-debian
        command: ["sh", "-c"]
        args:
        - |
          cp -a /etc/universal/* /config/
          sed -i 's|^oms_servers.*|oms_servers 7878@{{ oms_address }}|' /config/uags.conf
          sed -i "s|^netname.*|netname {{ namespace }}-agent|" /config/uags.conf
        volumeMounts:
        - name: universal-config
          mountPath: /config
      containers:
      - name: uag
        image: stonebranch/universal-agent:8.0.0.0-debian
        volumeMounts:
        - name: universal-config
          mountPath: /etc/universal
        ports:
        - containerPort: 7887
        resources:
          requests:
            cpu: 50m
            memory: 128Mi
          limits:
            cpu: 250m
            memory: 256Mi
        livenessProbe:
          tcpSocket:
            port: 7887
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          tcpSocket:
            port: 7887
          initialDelaySeconds: 15
          periodSeconds: 5
      volumes:
      - name: universal-config
        emptyDir: {}
```

### 3. NetworkPolicy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: uag-agent-egress
  namespace: {{ namespace }}
spec:
  podSelector:
    matchLabels:
      app: uag-agent
  policyTypes:
  - Egress
  - Ingress
  egress:
  # Allow agent to reach OMS only
  - to:
    - ipBlock:
        cidr: {{ oms_ip }}/32
    ports:
    - port: 7878
      protocol: TCP
  # Allow DNS
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - port: 53
      protocol: UDP
  ingress: []   # No inbound traffic to agent
```

## Security Model

```
┌─────────────────────────────────────────────────────┐
│                    ISOLATION LAYERS                   │
│                                                       │
│  1. Kubernetes RBAC                                   │
│     Agent SA can ONLY access its own namespace         │
│     Read-only by default, exec opt-in                 │
│                                                       │
│  2. NetworkPolicy                                     │
│     Agent can ONLY talk to OMS (egress whitelist)     │
│     No ingress to agent                              │
│     Cannot reach pods in other namespaces             │
│                                                       │
│  3. Controller RBAC                                   │
│     UC controls who can define/trigger jobs           │
│     Jobs are scoped to specific agent names           │
│     Audit trail of all executions                     │
│                                                       │
│  4. Agent naming = namespace name                     │
│     team-alpha-agent can only run team-alpha jobs     │
│     Convention enforced by Controller job definitions │
└─────────────────────────────────────────────────────┘
```

### What team A CANNOT do:

- Access team B's namespace (RBAC: Role, not ClusterRole)
- Send network traffic to team B's pods (NetworkPolicy: egress locked to OMS only)
- Trigger jobs on team B's agent (Controller RBAC: job→agent mapping)
- See team B's job results (Controller RBAC: visibility scoped)

### What the platform team controls:

- Agent image version (pinned, not `:latest`)
- OMS address (hardcoded in init container)
- RBAC scope (read-only default, exec opt-in per namespace)
- Resource limits (prevent agent from consuming app resources)
- NetworkPolicy (egress locked to OMS)
- Agent naming convention (namespace-based, predictable)

## Deployment Automation Options

### Option A: Argo Workflows (fits your existing platform)

Add a step to the namespace onboarding workflow:

```yaml
# In namespace-onboarding-template.yaml, add after create-namespace:
- name: deploy-stonebranch-agent
  template: deploy-agent
  when: "{{tasks.parse-payload.outputs.parameters.stonebranch_enabled}} == true"
  arguments:
    parameters:
    - name: namespace
      value: "{{tasks.parse-payload.outputs.parameters.namespace}}"
    - name: oms_address
      value: "{{OMS_HOSTNAME}}"
```

### Option B: Kyverno Generate Policy (declarative)

Kyverno watches for the annotation and auto-generates agent resources:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-stonebranch-agent
spec:
  rules:
  - name: deploy-agent-on-annotation
    match:
      resources:
        kinds:
        - Namespace
        annotations:
          stonebranch.com/agent-enabled: "true"
    generate:
      kind: Deployment
      name: uag-agent
      namespace: "{{request.object.metadata.name}}"
      data:
        # ... agent deployment spec
```

### Option C: Flux/ArgoCD GitOps (your existing stack)

Add agent manifests to the GitOps repo per namespace:

```
apps/
├── team-alpha/
│   ├── namespace.yaml
│   ├── stonebranch/           # ← added when team opts in
│   │   ├── deployment.yaml
│   │   ├── serviceaccount.yaml
│   │   ├── role.yaml
│   │   └── networkpolicy.yaml
├── team-beta/
│   ├── namespace.yaml         # no stonebranch/ dir = no agent
```

### Option D: Helm chart (template once, deploy many)

```bash
# Platform team runs per namespace
helm install uag-agent ./stonebranch-agent-chart \
  --namespace team-alpha \
  --set omsAddress={{OMS_HOSTNAME}} \
  --set agentName=team-alpha-agent
```

## Comparison: Shared vs Per-Namespace vs Sidecar

| Factor | Shared (cluster-wide) | Per-Namespace | Sidecar |
|--------|----------------------|---------------|---------|
| OMS connections | 2-5 | 1 per opted-in NS | 1 per pod |
| Isolation | None (cluster RBAC) | Namespace RBAC | Pod-level |
| Resource overhead | Low (~500MB total) | Medium (~128MB per NS) | High (~128MB per pod) |
| Scaling | Replicas on shared pool | 1 per NS (fixed) | Scales with app |
| Blast radius | Whole cluster | Single namespace | Single pod |
| Management | Simple | Medium | Complex |
| Onboarding | Nothing per team | Annotation + auto-deploy | Webhook injection |
| **Recommendation** | Dev/test, single team | **Production, multi-tenant** | Never |

## Resource Budget

For a cluster with 100 opted-in namespaces:

```
Per agent:  50m CPU request, 128Mi memory request
100 agents: 5 CPU, 12.8 Gi memory (requests)

Compare to sidecar (assuming 500 app pods):
500 agents: 25 CPU, 64 Gi memory — unacceptable
```

## Getting Started

1. Pick a deployment automation option (A/B/C/D above)
2. Get OMS address from Stonebranch team
3. Create the Helm chart or Kyverno policy or Argo workflow step
4. Have first team opt in with the annotation
5. Verify agent connects and appears in UC dashboard
6. Roll out to more teams
