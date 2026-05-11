---
name: idp-port-io
description: Port.io IDP for Kubernetes namespace self-service and application deployment via Argo Events + Argo Workflows. Covers setup, API patterns, troubleshooting.
tags: [kubernetes, idp, port-io, argo-events, argo-workflows, gitops]
---

# IDP Port.io — Namespace & App Deployment

## Architecture

```
Port.io UI → webhook POST → Argo Events EventSource (port 12000)
  → Sensor (routes by endpoint) → Argo Workflow (DAG)
    → validate → generate-manifests → git-commit → report-to-port
                                         ↓
                                    Git repo (feature branch)
                                         ↓
                                    Flux sync → K8s cluster
                                         ↓
                                    Port K8s Exporter → Port.io entities
```

**Two flows:**
1. **Namespace self-service**: Port.io → `/namespace-action` → create/delete/modify namespace manifests in Git → Flux applies
2. **App deployment**: Port.io → `/app-deploy` → kubectl apply Deployment+Service+Ingress+HPA directly

## Prerequisites

- Kubernetes cluster (Kind `dev` or AKS)
- Argo Events (namespace: `argo-events`)
- Argo Workflows (namespace: `argo`)
- MinIO (for artifact storage — in `argo-events` namespace)
- Traefik or ingress controller (for webhook exposure)
- Port.io account (free tier works)
- Git repo for GitOps manifests
- Cloudflare tunnel or ingress for webhook exposure

## Setup Steps

### 1. Deploy MinIO for artifact storage

Argo Workflows needs artifact storage. Without MinIO/S3, workflows fail silently on artifact upload.

```bash
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: argo-events
spec:
  selector:
    matchLabels: {app: minio}
  template:
    metadata:
      labels: {app: minio}
    spec:
      containers:
        - name: minio
          image: minio/minio:latest
          command: [minio, server, /data]
          env:
            - {name: MINIO_ACCESS_KEY, value: minio}
            - {name: MINIO_SECRET_KEY, value: minio123}
          ports: [{containerPort: 9000}]
---
apiVersion: v1
kind: Service
metadata: {name: minio, namespace: argo-events}
spec:
  selector: {app: minio}
  ports: [{port: 9000, targetPort: 9000}]
EOF
```

### 2. Configure Argo Workflows to use MinIO

Patch the `argo-workflows` ConfigMap or Helm values to use MinIO as artifact repository.

### 3. Deploy all IDP resources

Source files: `/home/david/repos/argo-workflow/idp-namespace-service/`

```bash
kubectl apply -f 00-eventsource-port-webhook.yaml
kubectl apply -f 05-rbac.yaml
kubectl apply -f 08-rbac-app-deploy.yaml
kubectl apply -f 02-workflow-create-namespace.yaml
kubectl apply -f 03-workflow-delete-namespace.yaml
kubectl apply -f 04-workflow-modify-namespace.yaml
kubectl apply -f 06-workflow-deploy-app.yaml
kubectl apply -f 01-sensor-namespace-actions.yaml
kubectl apply -f 07-sensor-app-deploy.yaml
```

### 4. Create the EventSource Service manually

**CRITICAL**: Argo Events webhook eventsources do NOT auto-create a Service. The EventSource spec has `service.ports` but that only configures the pod, not a k8s Service. Create it:

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: port-webhook-eventsource-svc
  namespace: argo-events
spec:
  selector:
    eventsource-name: port-webhook
  ports:
    - port: 12000
      targetPort: 12000
EOF
```

### 5. Create Port.io blueprints and actions via API

Use `scripts/setup-port-blueprints.sh` or manually via API. See `references/port-api.md`.

### 6. Expose webhook

Option A — Cloudflare tunnel:
```bash
cloudflared tunnel --url http://port-webhook-eventsource-svc.argo-events.svc:12000
```

Option B — Traefik IngressRoute pointing to the eventsource service.

### 7. Create secrets

```bash
# Git SSH key
kubectl create secret generic git-ssh-key -n argo-events \
  --from-file=ssh-privatekey=~/.ssh/id_ed25519

# Git credentials
kubectl create secret generic git-credentials -n argo-events \
  --from-literal=repo-url=git@ssh.dev.azure.com:v3/org/project/repo

# Port.io credentials
kubectl create secret generic port-credentials -n argo-events \
  --from-literal=client-id=YOUR_ID \
  --from-literal=client-secret=YOUR_SECRET
```

**Store all secrets in Google Cloud Secret Manager too.**

## Port.io API Patterns

See `references/port-api.md` for full reference.

Quick auth:
```bash
TOKEN=$(curl -s -X POST "https://api.getport.io/v1/auth/access_token" \
  -H "Content-Type: application/json" \
  -d '{"clientId":"'$CLIENT_ID'","clientSecret":"'$CLIENT_SECRET'"}' | jq -r '.accessToken')
