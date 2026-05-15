# IMDS Exposure on AKS — Risk, Assessment, and Mitigation

> **TL;DR:** Pods on AKS can reach the Azure Instance Metadata Service at `169.254.169.254` by default and request OAuth tokens for managed identities attached to the underlying node VMSS, normally the **kubelet managed identity**. The blast radius equals the Azure role assignments on those identities. This document explains the risk, provides assessment commands, and outlines mitigation options.

---

## 1. Background

### What is IMDS?

The Azure Instance Metadata Service (IMDS) is a non-routable REST API at `http://169.254.169.254` that returns metadata about the VM it is queried from — SKU, network configuration, tags, and crucially **OAuth 2.0 tokens for any managed identity attached to the VM**.

It is the foundational mechanism for "no credentials on disk" cloud authentication. AWS and GCP have equivalents (EC2 IMDS, GCE metadata server).

### Why it matters in AKS

On AKS, IMDS is reachable from each **node VM** (member of the node pool VMSS). The kubelet identity associated with the node pool is what kubelet uses for node-level operations such as authenticating to Azure Container Registry (ACR) when configured.

By default, AKS does **not** restrict pod egress to `169.254.169.254`. Any pod, in any namespace, with no special privileges, can request a token for a managed identity exposed through the node's IMDS endpoint. In the usual AKS case, that is the kubelet identity. The token's permissions equal whatever Azure RBAC roles have been granted to that identity.

This is the same attack pattern that caused the Capital One breach (2019) on AWS, and is the reason AWS introduced IMDSv2.

### The AKS identities most relevant to this risk

| Identity | Attached to | Reachable via pod IMDS? | Typical roles |
|---|---|---|---|
| **Control plane identity** | Managed control plane (Microsoft-owned) | **No** — pods cannot reach control plane hosts | Node resource group operations, networking, disk/LB management |
| **Kubelet identity** | Node pool VMSS (your VMs) | **Yes** — every pod can request a token | `AcrPull` on attached ACR (minimum) |
| **`cost-analysis-identity`** (if `--enable-cost-analysis` is set) | Node pool VMSS (your VMs) | **Yes** — every pod can request a token | Reader on the cluster's **node resource group** |
| **Other add-on identities** (e.g., AMA, AGIC, Key Vault CSI when not on WI) | Node pool VMSS (your VMs) | **Yes** — every pod can request a token | Varies per add-on |

The kubelet identity is the common exposed identity. Any additional managed identity attached to the node VMSS — whether added explicitly for "convenience" (Key Vault access, Storage Blob access, broader subscription Reader) or implicitly by an AKS add-on (cost analysis, AMA, AGIC, etc.) — is effectively shared with every workload that can reach IMDS. See §2.4 for the add-on inventory.

---

## 2. Risk Summary

### Default exposure on a stock AKS cluster

- Any pod can run `curl -H "Metadata: true" http://169.254.169.254/metadata/identity/oauth2/token?...` and get a bearer token when node IMDS is unrestricted.
- The token authenticates as a managed identity available to the **node VMSS the pod landed on**, normally the kubelet identity.
- No Kubernetes RBAC, namespace, or service account scoping applies — this traffic bypasses the API server entirely.
- Workload Identity does **not** close this hole by itself. It only provides a better alternative path for legitimate workloads.

### Multi-tenancy implications

On a shared platform cluster:

- Tenant A's pod can pull from ACR repos owned by Tenant B (since `AcrPull` is typically registry-scoped, not repo-scoped).
- Any SSRF vulnerability in a tenant workload becomes an Azure credential leak.
- Any role ever added to the kubelet identity is silently shared across all tenants on the cluster.
- Long-lived clusters accumulate role grants over time as engineers attach permissions for one-off integrations.

### Bypass: `hostNetwork: true`

Pods with `hostNetwork: true` share the node's network namespace and can bypass pod-level CNI policy and AKS native non-host-network IMDS restriction. Any IMDS control must be paired with admission policy (Kyverno/Gatekeeper) blocking unauthorised `hostNetwork` usage.

### AKS add-ons that compound exposure

