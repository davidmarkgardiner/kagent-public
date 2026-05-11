# Troubleshooting — IDP Port.io + Argo

## EventSource Issues

### Webhook not reachable
**Symptom**: curl to eventsource returns connection refused.
**Cause**: EventSource pod is running but no k8s Service exists.
**Fix**: Create Service manually:
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
**Why**: Argo Events `spec.service.ports` configures the pod's container port, NOT a k8s Service.

### EventSource pod not starting
```bash
kubectl get eventsource -n argo-events
kubectl describe eventsource port-webhook -n argo-events
kubectl logs -l eventsource-name=port-webhook -n argo-events
```

## Sensor Issues

### Sensor fires only once
**Symptom**: First webhook triggers workflow, subsequent ones don't.
**Cause**: Missing `conditionsReset`.
**Fix**: Add to trigger template:
```yaml
conditionsReset:
  - byTime:
      cron: "* * * * *"
```

### Sensor can't create workflows
**Symptom**: Sensor logs show RBAC errors.
**Fix**: Ensure sensor ServiceAccount has workflow create permission:
```yaml
rules:
  - apiGroups: ["argoproj.io"]
    resources: ["workflows"]
    verbs: ["create", "get", "list"]
  - apiGroups: ["argoproj.io"]
    resources: ["workflowtemplates"]
    verbs: ["get", "list"]
```

### Sensor references same event multiple times
**Symptom**: Only first trigger works, or unexpected behavior.
**Cause**: Can't have multiple dependencies pointing to same event.
**Fix**: Use single dependency with routing in trigger conditions, or use separate endpoints per action.

## Workflow Issues

### WorkflowTemplate not found
**Symptom**: `WorkflowTemplate not found` error.
**Cause**: Template is in different namespace than where workflow is created.
**Fix**: WorkflowTemplates must be in same namespace as workflows. If sensor creates workflows in `argo-events`, templates must also be in `argo-events`.

### ServiceAccount not found
**Symptom**: Workflow fails with `serviceaccount "idp-workflow-sa" not found`.
**Cause**: SA exists in `argo` but workflow runs in `argo-events`.
**Fix**: Create SA in the workflow's namespace:
```bash
kubectl create serviceaccount idp-workflow-sa -n argo-events
```
Then update ClusterRoleBinding subjects to reference correct namespace.

### workflowtaskresults permission denied
**Symptom**: Workflow hangs or fails with RBAC error about `workflowtaskresults`.
**Fix**: Add to workflow SA's ClusterRole:
```yaml
- apiGroups: ["argoproj.io"]
  resources: ["workflowtaskresults"]
  verbs: ["create", "patch"]
```

### Artifact upload fails silently
**Symptom**: Workflow step succeeds but next step can't find artifact. Or workflow logs show artifact errors.
**Cause**: No artifact repository configured (MinIO/S3).
**Fix**: Deploy MinIO and configure Argo Workflows artifact repository.

### Secrets not found in workflow
**Symptom**: `secret "git-credentials" not found` or similar.
**Cause**: Secrets exist in wrong namespace.
**Fix**: All secrets (`git-ssh-key`, `git-credentials`, `port-credentials`) must be in the namespace where workflows run:
```bash
kubectl get secrets -n argo-events | grep -E 'git|port'
```

## Container Image Issues

### `bash: not found` in alpine containers
**Cause**: Alpine doesn't have bash. `alpine/git` also lacks bash and jq.
**Fix**: Use `sh` instead of `bash`, or:
```yaml
command: [sh, -c, "apk add --no-cache bash jq && bash /script.sh"]
```

### `bitnami/git:2.43.0` image pull failure
**Cause**: Specific tag may not exist or be pulled.
**Fix**: Use `alpine:latest` with packages:
```yaml
image: alpine:latest
command: [sh, -c, "apk add --no-cache git jq openssh && sh /script.sh"]
```

### Recommended images
| Use case | Image |
|----------|-------|
| Python scripting | `python:3.12-alpine` |
| Git operations | `alpine:latest` + `apk add git openssh` |
| kubectl operations | `alpine/k8s:1.32.2` |
| curl/wget | `curlimages/curl:8.5.0` |

## Port.io API Issues

### Wrong actions endpoint
**Wrong**: `POST /v1/blueprints/{id}/actions`
**Right**: `POST /v1/actions`

### Token expired
Port tokens last 24 hours. If workflow takes long, token may expire mid-run. Get token fresh in each step.

### Entity upsert not updating
Ensure `upsert=true` and `merge=true` query params:
```
POST /v1/blueprints/namespace/entities?upsert=true&merge=true
```

## Monitoring

### Check all components
```bash
# EventSource
kubectl get eventsource -n argo-events
kubectl logs -l eventsource-name=port-webhook -n argo-events --tail=20

# Sensors
kubectl get sensor -n argo-events
kubectl logs -l sensor-name=namespace-actions -n argo-events --tail=20
kubectl logs -l sensor-name=app-deploy -n argo-events --tail=20

# Workflows
kubectl get workflows -n argo-events --sort-by=.metadata.creationTimestamp
kubectl get workflow <name> -n argo-events -o json | jq '.status.nodes | to_entries[] | {name: .value.displayName, phase: .value.phase}'

# Argo Workflows UI
kubectl port-forward -n argo svc/argo-workflows-server 2746:2746
# Open https://localhost:2746
```

### Alertmanager repeat_interval
If using kube-prometheus-stack, note that `repeat_interval: 12h` means an alert won't re-fire for 12 hours. Set lower for testing:
```yaml
repeat_interval: 5m
```