```

Create blueprint: `POST /v1/blueprints` with JSON body.
Create entity: `POST /v1/blueprints/{blueprint}/entities?upsert=true`.
Create action: `POST /v1/actions` (**NOT** `/v1/blueprints/{id}/actions`).
Create scorecard: `POST /v1/blueprints/{blueprint}/scorecards`.

## Lessons Learned (Critical)

1. **EventSource Service**: Argo Events webhook eventsources don't auto-create k8s Services. Must create manually with selector `eventsource-name: <name>`.

2. **WorkflowTemplate namespace**: Must be in same namespace as sensor-triggered workflows. If sensor creates workflows in `argo-events`, templates must be in `argo-events`.

3. **ServiceAccount namespace**: `idp-workflow-sa` must exist in the namespace where workflows run (e.g., `argo-events`), not just where RBAC yaml declares it. The RBAC file had it in `argo` but workflows ran in `argo-events`.

4. **workflowtaskresults RBAC**: Workflow SA needs permission to create `workflowtaskresults` in the `argoproj.io` API group, or workflows hang.

5. **Container images**:
   - `alpine/git` has no bash or jq — use `sh` and `apk add`
   - `bitnami/git:2.43.0` may not exist — use `alpine:latest` with `apk add git jq openssh`
   - `alpine/k8s:1.32.2` has kubectl + jq — good for deploy workflows

6. **Argo artifacts**: Need MinIO or S3 configured. Workflows fail silently on artifact upload without it.

7. **Port.io actions API**: Endpoint is `/v1/actions`, NOT `/v1/blueprints/{id}/actions`.

8. **Alertmanager**: `repeat_interval: 12h` means alerts won't re-fire for 12 hours — set lower for testing.

9. **Secrets in workflow namespace**: `git-credentials`, `port-credentials`, `git-ssh-key` must all be in the namespace where workflows execute.

10. **Sensor dependencies**: Can't reference same event from multiple dependencies. Use single dependency with filters or separate endpoints per action type.

11. **conditionsReset**: Sensors need `conditionsReset` with a cron or the trigger fires only once. Use `cron: "* * * * *"` for continuous triggering.

## Testing

### Test namespace creation webhook
```bash
kubectl run -n argo-events test-create --rm -it --restart=Never --image=curlimages/curl -- \
  curl -s -X POST http://port-webhook-eventsource-svc.argo-events.svc.cluster.local:12000/namespace-action \
  -H "Content-Type: application/json" \
  -d '{"action":"create","namespace":"platform-dev-testing","cluster":"homelab","owner":"david@bank.com","team":"platform","environment":"dev","cpu_quota":"4","memory_quota":"8Gi"}'
```

### Test app deployment webhook
```bash
kubectl run -n argo-events test-deploy --rm -it --restart=Never --image=curlimages/curl -- \
  curl -s -X POST http://port-webhook-eventsource-svc.argo-events.svc.cluster.local:12000/app-deploy \
  -H "Content-Type: application/json" \
  -d '{"app_name":"podinfo","namespace":"platform-dev-testing","image":"stefanprodan/podinfo:latest","replicas":"2","port":"9898","cpu_request":"100m","memory_request":"128Mi","enable_ingress":"true","enable_hpa":"false"}'
```

### Watch workflows
```bash
kubectl get workflows -n argo-events -w
kubectl get workflow <name> -n argo-events -o json | jq '.status.nodes | to_entries[] | {name: .value.displayName, phase: .value.phase}'
stern -n argo-events "ns-create\|app-deploy" --since 5m
```

## File Reference

All in `/home/david/repos/argo-workflow/idp-namespace-service/`:

| File | Purpose |
|------|---------|
| `00-eventsource-port-webhook.yaml` | Webhook receiver on port 12000 with `/namespace-action` and `/app-deploy` endpoints |
| `01-sensor-namespace-actions.yaml` | Routes namespace webhook to create-namespace WorkflowTemplate |
| `02-workflow-create-namespace.yaml` | DAG: validate → generate-manifests → git-commit → report-to-port |
| `03-workflow-delete-namespace.yaml` | DAG: validate → git-remove → report-to-port |
| `04-workflow-modify-namespace.yaml` | DAG: validate → git-modify-quotas → report-to-port |
| `05-rbac.yaml` | ServiceAccounts, ClusterRoles, ClusterRoleBindings, secret templates |
| `06-workflow-deploy-app.yaml` | DAG: validate → kubectl apply (Deployment+Service+Ingress+HPA) → wait-rollout → report |
| `07-sensor-app-deploy.yaml` | Routes app-deploy webhook to deploy-application WorkflowTemplate |
| `08-rbac-app-deploy.yaml` | ClusterRole for app deploy (deployments, services, ingresses, HPAs) |
| `port/blueprint-cluster.json` | Cluster blueprint definition |
| `port/blueprint-namespace.json` | Namespace blueprint with properties, relations, status enums |
| `port/action-create-namespace.json` | Self-service CREATE action with user inputs |
| `port/action-delete-namespace.json` | Self-service DELETE action (requires approval) |
| `port/action-modify-namespace.json` | DAY-2 action for quota modification |
| `port/scorecard-namespace.json` | Compliance scorecard (quota, netpol, RBAC, owner checks) |

## Generated Namespace Manifests

The create-namespace workflow generates these files per namespace:

```
clusters/{cluster}/namespaces/{name}/
├── namespace.yaml        # With IDP labels (team, env, owner)
├── resourcequota.yaml    # CPU/memory/pod limits
├── limitrange.yaml       # Default container resource limits
├── networkpolicy.yaml    # Default-deny + same-ns + DNS egress
├── rbac.yaml             # Team→edit, SRE→view RoleBindings
└── kustomization.yaml    # Kustomize wrapper with common labels
```

## Port.io Credentials

Stored in Google Cloud Secret Manager:
- `port-io-client-id`
- `port-io-client-secret`