Several first-party AKS add-ons quietly attach additional managed identities to the node VMSS, expanding the set of tokens that any pod can mint via IMDS. They're not malicious — they're a deliberate design choice by Microsoft that prioritises "works on any cluster" over "secure by default" — but each one needs to be tracked the same way the kubelet identity is.

| Add-on | Identity attached to node VMSS | Scope | Notes |
|---|---|---|---|
| `--enable-cost-analysis` | `cost-analysis-identity` | Reader on the cluster's **node resource group** | Used by the `cost-agent` pod to map Kubernetes objects to Azure billing data. The `cost-agent` is **not** `hostNetwork`, so it relies on IMDS for token acquisition. |
| Azure Monitor Agent (Container Insights) | AMA identity | Varies — typically Monitoring Metrics Publisher | DaemonSet runs `hostNetwork: true`. |
| AGIC (Application Gateway Ingress Controller) | AGIC identity | `Contributor` on the Application Gateway, `Reader` on the AGW resource group | Often broader than expected; audit carefully. |
| Azure Key Vault Provider for Secrets Store CSI (legacy, pre-WI) | Per-cluster UAMI | `Key Vault Secrets User` on attached vaults | Should be migrated to Workload Identity. |
| Azure Policy add-on | Azure Policy identity | Read access on policy assignments | Minor exposure. |

