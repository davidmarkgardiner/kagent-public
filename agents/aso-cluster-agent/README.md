# ASO Cluster Agent Demo

A stakeholder demo: talk to a KAgent AI agent in chat, ask for an AKS cluster, watch it provision via Azure Service Operator and KRO, and receive a certification verdict.

## Cost policy reminder

> **NEVER create Azure resources without explicit authorization.**
> This demo defaults to `dryRun=true` — no Azure spend.
> To run a real provision, update the `DRY_RUN_DEFAULT` annotation on the agent
> and populate `platform-defaults-secret.yaml` with real Azure values.
> Always clean up demo clusters after use.

---

## How the demo works

```
User (kagent UI) ──► aso-cluster-provisioner (KAgent agent)
                          │ submits Workflow CR
                          ▼
                 provision-aks-cluster (Argo WorkflowTemplate)
                          │ 1. validate inputs
                          │ 2. render UK8SClusterPublic YAML from Secret defaults
                          │ 3. apply (or --dry-run=server)
                          │ 4. wait for ACTIVE+Ready
                          │ 5. apply UK8SCertificationV2 instance
                          ▼
                 certificationTrigger Job (auto-fires cert workflow)
                          ▼
                 sre-triage-agent (KAgent) ──► verdict
```

The agent only extracts `{clusterName, region, size}` — all YAML is rendered inside the workflow using values from a Kubernetes Secret.

---

## Prerequisites

- `{{CLUSTER_NAME}}` cluster with KAgent + Argo Workflows installed
- KRO controller running with the UK8SClusterPublic + UK8SCertificationV2 RGDs applied:
  ```bash
  kubectl apply -f infra-stack/kro-stack/definitions/uk8scluster-public.yaml
  kubectl apply -f infra-stack/kro-stack/definitions/uk8s-certification-v2.yaml
  ```
  (No ASO controller needed for dry-run — KRO validates but never persists)
- `argo-workflow-executor` ServiceAccount exists in `argo` namespace

---

## Deploy (home / dry-run)

```bash
cd aks-mgmt-stack/aso-cluster-agent-demo

# Install everything (idempotent)
bash scripts/deploy-home-dryrun.sh

# Run RBAC preflight (must pass before anything else)
bash scripts/smoke-test-rbac.sh

# Run dry-run workflow test (proves no Azure resources are created)
bash scripts/smoke-test-dryrun.sh

# Run bad-input rejection tests
bash scripts/smoke-test-bad-inputs.sh
```

All four must exit 0 before the demo.

---

## Flip to real provisioning (work cluster)

1. **Populate real Azure values** in `workflow/platform-defaults-secret.yaml`:
   ```bash
   cp workflow/platform-defaults-secret.yaml.template workflow/platform-defaults-secret.yaml
   # Edit: SUBSCRIPTION_ID, VNET_*, identity IDs, SSH_PUBLIC_KEY, FLUX_*_URL
   kubectl apply -f workflow/platform-defaults-secret.yaml -n argo
   ```

2. **Disable dry-run** on the agent:
   ```bash
   kubectl annotate agent aso-cluster-provisioner -n kagent \
     DRY_RUN_DEFAULT=false --overwrite
   kubectl patch agent aso-cluster-provisioner -n kagent --type=json \
     -p '[{"op":"replace","path":"/spec/declarative/systemMessage","value":"..."}]'
   ```
   Or edit `agent/aso-provisioner-agent.yaml`, change `DRY_RUN` default to `"false"`, re-apply.

3. **Run cert-trigger rehearsal** (30 min before demo, against an already-Ready cluster):
   ```bash
   bash scripts/smoke-test-cert-trigger.sh --cluster <existing-cluster-name>
   ```

4. **Pre-stage a fallback cluster** (`demonstration-one-prebuilt`) 30 min before stakeholders arrive.

---

## Using the agent

Open `https://{{INGRESS_DOMAIN}}` → select **aso-cluster-provisioner**.

Example conversation:
```
User:  Hi, I'd like a cluster please.
Agent: Sure! I need: cluster name, region (uksouth/westeurope/northeurope/ukwest), and size (small/medium/large).

User:  Call it demonstration-one, West Europe, small.
Agent: Cluster request ready to submit:
         name   : demonstration-one
         region : westeurope
         size   : small (Standard_B8ms × 1 node)
         dry-run: true
       Type "yes, provision" to proceed.

User:  yes, provision
Agent: Workflow submitted: provision-aks-demonstration-one-xk7p2.
       Ask me "status of provision-aks-demonstration-one-xk7p2" to check progress.

User:  status of provision-aks-demonstration-one-xk7p2
Agent: The cluster demonstration-one is currently simulating provisioning
       (phase: bootstrapping-node-pool-(simulated), elapsed: 15s).
       Argo workflow phase: Running.
```

---

## Checking workflow status directly

```bash
# Argo UI
kubectl port-forward svc/argo-server -n argo 2746:2746
# open http://localhost:2746

# Status ConfigMap (what the agent reads)
kubectl get configmap provision-status-<workflow-name> -n argo -o yaml

# Watch workflow progress
argo watch <workflow-name> -n argo
```

---

## Teardown

```bash
# Remove demo artifacts (leave RBAC)
bash scripts/teardown-home.sh

# Remove everything including RBAC
bash scripts/teardown-home.sh --purge-rbac

# After a real provision — delete the cluster and cert instance
kubectl delete uk8sclusterpublic <cluster-name> -n uk8s-nextgen
kubectl delete uk8scertificationv2 cert-<cluster-name> -n uk8s-nextgen
```

---

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Agent not Ready in kagent UI | `kubectl logs -n kagent deploy/kagent-controller \| tail -30` |
| Workflow fails at `validate-inputs` | Check name regex, region/size enum in workflow logs |
| Workflow fails at `render-and-apply` | Check `platform-defaults` Secret exists: `kubectl get secret platform-defaults -n argo` |
| `--dry-run=server` admission error | KRO CRD not installed or UK8SClusterPublic RGD not applied |
| Agent hallucinates a field | Check system prompt `NEVER` rules; model may need temperature lowered |
| Status ConfigMap missing | Workflow failed before `init-status-cm` step — check `validate-inputs` logs |

---

## File layout

```
aso-cluster-agent-demo/
├── README.md                                 (this file)
├── DEMO-SCRIPT.md                            (turn-by-turn stakeholder walk-through)
├── DESIGN-DECISIONS.md                       (why A-lite; Codex review notes)
├── agent/
│   └── aso-provisioner-agent.yaml            KAgent Agent CRD
├── workflow/
│   ├── provision-aks-cluster-template.yaml   Argo WorkflowTemplate
│   ├── platform-defaults-secret.yaml.template  committed template, real file gitignored
│   └── rbac.yaml                             tightly scoped RBAC
└── scripts/
    ├── deploy-home-dryrun.sh
    ├── smoke-test-rbac.sh
    ├── smoke-test-dryrun.sh
    ├── smoke-test-bad-inputs.sh
    └── teardown-home.sh
```
