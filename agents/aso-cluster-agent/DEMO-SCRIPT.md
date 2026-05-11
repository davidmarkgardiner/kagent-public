# Demo Script — ASO Cluster Agent

Turn-by-turn guide for the stakeholder session. Read this before walking into the room.

---

## Before you start (T-30 min)

1. Run all four smoke tests — they must all exit 0:
   ```bash
   bash scripts/smoke-test-rbac.sh
   bash scripts/smoke-test-dryrun.sh
   bash scripts/smoke-test-bad-inputs.sh
   ```

2. Open these tabs in advance:
   - **Tab 1**: `https://{{INGRESS_DOMAIN}}` — KAgent UI, agent selected
   - **Tab 2**: Argo UI (`kubectl port-forward svc/argo-server -n argo 2746:2746` → `http://localhost:2746`)
   - **Tab 3** (work cluster only): Azure portal → Resource Groups, filtered to your subscription

3. **Work cluster only**: pre-stage a fallback cluster:
   ```bash
   # Apply a real cluster 30 min before demo so it's Ready when you walk in
   kubectl apply -f - <<YAML
   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: provision-aks-demonstration-one-prebuilt-
     namespace: argo
   spec:
     workflowTemplateRef:
       name: provision-aks-cluster
     arguments:
       parameters:
         - name: clusterName
           value: "demonstration-one-prebuilt"
         - name: region
           value: "westeurope"
         - name: size
           value: "small"
         - name: dryRun
           value: "false"
         - name: confirmedBy
           value: "demo-prep"
   YAML
   ```

---

## The conversation (type this exactly)

### Opening

**You say to audience:**
> "I'm going to show you how a platform engineer or a developer can request an AKS cluster
> just by having a conversation. The agent understands the request, confirms the details,
> and then the platform takes over — creating the cluster via Azure Service Operator and
> running an automated certification before handing it back."

---

### Turn 1 — start the conversation

**Type into kagent UI:**
```
Hi, I'd like a new AKS cluster please.
```

**Expected agent reply (paraphrased):**
```
Hi! I can help with that. I'll need three things:
- A cluster name (lowercase, hyphens only, e.g. "demonstration-one")
- A region: uksouth, westeurope, northeurope, or ukwest
- A size: small, medium, or large
```

**If the agent says something else:** It's still valid — the model may phrase the greeting differently. As long as it asks for the three parameters, continue.

---

### Turn 2 — provide the details

**Type:**
```
Call it demonstration-one, West Europe, small please.
```

**Expected agent reply:**
```
Cluster request ready to submit:
  name   : demonstration-one
  region : westeurope
  size   : small (Standard_B8ms × 1 node)
  dry-run: true

Type "yes, provision" to proceed, or change any detail.
```

**If the agent gets the name wrong (e.g. "demonstration-1"):** Say:
> "The model slightly changed my cluster name — watch, I'll correct it."
> Type: `No, the name should be exactly demonstration-one`
> The agent should correct and re-show the confirmation block.

---

### Turn 3 — confirm

**Type exactly:**
```
yes, provision
```

**Expected agent reply:**
```
Workflow submitted: provision-aks-demonstration-one-<suffix>.
Ask me "status of provision-aks-demonstration-one-<suffix>" to check progress.
```

**While waiting:** Switch to Tab 2 (Argo UI) and show the running workflow.
> "You can see the workflow has kicked off — it's validating the inputs, rendering the
> cluster configuration from our platform defaults, and applying it to Kubernetes.
> The platform template handles all the complexity — the user just chose a name and a size."

---

### Turn 4 — ask for status (30–60 seconds later)

**Type:**
```
status of provision-aks-demonstration-one-<suffix>
```

**Expected agent reply (dry-run):**
```
The cluster demonstration-one is currently in phase "bootstrapping-node-pool-(simulated)"
(elapsed: ~15s). The Argo workflow is Running.
(Note: this is a dry-run — no Azure resources are being created.)
```

**Expected agent reply (real provision):**
```
The cluster demonstration-one is provisioning (phase: provisioning, KRO state: PENDING,
elapsed: 120s). The Argo workflow is Running. Check back in a few minutes.
```

**Point to Tab 3 (work only):** Azure portal should show a new resource group appearing.

---

### Turn 5 — final status (work cluster, ~12–15 min in)

**Type:**
```
status of provision-aks-demonstration-one-<suffix>
```

**Expected:**
```
The cluster demonstration-one is ready (phase: ready). The Argo workflow Succeeded.
A UK8SCertificationV2 instance has been applied — the certification workflow is auto-firing
to verify the cluster's health and will deliver a verdict shortly.
```

**Fallback if live cluster isn't ready yet:** Switch to `demonstration-one-prebuilt`:
> "Our pre-staged cluster is already Ready — let me show you what the final state looks like."
> Type: `status of provision-aks-demonstration-one-prebuilt-<suffix>`

---

## Audience questions

**"What's dry-run mode?"**
> "In dry-run, the Kubernetes API validates the full cluster configuration against our
> platform schema, but no Azure resources are actually created. It's how we rehearse
> the demo without incurring cost."

**"What's KRO?"**
> "KRO is a resource orchestration layer — think of it as a platform abstraction.
> The agent submits a single UK8SClusterPublic resource; KRO expands that into the
> twenty-odd Azure resources needed for a production cluster — VNets, identities,
> the AKS managed cluster, Flux GitOps, Defender — all with our security defaults baked in."

**"What's certification?"**
> "After provisioning, the UK8SCertificationV2 workflow runs a battery of checks —
> KRO resources active, ASO resources ready, Flux synced, AKS system components healthy,
> security addons enabled — and then hands the results to an SRE triage agent that
> produces a severity verdict. CRITICAL means the cluster needs immediate attention;
> INFO means all green."

**"Could a developer do this from Slack or Teams?"**
> "Yes — KAgent supports Teams integration. The same agent could be exposed as a Teams bot;
> the workflow underneath is identical. We kept the demo in the UI for visibility."

**"What if the agent picks the wrong parameters?"**
> "The workflow validates every parameter before touching anything. Wrong region? Fails
> immediately with a clear message. Wrong name format? Same. The structural guardrails
> are in the platform, not just in the prompt."

---

## Recovery lines

| What went wrong | What to say | What to type |
| --- | --- | --- |
| Agent doesn't respond | "Let me refresh the agent connection." | Reload the browser tab |
| Model invented a cluster name | "Notice the agent rejected a name that doesn't match our naming standard — that's the guard." | Explicitly type the correct name |
| Workflow stuck in Pending | "The workflow controller is picking it up — let me show you directly in Argo." | Switch to Argo UI tab |
| Workflow failed | "Let me use the prebuilt cluster to show the certified state." | Status of prebuilt cluster |
| Cert workflow not fired | "The cert job triggers automatically once the cluster is Ready — on the prebuilt cluster it already ran." | Show cert workflow in Argo UI |

---

## After the demo

```bash
# Dry-run: nothing to clean up (no Azure resources)
bash scripts/teardown-home.sh

# Real provision: delete cluster and cert instance
kubectl delete uk8sclusterpublic demonstration-one -n uk8s-nextgen
kubectl delete uk8sclusterpublic demonstration-one-prebuilt -n uk8s-nextgen
kubectl delete uk8scertificationv2 cert-demonstration-one -n uk8s-nextgen
kubectl delete uk8scertificationv2 cert-demonstration-one-prebuilt -n uk8s-nextgen
```
