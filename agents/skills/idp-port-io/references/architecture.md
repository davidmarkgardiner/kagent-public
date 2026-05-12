# IDP Architecture — Detailed

## System Overview

```
┌─────────────────────┐     webhook POST     ┌──────────────────────────┐
│   Port.io Portal    │ ──────────────────► │  Argo Events EventSource │
│   (SaaS)            │                      │  port-webhook            │
│                     │                      │  port: 12000             │
│  Blueprints:        │                      │                          │
│  - cluster          │                      │  Endpoints:              │
│  - namespace        │                      │  /namespace-action       │
│  - application      │                      │  /app-deploy             │
│                     │                      └────────┬─────────────────┘
│  Actions:           │                               │
│  - create_namespace │                               │ event
│  - delete_namespace │                               │
│  - modify_namespace │                      ┌────────▼─────────────────┐
│  - deploy_app       │                      │  Sensors                 │
│                     │                      │  - namespace-actions     │
│  Scorecards:        │                      │  - app-deploy            │
│  - compliance       │                      │                          │
└─────────┬───────────┘                      │  Routes by endpoint to   │
          │                                  │  WorkflowTemplate        │
          │ status updates                   └────────┬─────────────────┘
          │ (entity upsert)                           │
          │                                           │ creates Workflow
┌─────────┴───────────┐                      ┌────────▼─────────────────┐
│  Port K8s Exporter  │                      │  Argo Workflow (DAG)     │
│  (optional, reads   │                      │                          │
│   cluster state     │                      │  Namespace flow:         │
│   back to Port)     │                      │  validate → generate →   │
└─────────────────────┘                      │  git-commit → report     │
                                             │                          │
                                             │  App deploy flow:        │
                                             │  validate → kubectl →    │
                                             │  wait-rollout → report   │
                                             └────────┬─────────────────┘
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    │                 │                 │
                              ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
                              │  Git Repo │    │  kubectl   │    │  Port API │
                              │  (GitOps) │    │  apply     │    │  (report) │
                              └─────┬─────┘    └───────────┘    └───────────┘
                                    │
                              ┌─────▼─────┐
                              │  Flux     │
                              │  sync     │
                              └─────┬─────┘
                                    │
                              ┌─────▼─────┐
                              │  K8s      │
                              │  cluster  │
                              └───────────┘
```

## Component Details

### EventSource (`00-eventsource-port-webhook.yaml`)
- Runs as a pod in `argo-events` namespace
- Listens on port 12000
- Two webhook endpoints: `/namespace-action`, `/app-deploy`
- **Does NOT create a k8s Service** — must create manually

### Sensors
- **namespace-actions** (`01-sensor`): Listens to `port-namespace-action` event, creates workflow from `create-namespace` template
- **app-deploy** (`07-sensor`): Listens to `port-app-deploy` event, creates workflow from `deploy-application` template
- Both use `conditionsReset` with cron to allow repeated triggers
- Both pass webhook body as `payload` parameter to workflow

### WorkflowTemplates (all in `argo-events` namespace)
| Template | Steps | Artifacts |
|----------|-------|-----------|
| `create-namespace` | validate → generate-manifests → git-commit → report | manifests (MinIO) |
| `delete-namespace` | validate → git-remove → report | none |
| `modify-namespace` | validate → git-modify → report | none |
| `deploy-application` | validate → kubectl-apply → wait-rollout → report | none |

### RBAC
- **idp-workflow-sa**: ServiceAccount for workflows. Needs pods/log read, secrets read, namespace list, workflow create, `workflowtaskresults` create
- **idp-sensor-sa**: ServiceAccount for sensors. Needs workflow create, workflowtemplate read
- **idp-app-deploy-role**: ClusterRole for app deployments, services, ingresses, HPAs

### Secrets (all in workflow namespace)
| Secret | Keys | Purpose |
|--------|------|---------|
| `git-ssh-key` | `ssh-privatekey` | SSH key for git clone/push |
| `git-credentials` | `repo-url` | GitOps repository URL |
| `port-credentials` | `client-id`, `client-secret` | Port.io API auth |

## Data Flow — Namespace Creation

1. User fills form in Port.io UI (namespace name, cluster, team, env, quotas)
2. Port.io POSTs JSON to webhook URL `/namespace-action`
3. EventSource receives POST, emits `port-namespace-action` event
4. Sensor matches event, creates Workflow from `create-namespace` template with payload
5. Workflow DAG runs:
   - **validate**: Python checks naming convention, required fields, quota formats
   - **generate-manifests**: Python creates 6 YAML files (ns, quota, limitrange, netpol, rbac, kustomization) → stores as artifact in MinIO
   - **git-commit**: Clones GitOps repo, copies manifests, commits to feature branch, pushes
   - **report-success**: POSTs to Port.io API to upsert namespace entity with status=Active
6. **onExit handler**: If workflow fails, reports status=Failed to Port.io
7. Flux detects new branch/commit, syncs manifests to cluster
8. (Optional) Port K8s Exporter reads cluster state back to Port.io

## Data Flow — App Deployment

1. User fills form (app name, namespace, image, replicas, port, ingress, HPA)
2. Port.io POSTs to `/app-deploy`
3. Sensor creates Workflow from `deploy-application` template
4. Workflow runs:
   - **validate**: Checks namespace exists via kubectl
   - **apply-manifests**: kubectl apply Deployment, Service, optionally Ingress and HPA
   - **wait-rollout**: `kubectl rollout status` with 120s timeout
   - **report-success**: Upserts `application` entity in Port.io, updates action run status
5. On failure: report-failure step runs instead