**Viewer-side exposure (cost analysis specifically).** Enabling cost analysis also requires that anyone wanting to *view* cost data hold one of `Owner`, `Contributor`, `Reader`, `Cost Management Contributor`, or `Cost Management Reader` **at subscription scope** ([source](https://learn.microsoft.com/en-us/azure/aks/cost-analysis)). There is no resource-group-scoped option. On a shared platform subscription this means granting cost-analysis access to Tenant A effectively lets them enumerate every resource Tenant B owns. `Cost Management Reader` is narrower than plain `Reader` (it's scoped to cost + budgets), but the subscription-wide enumeration concern remains.

**Action:** include every add-on identity in the §3.2 role-assignment audit, not just the kubelet identity, and revisit when any new add-on is enabled.

---

## 3. Assessment Commands

The Azure inventory commands below are read-only. The in-cluster proof commands create a short-lived pod and may mint real bearer tokens; run those only as controlled security testing, avoid logging tokens, and delete the test namespace afterwards.

### 3.1 Identify the kubelet identity on each cluster

```bash
# Get both identities
az aks show \
  --resource-group {{RESOURCE_GROUP}} \
  --name {{CLUSTER_NAME}} \
  --query "{controlPlane: identity, kubelet: identityProfile.kubeletidentity}" \
  -o json

# Extract just the kubelet identity's principal ID (object ID)
KUBELET_PRINCIPAL=$(az aks show \
  --resource-group {{RESOURCE_GROUP}} \
  --name {{CLUSTER_NAME}} \
  --query "identityProfile.kubeletidentity.objectId" \
  -o tsv)

echo "Kubelet identity principal ID: $KUBELET_PRINCIPAL"
```

### 3.2 Enumerate role assignments on the kubelet identity

This is **the** command to understand blast radius. Ideally the output is short: `AcrPull` scoped to your ACR(s) and nothing else.

```bash
# All role assignments for the kubelet identity, across all scopes
az role assignment list \
  --assignee "$KUBELET_PRINCIPAL" \
  --all \
  -o table

# Same data with full scope detail for audit
az role assignment list \
  --assignee "$KUBELET_PRINCIPAL" \
  --all \
  --query "[].{Role:roleDefinitionName, Scope:scope, PrincipalType:principalType}" \
  -o json
```

**Flags for follow-up:**
- Any `Contributor`, `Owner`, or `User Access Administrator` role → critical, investigate immediately
- Roles at subscription or management group scope → high risk
- Key Vault Secrets User, Storage Blob Data Reader/Contributor → assess what data is reachable
- Anything beyond `AcrPull` → document the justification

#### Also enumerate every add-on identity on the node VMSS

Add-ons attach their own managed identities to the same node VMSS as kubelet (see §2.4). Each one is reachable from every pod via IMDS, so each one needs the same audit. The most common one today is `cost-analysis-identity`:

```bash
# List every user-assigned identity attached to the node VMSS, across all node pools.
NODE_RG=$(az aks show \
  --resource-group {{RESOURCE_GROUP}} \
  --name {{CLUSTER_NAME}} \
  --query "nodeResourceGroup" -o tsv)

for VMSS in $(az vmss list --resource-group "$NODE_RG" --query "[].name" -o tsv); do
  echo "=== VMSS: $VMSS ==="
  az vmss identity show \
    --resource-group "$NODE_RG" \
    --name "$VMSS" \
    --query "userAssignedIdentities" -o json
done
```

For every principal ID returned, repeat the §3.2 `az role assignment list --assignee <principalId> --all` command. Document each identity's purpose, owner, and migration status to Workload Identity in your IMDS exception inventory (§5.2).

### 3.3 Audit the control plane identity (for completeness)

Not exposed via pod IMDS, but worth keeping tight.

```bash
CONTROL_PLANE_PRINCIPAL=$(az aks show \
  --resource-group {{RESOURCE_GROUP}} \
  --name {{CLUSTER_NAME}} \
  --query "identity.principalId" \
  -o tsv)

az role assignment list \
  --assignee "$CONTROL_PLANE_PRINCIPAL" \
  --all \
  -o table
```

### 3.4 Demonstrate exposure from inside the cluster

Create a non-privileged pod in a disposable test namespace and prove it can reach IMDS. Treat any returned token as sensitive.

```bash
kubectl create namespace imds-probe

# Run an ephemeral debug pod (no special privileges)
kubectl run imds-probe \
  --rm -it --restart=Never \
  --image=mcr.microsoft.com/azure-cli:latest \
  --namespace=imds-probe \
  -- bash
```

Then inside the pod shell:

```bash
# Confirm reachability
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Metadata: true" \
  --noproxy "*" \
  "http://169.254.169.254/metadata/instance?api-version=2023-11-15"

# Pull instance metadata (no auth needed)
curl -s -H "Metadata: true" \
  --noproxy "*" \
  "http://169.254.169.254/metadata/instance?api-version=2023-11-15" | jq .

# Request a token for ARM — this is the dangerous one
curl -s -H "Metadata: true" \
  --noproxy "*" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/" | jq .

# Request a token for ACR
curl -s -H "Metadata: true" \
  --noproxy "*" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://containerregistry.azure.net/" | jq .
```

If the token endpoints return a JSON object with `access_token`, the cluster is exposed. To prove blast radius, decode the token at [jwt.io](https://jwt.io) (do **not** paste production tokens into a public site — use a local JWT decoder or `jq` on the base64-decoded middle segment):

```bash
# Local decode of the JWT payload
TOKEN=$(curl -s -H "Metadata: true" --noproxy "*" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/" \
  | jq -r .access_token)

PAYLOAD=$(echo "$TOKEN" | cut -d. -f2 | tr '_-' '/+')
case $((${#PAYLOAD} % 4)) in
  2) PAYLOAD="${PAYLOAD}==" ;;
  3) PAYLOAD="${PAYLOAD}=" ;;
  0) ;;
  *) echo "Invalid JWT payload length"; exit 1 ;;
esac
echo "$PAYLOAD" | base64 -d 2>/dev/null | jq .
```

The `oid` claim is the kubelet identity's object ID. Confirm it matches `$KUBELET_PRINCIPAL` from section 3.1.

### 3.5 Demonstrate what the token can actually do

With the token from above, list resources the kubelet identity can see at subscription scope. If this returns anything, role assignments are too broad.

```bash
# From inside the pod, or anywhere with the token
SUBSCRIPTION_ID={{SUBSCRIPTION_ID}}

curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups?api-version=2021-04-01" \
  | jq '.value[].name'
```

A correctly-scoped kubelet identity should return an authorisation error (403) or an empty list. Unset `TOKEN` when finished.

```bash
unset TOKEN PAYLOAD
kubectl delete namespace imds-probe
```

### 3.6 Find hostNetwork pods in the cluster

These bypass any CNI-based IMDS restriction.

```bash
kubectl get pods --all-namespaces \
  -o jsonpath='{range .items[?(@.spec.hostNetwork==true)]}{.metadata.namespace}{"\t"}{.metadata.name}{"\n"}{end}' \
  | sort -u
```

System namespaces (`kube-system`, `gatekeeper-system`, CNI daemonsets) are expected. Anything in a tenant namespace warrants investigation.

### 3.7 Identify pods using IMDS in flight (Cilium)

If Cilium Hubble is enabled, you can observe IMDS traffic directly:

```bash
# Requires hubble CLI configured against the cluster
hubble observe --to-ip 169.254.169.254 --last 1000
```

This shows which pods are actually hitting IMDS today, useful for building the allowlist before applying a deny policy.

---

## 4. Who Legitimately Needs IMDS

Before locking anything down, build the allowlist. The shorter list every year — as Workload Identity matures, fewer components need IMDS access.

### Genuinely needs IMDS (cannot be migrated)

| Component | Namespace | Why | Notes |
|---|---|---|---|
| kubelet | (host process) | Pull images using kubelet identity | Not a pod — bypasses CNI policy anyway |
| Azure cloud controller manager | `kube-system` | Node identity, LB management | Runs hostNetwork |
| Azure CNI / Cilium control plane | `kube-system` or `cilium` | Node-level networking setup | Runs hostNetwork |
| Azure Monitor Agent (ama-logs) | `kube-system` | Node-level metrics collection | Runs hostNetwork — bypasses CNI policy |
| csi-azuredisk-node, csi-azurefile-node | `kube-system` | Disk attach/detach as node identity | DaemonSet, hostNetwork |

### Supports Workload Identity — should be migrated

| Component | Status | Action |
|---|---|---|
| Azure Key Vault Provider for Secrets Store CSI | Supported | Configure with WI; no IMDS needed |
| External Secrets Operator | Supported | Configure with WI |
| cert-manager (Azure DNS solver) | Supported | Configure with WI |
| Azure Service Operator (ASO) | Supported | Already on WI in our golden path |
| Argo Workflows / Events (when calling Azure APIs) | Supported | Per-workflow WI |

### Should never need IMDS

- **Any tenant application pod.** If one is hitting IMDS, it's either legacy code or an attack indicator.
- **Any pod with a federated service account.** By definition has its own token.

---

## 5. Mitigation: Defence in Depth Bundle

These six layers compose. None require AKS preview features, none break Flux, and each is independently valuable. Recommended deployment order is the rollout sequence in section 7.

### 5.1 Layer 1: Cilium clusterwide policy — default deny IMDS to tenants

Blocks pod egress to `169.254.169.254` from any namespace not on the platform allowlist. Survives node reimage. Per-namespace granularity. Works alongside everything in our stack.

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: deny-imds-egress-tenants
  annotations:
    platform.example.com/owner: "platform-security"
    platform.example.com/purpose: "Prevent tenant pods from acquiring node managed identity tokens via IMDS"
spec:
  description: "Deny egress to Azure IMDS from all namespaces except platform allowlist"
  endpointSelector:
    matchExpressions:
      # Apply to all pods EXCEPT those in platform namespaces below
      - key: io.kubernetes.pod.namespace
        operator: NotIn
        values:
          - kube-system
          - kube-public
          - kube-node-lease
          - cilium
          - flux-system
          - gatekeeper-system
          - kyverno
          - azure-workload-identity-system
          - external-secrets
          - cert-manager
          - aso-system
          - argo
          - argo-events
          - istio-system
          - aks-istio-system
          - aks-istio-ingress
          - aks-istio-egress
          - observability
          - monitoring
          # Add platform namespaces here, NEVER add tenant namespaces
  # Keep existing broad egress behavior for selected endpoints.
  # Without this allow, selecting endpoints with an egress policy can place
  # them into egress default-deny mode and block more than IMDS.
  egress:
    - toEntities:
        - all
  egressDeny:
    - toCIDR:
        - 169.254.169.254/32
```

**Important:** every namespace added to this allowlist is a privileged namespace. Treat additions like RBAC changes — they need review. The whole point of the policy is that tenant namespaces *cannot* add themselves to it.

### 5.2 Layer 2: platform IMDS exception inventory

A Cilium allow policy cannot override a matching `egressDeny`; deny rules win. Platform access is therefore controlled by the namespace allowlist in section 5.1, and the exception list below is an auditable inventory of which service accounts are expected to use IMDS inside those platform namespaces.

Keep this inventory in Git next to the policy and review it like RBAC. Every entry should have an owner, reason, and migration status.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: imds-platform-exceptions
  namespace: platform-security
  annotations:
    platform.example.com/owner: "platform-security"
data:
  exceptions.yaml: |
    - namespace: kube-system
      serviceAccount: cloud-node-manager
      reason: "Azure cloud provider node integration"
      migration: "not-migratable"
    - namespace: kube-system
      serviceAccount: csi-azuredisk-node-sa
      reason: "Node-level disk operations"
      migration: "not-migratable"
    - namespace: kube-system
      serviceAccount: csi-azurefile-node-sa
      reason: "Node-level file operations"
      migration: "not-migratable"
    - namespace: kube-system
      serviceAccount: ama-logs
      reason: "Azure Monitor node agent"
      migration: "review"
```

Use Hubble to compare observed traffic with the inventory:

```bash
hubble observe \
  --to-ip 169.254.169.254 \
  --last 1000 \
  -o json \
  | jq -r '.flow
           | select(.destination.IP=="169.254.169.254")
           | [.source.namespace, .source.pod_name, .source.identity] | @tsv' \
  | sort -u
```

### 5.3 Layer 3: Kyverno policy — block hostNetwork in tenant namespaces

Closes the bypass. `hostNetwork: true` pods reach IMDS regardless of any CNI policy.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-host-network-tenants
  annotations:
    policies.kyverno.io/title: "Disallow hostNetwork in tenant namespaces"
    policies.kyverno.io/category: "Multi-Tenancy"
    policies.kyverno.io/severity: "high"
    policies.kyverno.io/description: >-
      hostNetwork pods share the node's network namespace and can reach
      the Azure IMDS endpoint (169.254.169.254) regardless of any CNI
      network policy. Tenant workloads must run with hostNetwork: false.
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: block-host-network
      match:
        any:
          - resources:
              kinds: [Pod]
      exclude:
        any:
          # Platform namespaces explicitly permitted (matches Cilium allowlist)
          - resources:
              namespaces:
                - kube-system
                - kube-public
                - cilium
                - flux-system
                - gatekeeper-system
                - kyverno
                - azure-workload-identity-system
                - istio-system
                - aks-istio-system
                - observability
                - monitoring
      validate:
        message: >-
          hostNetwork: true is not permitted in tenant namespaces.
          This setting allows pods to bypass network policy and reach
          the Azure IMDS endpoint. Contact the platform team if your
          workload requires host network access.
        pattern:
          spec:
            =(hostNetwork): "false"
```

### 5.4 Layer 4: Kyverno policy — audit pods without Workload Identity

Visibility play. Doesn't block anything, but flags workloads in tenant namespaces that are *likely* to break when the deny rule turns on. Use the audit output to drive tenant migration before enforcement.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: audit-pods-without-workload-identity
  annotations:
    policies.kyverno.io/title: "Audit pods missing Workload Identity"
    policies.kyverno.io/category: "Multi-Tenancy"
    policies.kyverno.io/severity: "medium"
    policies.kyverno.io/description: >-
      Identifies pods in tenant namespaces whose service account does not
      have the azure.workload.identity/use=true label, indicating they may
      rely on IMDS for Azure authentication.
spec:
  validationFailureAction: Audit
  background: true
  rules:
    - name: check-wi-label
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaceSelector:
                matchExpressions:
                  - key: tier
                    operator: In
                    values: ["tenant"]
      validate:
        message: >-
          Pod's service account does not have label
          azure.workload.identity/use=true. If this workload needs Azure
          access it should use Workload Identity, not IMDS.
        deny:
          conditions:
            all:
              - key: "{{ request.object.spec.serviceAccountName || 'default' }}"
                operator: NotEquals
                value: ""
              - key: >-
                  {{ lookup('v1/ServiceAccount',
                  request.namespace,
                  request.object.spec.serviceAccountName || 'default').metadata.labels."azure.workload.identity/use"
                  || 'false' }}
                operator: NotEquals
                value: "true"
```

Query the audit output:

```bash
kubectl get policyreport -A \
  -o json \
  | jq '.items[].results[]
        | select(.policy=="audit-pods-without-workload-identity"
                 and .result=="fail")
        | {namespace: .resources[0].namespace, pod: .resources[0].name}'
```

### 5.5 Layer 5: Kyverno policy — auto-generate per-namespace baseline egress

Optional but powerful. When a new tenant namespace is created via your KRO/Flux Tier 1 onboarding, auto-inject a baseline `CiliumNetworkPolicy` that establishes egress posture (including the IMDS deny) without each tenant having to author it.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-tenant-baseline-egress
spec:
  rules:
    - name: tenant-baseline-egress-policy
      match:
        any:
          - resources:
              kinds: [Namespace]
              selector:
                matchLabels:
                  tier: tenant
      generate:
        apiVersion: cilium.io/v2
        kind: CiliumNetworkPolicy
        name: tenant-baseline-egress
        namespace: "{{request.object.metadata.name}}"
        synchronize: true
        data:
          metadata:
            annotations:
              platform.example.com/generated-by: "kyverno"
              platform.example.com/policy: "tenant-baseline-egress"
          spec:
            description: "Tenant baseline egress posture"
            endpointSelector: {}
            # Keep existing broad egress behavior unless this namespace also
            # has a stricter tenant egress allowlist. Merge this deny with that
            # allowlist instead of deploying two competing baselines.
            egress:
              - toEntities:
                  - all
            egressDeny:
              - toCIDR:
                  - 169.254.169.254/32  # IMDS
                  - 169.254.0.0/16      # Other link-local
```

This means tenants always start with IMDS blocked at their namespace level, even if the clusterwide policy is somehow misconfigured. Defence in depth.

### 5.6 Layer 6: Right-size the kubelet identity

Independent of network controls — reduces blast radius if any layer above fails.

Target state per cluster:
- `AcrPull` scoped to specific ACR resources (not subscription scope)
- No other role assignments unless explicitly justified
- Quarterly audit using section 3.2 commands
- Document any deviation in a registered exception

If a workload needs Azure access, the answer is always **Workload Identity with a per-workload federated UAMI**, never a role grant on the kubelet identity.

### 5.7 AKS native IMDS restriction (`--enable-imds-restriction`) — what it covers and when to use it

Microsoft offers `--enable-imds-restriction` on `az aks create`/`update`. AKS manages iptables rules on each node, restored on reimage. It's currently **preview** and excluded from the AKS SLA.

#### What it does close

- Blocks **non-`hostNetwork` pods** from reaching `169.254.169.254`. This is the primary risk: tenant workloads, sidecars, anything running with the default pod network namespace can no longer mint tokens for the kubelet identity or any other VMSS-attached identity.
- Survives node reimage — AKS reapplies the iptables rules automatically.

#### What still has IMDS access (by design — not broken)

Anything with `hostNetwork: true` shares the node's network namespace and bypasses the iptables rule. This is intentional, because the following components need IMDS to function and already run hostNetwork:

- kubelet itself (host process, not even a pod)
- Azure cloud controller manager / `cloud-node-manager`
- Azure CNI / Cilium control plane
- Azure Monitor Agent (`ama-logs`)
- CSI drivers (`csi-azuredisk-node`, `csi-azurefile-node`)

So the legitimate platform IMDS users keep working. This also means `--enable-imds-restriction` **does not close the `hostNetwork: true` bypass** — you still need the Kyverno policy from §5.3 to block tenant pods from setting `hostNetwork: true`.

#### What it breaks

Microsoft hard-blocks `--enable-imds-restriction` from being enabled on clusters with these add-ons (admission-time gate, not a runtime issue):

- **AKS Flux extension** — alone, this is a deal-breaker for any platform using GitOps via the Flux extension for Tier 1 onboarding
- Container Insights
- Azure Policy add-on
- AGIC (Application Gateway Ingress Controller)
- AKS Backup
- Dapr, App Configuration, ML extension, Container Storage, Virtual Nodes, App Routing, AI toolchain operator
- **Windows node pools** — not supported at all

It will also break any **non-hostNetwork pod that legitimately uses IMDS** — including the `cost-agent` pod added by `--enable-cost-analysis`, which is not hostNetwork. With both flags enabled, cost analysis silently stops collecting data because the agent cannot mint tokens for `cost-analysis-identity`. Microsoft has not (as of this writing) added cost analysis to the documented incompatibility list, but functionally it is broken. Verify in a sandbox before enabling both.

In general, tenant pods that "legitimately" need IMDS are migration candidates for Workload Identity anyway — that pressure is the desired outcome.

#### When the native restriction is actually fine

- **Greenfield clusters that don't need the AKS Flux extension, Container Insights, AGIC, or cost analysis**, and run Linux only — for these, `--enable-imds-restriction` is simpler than the Cilium stack and a perfectly reasonable choice.
- **Sandbox / non-prod clusters** to validate the iptables behaviour and exercise the migration of identified IMDS callers to Workload Identity ahead of broader rollout.

#### Why it doesn't fit this platform today

- Preview, excluded from AKS SLA — unsuitable for a regulated production platform.
- The **AKS Flux extension exclusion alone breaks Tier 1**.
- Windows node pool support missing.
- All-or-nothing per cluster — no per-namespace granularity, no allowlist by service account, no Hubble observability.

The Cilium-based bundle in §5.1–5.5 was chosen because it is GA, doesn't conflict with the Flux extension, gives per-namespace allowlists, works on Windows node pools at the CNI layer, and lets Hubble show you who is actually hitting IMDS.

**Re-evaluate `--enable-imds-restriction` when:** the feature reaches GA *and* the Flux extension / Azure Policy / Container Insights exclusions are resolved. Track the upstream AKS issue tracker quarterly.

---

## 6. Verifying the Policies Work

After deploying the bundle in section 5, run these tests to confirm enforcement.

### 6.1 Tenant pod is blocked

```bash
# Create a test tenant namespace (or use an existing one)
kubectl create namespace tenant-imds-test
kubectl label namespace tenant-imds-test tier=tenant

# Run a probe pod
kubectl run imds-probe \
  --rm -it --restart=Never \
  --image=mcr.microsoft.com/azure-cli:latest \
  --namespace=tenant-imds-test \
  -- bash
```

Inside the pod:

```bash
# Should time out — Cilium deny in effect
curl -s --max-time 5 \
  -H "Metadata: true" \
  "http://169.254.169.254/metadata/instance?api-version=2023-11-15"
echo "Exit code: $?"  # 28 = timeout = policy working
```

Expected: connection times out, no token returned.

### 6.2 hostNetwork bypass is blocked by Kyverno

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: hostnet-bypass-test
  namespace: tenant-imds-test
spec:
  hostNetwork: true
  containers:
    - name: probe
      image: mcr.microsoft.com/azure-cli:latest
      command: ["sleep", "3600"]
EOF
```

Expected: admission denied with the Kyverno policy message.

### 6.3 Platform component still works

Pick a platform pod that legitimately uses IMDS and verify it still functions:

```bash
# Check ama-logs DaemonSet is healthy and ingesting
kubectl -n kube-system get ds ama-logs
kubectl -n kube-system logs -l rsName=ama-logs --tail=20 | grep -i error

# Check cloud-node-manager is healthy
kubectl -n kube-system get ds cloud-node-manager
```

### 6.4 Hubble confirms denies

```bash
# Should show DROPPED flows from tenant namespaces to 169.254.169.254
hubble observe \
  --to-ip 169.254.169.254 \
  --verdict DROPPED \
  --last 100
```

### 6.5 Cleanup

```bash
kubectl delete namespace tenant-imds-test
```

---

## 7. Recommended Rollout Sequence

1. **Preflight CRDs** — confirm Cilium and Kyverno CRDs exist before applying the bundle.
2. **Assess** — run section 3 commands against all production AKS clusters. Document kubelet identity role assignments per cluster in a tracking spreadsheet.
3. **Trim identities** — remove any unjustified roles on kubelet identities. Move workload-specific Azure access to per-workload federated UAMIs.
4. **Observe before enforcing** — apply section 5.4 (Workload Identity audit) and use Hubble flow data for 1-2 weeks per region. Do not treat a Cilium allow policy as audit mode for a future deny policy.
5. **Build the allowlist from observed data** — Hubble `--to-ip 169.254.169.254` flow logs tell you who's actually calling IMDS. Cross-reference with section 4 to identify required vs migratable callers.
6. **Migrate identified callers to Workload Identity** — most should be straightforward (KV CSI, External Secrets, cert-manager are all WI-capable today).
7. **Deploy Kyverno hostNetwork policy (5.3)** — enforce in tenant namespaces first.
8. **Deploy Cilium deny policy (5.1)** — start in one region, monitor for breakage for 48 hours, then roll across regions.
9. **Add baseline egress generation (5.5)** — apply to all newly-created tenant namespaces via the KRO Tier 1 path after confirming the Kyverno background controller can create Cilium resources.
10. **Verify** — section 6 tests on each cluster post-deployment.
11. **Track AKS IMDS restriction GA** — re-evaluate the native feature when Flux extension and Azure Policy support land.

---

## 8. Operational Notes

### Detection signal

Once the deny policy is live, **any** IMDS access attempt from a tenant namespace is a signal. Example Hubble CLI check:

```bash
hubble observe \
  --to-ip 169.254.169.254 \
  --verdict DROPPED \
  --last 1000 \
  -o json \
  | jq -r '.flow
           | select(.source.namespace as $ns
                    | ["kube-system","cilium","kyverno","monitoring"] | index($ns) | not)
           | [.time, .source.namespace, .source.pod_name, .verdict] | @tsv'
```

A high rate of drops from one namespace suggests either a workload trying to legitimately use Azure (which should be migrated to WI) or, less commonly, an exploitation attempt.

### Emergency bypass

If a critical platform workload needs temporary IMDS access during an incident, the procedure is:

1. Add the platform-owned workload namespace to the Cilium policy allowlist (PR with security approval).
2. Set an expiry date on the addition.
3. Migrate to Workload Identity within the window.

Never add a tenant namespace to the allowlist. The whole point of the policy is that tenants don't have this escape hatch.

### Re-audit cadence

Quarterly:
- Re-run section 3.2 against every cluster — kubelet identity role drift detection.
- Review Cilium policy allowlist — every entry should still be justified.
- Review Kyverno hostNetwork exception list — same.

---

## 9. Validation Evidence

### 2026-05-15 local non-AKS test cluster

This evidence is from a local non-AKS Kubernetes cluster using the `red` context. It is useful for checking manifest gating and generic pod reachability, but it does **not** prove AKS managed identity exposure.

| Check | Result |
|---|---|
| API reachability | Kubernetes API reachable through current `red` context; endpoint omitted from this public document |
| IMDS probe pod | Disposable pod curl to `169.254.169.254` timed out: `http_code=000`, curl exit `28` |
| Cilium CRDs | `CiliumClusterwideNetworkPolicy` and `CiliumNetworkPolicy` CRDs absent |
| Kyverno CRDs | `ClusterPolicy` and `PolicyReport` CRDs present |
| Kyverno hostNetwork policy | Accepted by `kubectl apply --dry-run=server` |
| Kyverno Workload Identity audit policy | Accepted by `kubectl apply --dry-run=server` |
| Kyverno generate Cilium baseline | Rejected by Kyverno admission because `cilium.io/v2/CiliumNetworkPolicy` GVR is missing |
| Cilium deny policy | Rejected by Kubernetes discovery because `cilium.io/v2/CiliumClusterwideNetworkPolicy` CRD is missing |
| Cleanup | Disposable namespace `imds-probe-red` deleted |

Conclusion: the red cluster is not a valid target for Cilium enforcement testing because Cilium CRDs are not installed. The timeout confirms that this non-AKS cluster does not expose an Azure IMDS endpoint to ordinary pods, which is expected and should not be generalized to AKS.

---

## 10. References

- [Azure Instance Metadata Service overview](https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service)
- [Block pod access to the IMDS endpoint (preview)](https://learn.microsoft.com/en-us/azure/aks/imds-restriction)
- [Microsoft Entra Workload ID for AKS](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Cilium network policies](https://docs.cilium.io/en/stable/security/policy/)
- [Cilium deny policies](https://docs.cilium.io/en/stable/security/policy/deny/)
- [Kyverno generate rules](https://kyverno.io/docs/policy-types/cluster-policy/generate/)
- Capital One breach post-mortem (2019) — IMDS as the original attack vector
