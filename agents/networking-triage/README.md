# Container Network Insights Agent — Phase 1 (Interactive Tool)

Install Microsoft's AI-powered networking diagnostic agent on an AKS cluster
and use it as an interactive chatbot for deep-dive troubleshooting.

**Phase 1 scope:** deploy the Microsoft extension as-is, team uses the browser
chat for networking problems. No programmatic integration.

**Phase 2 (later):** bake diagnostic patterns into a dedicated kagent
`networking-triage-agent` for automated flows. See `ROADMAP.md`.

## What It Is

- Microsoft-managed AI chatbot packaged as an AKS cluster extension
- Runs as a pod in `kube-system` on your AKS cluster
- Uses AKS MCP server + Azure OpenAI under the hood
- Provides browser chat UX for DNS / packet drop / K8s networking diagnosis
- **Read-only** — produces recommendations, never modifies the cluster
- Free during public preview (you pay for Azure OpenAI token consumption)

Official docs: https://learn.microsoft.com/en-us/azure/aks/container-network-insights-agent-overview

## Prerequisites

| Requirement | Notes |
|---|---|
| AKS cluster | Not Arc-enabled, not hybrid, not AKS on Azure Stack HCI |
| Azure region | `centralus`, `eastus`, `eastus2`, `uksouth`, or `westus2` |
| Azure CLI | ≥ 2.60 recommended; need `k8s-extension` subcommand |
| `Microsoft.KubernetesConfiguration` provider registered on subscription | For cluster extensions |
| (Optional but recommended) Azure CNI powered by Cilium | For Cilium policy + Hubble diagnostics |
| (Optional but recommended) Advanced Container Networking Services (ACNS) | For Hubble flow analysis |

Check your region and CNI:

```bash
az aks show --name <aks-name> --resource-group <rg> \
  --query "{location:location, cni:networkProfile.networkPlugin, cniMode:networkProfile.networkPluginMode}" -o table
```

Expected for full capability:
```
Location    Cni    CniMode
----------  -----  --------
uksouth     azure  overlay    (with Cilium)
```

## Install (15 minutes)

### 1. Register the preview extension provider

One-off per subscription:

```bash
az provider register --namespace Microsoft.KubernetesConfiguration
# Wait for registration to complete
az provider show --namespace Microsoft.KubernetesConfiguration \
  --query registrationState -o tsv
# Expected: Registered
```

### 2. Install the extension

```bash
az k8s-extension create \
  --cluster-type managedClusters \
  --cluster-name <aks-name> \
  --resource-group <rg> \
  --name container-networking-agent \
  --extension-type microsoft.containernetworkingagent \
  --scope cluster \
  --release-train preview
```

This creates:
- A Deployment `container-networking-agent` in `kube-system`
- A Service exposing the chat UI
- A ServiceAccount `container-networking-agent-reader` with read-only RBAC
- On first packet-drop query: a DaemonSet `rx-troubleshooting-debug` (auto-cleaned)

### 3. Verify the install

```bash
kubectl get deploy -n kube-system container-networking-agent
kubectl get pods  -n kube-system -l app=container-networking-agent
kubectl get svc   -n kube-system container-networking-agent
```

All should be Ready / Running.

### 4. Access the chat UI

```bash
# If the Service is ClusterIP (default), port-forward to access
kubectl port-forward -n kube-system svc/container-networking-agent 8080:80
# Then open http://localhost:8080 in your browser
```

Or expose via your existing Istio wildcard Gateway + VirtualService if you want
team-wide access under a hostname like `net-agent.<wildcard-domain>`.

First-time sign-in uses either Microsoft Entra ID or a local username (depends
on how the extension is configured in your env).

## First-Run Smoke Test

Try these prompts to confirm the agent works (see `TEST-PROMPTS.md` for more):

1. **Read-only situational awareness:**
   > *"How many pods are running in the kube-system namespace?"*

   Should return a count + brief summary. Confirms Kubernetes API access.

2. **DNS health:**
   > *"Check CoreDNS health in this cluster."*

   Should run CoreDNS diagnostics and return a structured report.

3. **Harmless networking check:**
   > *"Is there any unusual packet loss on the nodes?"*

   Triggers deployment of the debug DaemonSet on first run (takes 30–60s).
   Subsequent runs are fast.

If all three return structured reports, the agent is working.

## Who Uses It

**Primary persona:** SREs during interactive debugging of gnarly networking issues.

**When to reach for it instead of your kagent pipeline:**

| Use case | Use this agent? |
|---|---|
| Alert fires → automated triage | ❌ Use the kagent pipeline |
| Routine health check | ❌ Use kagent scheduled workflows |
| DNS mystery, packet drops, "why is this pod not reachable" | ✅ Open the chat, ask in plain English |
| Pre-change validation ("will this network policy break anything?") | ✅ Chat with it before applying |
| Post-incident review needing deep network evidence | ✅ Chat + copy the evidence table into the ticket |

## Limitations to Know

- **Browser-only.** No API, no webhook, no programmatic invocation.
- **In-memory sessions.** Conversations lost on pod restart. Copy useful outputs to tickets.
- **Chat context ~15 exchanges.** Start new conversations for unrelated issues.
- **Concurrency limits.** 1–7 users typical; reduced on large clusters (25+ nodes).
- **Preview.** Available in limited regions; not covered by production SLA.
- **Per-cluster deployment.** Each AKS cluster needs its own extension install.

## Sample Install Script

See `install.sh` in this directory — one-shot script that registers the
provider, installs the extension, and prints the port-forward command. Edit
the variables at the top and run.

## Uninstall

```bash
az k8s-extension delete \
  --cluster-type managedClusters \
  --cluster-name <aks-name> \
  --resource-group <rg> \
  --name container-networking-agent --yes

# If the debug DaemonSet was orphaned:
kubectl delete ds rx-troubleshooting-debug -n kube-system --ignore-not-found
```

## What's Next

See `ROADMAP.md` for how this fits into the broader AI platform — specifically
the Phase 2 plan to build a kagent-native networking triage agent that can be
invoked programmatically from Argo Workflows, while leaving this Microsoft
agent in place for interactive deep dives.
