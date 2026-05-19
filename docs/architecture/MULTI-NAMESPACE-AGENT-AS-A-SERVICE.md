# KAgent — Multi-Namespace / Agent-as-a-Service

## Overview

The kagent controller runs in the `kagent` namespace. Tenant teams on the same cluster can use it by pointing at its service and creating `Agent` CRDs in their own namespace. No separate controller deployment required.

```
┌─────────────────────────────────────────────────────┐
│                     Cluster                         │
│                                                     │
│  ┌─────────────────────┐   ┌────────────────────┐  │
│  │  kagent namespace   │   │  tenant-a namespace │  │
│  │                     │◄──│                     │  │
│  │  kagent-controller  │   │  Agent CRDs         │  │
│  │  (ClusterRole)      │   │  (Role: kagent-     │  │
│  │                     │   │   tenant)           │  │
│  └─────────────────────┘   └────────────────────┘  │
│           ▲                                         │
│           │         ┌────────────────────┐          │
│           └─────────│  tenant-b namespace │          │
│                     │  Agent CRDs         │          │
│                     └────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## Service Discovery

Any pod in any namespace reaches the controller via:

```
kagent-controller.kagent.svc.cluster.local:<port>
```

No additional config needed for DNS resolution. Blocked only if NetworkPolicy or Istio AuthorizationPolicy restricts ingress to the `kagent` namespace.

---

## Required Permissions

### 1. Controller — ClusterRole (watch all namespaces)

The controller must have a `ClusterRole` (not a namespaced `Role`) to watch `Agent` objects across namespaces. Verify:

```bash
kubectl get clusterrolebinding -l app=kagent-controller
```

If missing, apply:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kagent-controller
rules:
  - apiGroups: ["kagent.dev"]
    resources: ["agents", "agentgateways", "modelconfigs", "skills"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: [""]
    resources: ["secrets", "configmaps"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kagent-controller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kagent-controller
subjects:
  - kind: ServiceAccount
    name: kagent-controller
    namespace: kagent
```

### 2. Tenant Namespace — Role (create/manage Agent CRDs)

Each tenant namespace needs a `Role` granting access to kagent CRDs, bound to the relevant service account or team:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kagent-tenant
  namespace: <tenant-namespace>
rules:
  - apiGroups: ["kagent.dev"]
    resources: ["agents", "agentgateways", "modelconfigs"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kagent-tenant
  namespace: <tenant-namespace>
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kagent-tenant
subjects:
  - kind: ServiceAccount
    name: <tenant-service-account>
    namespace: <tenant-namespace>
```

### 3. NetworkPolicy (if present)

If the `kagent` namespace has ingress restrictions, label tenant namespaces and add an allow rule:

```bash
# Label tenant namespace
kubectl label namespace <tenant-namespace> kagent-access=true
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-tenant-ingress
  namespace: kagent
spec:
  podSelector:
    matchLabels:
      app: kagent-controller
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kagent-access: "true"
```

### 4. Istio AuthorizationPolicy (if Istio present)

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: kagent-controller-access
  namespace: kagent
spec:
  selector:
    matchLabels:
      app: kagent-controller
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/<tenant-namespace>/sa/<tenant-sa>"
```

---

## Onboarding a New Tenant Namespace

```bash
# 1. Label namespace for NetworkPolicy
kubectl label namespace <tenant-namespace> kagent-access=true

# 2. Apply tenant RBAC
kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kagent-tenant
  namespace: <tenant-namespace>
rules:
  - apiGroups: ["kagent.dev"]
    resources: ["agents", "agentgateways", "modelconfigs"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kagent-tenant
  namespace: <tenant-namespace>
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kagent-tenant
subjects:
  - kind: ServiceAccount
    name: <tenant-service-account>
    namespace: <tenant-namespace>
EOF

# 3. Verify controller can see new namespace
kubectl auth can-i list agents --as=system:serviceaccount:kagent:kagent-controller -n <tenant-namespace>
```

---

## Minimal Tenant Agent Example

Once onboarded, tenants create `Agent` objects in their own namespace:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: my-app-agent
  namespace: <tenant-namespace>
  labels:
    platform.com/team: <team-name>
    platform.com/type: application
spec:
  description: "Agent for <app-name>"
  systemPrompt: |
    You are an assistant for <app-name>.
  modelConfig:
    apiKeySecretRef: kagent-model-secret   # can reference secret in kagent namespace
  tools:
    - name: kagent-tool-server
      type: McpServer
      config:
        url: http://kagent-tool-server.kagent.svc.cluster.local:8080/mcp
```

---

## Checklist

| Step | Command | Expected |
|------|---------|----------|
| Controller has ClusterRole | `kubectl get clusterrolebinding -l app=kagent-controller` | Bound to kagent-controller SA |
| Tenant RBAC applied | `kubectl get role kagent-tenant -n <ns>` | Role exists |
| Namespace labelled | `kubectl get ns <ns> --show-labels` | `kagent-access=true` |
| NetworkPolicy allows | `kubectl get networkpolicy -n kagent` | allow-tenant-ingress present |
| Controller can watch | `kubectl auth can-i list agents --as=system:serviceaccount:kagent:kagent-controller -n <ns>` | `yes` |
| Tenant can create | `kubectl auth can-i create agents --as=system:serviceaccount:<ns>:<sa> -n <ns>` | `yes` |
