# IMDS Exposure on AKS — Risk, Assessment, and Mitigation

> **TL;DR:** Every pod on every AKS cluster can reach the Azure Instance Metadata Service at `169.254.169.254` by default and acquire an OAuth token for the **kubelet managed identity** attached to the underlying VMSS. The blast radius equals the role assignments on that identity. This document explains the risk, provides commands to assess current exposure, and outlines mitigation options.

---

## 1. Background

### What is IMDS?

The Azure Instance Metadata Service (IMDS) is a non-routable REST API at `http://169.254.169.254` that returns metadata about the VM it is queried from — SKU, network configuration, tags, and crucially **OAuth 2.0 tokens for any managed identity attached to the VM**.

It is the foundational mechanism for "no credentials on disk" cloud authentication. AWS and GCP have equivalents (EC2 IMDS, GCE metadata server).

### Why it matters in AKS

On AKS, IMDS lives on each **node VM** (member of the node pool VMSS). The kubelet identity attached to that VMSS is what kubelet uses to pull images from ACR.

By default, AKS does **not** restrict pod egress to `169.254.169.254`. Any pod, in any namespace, with no special privileges, can request a token for the kubelet identity. The token's permissions equal whatever Azure RBAC roles have been granted to that identity.

This is the same attack pattern that caused the Capital One breach (2019) on AWS, and is the reason AWS introduced IMDSv2.

### The two UAMIs on a standard AKS deploy

| Identity | Attached to | Reachable via pod IMDS? | Typical roles |
|---|---|---|---|
| **Control plane identity** | Managed control plane VMs (Microsoft-owned) | **No** — pods cannot reach those VMs | Network Contributor on node RG, disk operations, LB management |
| **Kubelet identity** | Node pool VMSS (your VMs) | **Yes** — every pod can request a token | `AcrPull` on attached ACR (minimum) |

The kubelet identity is the one exposed. Any role ever attached to it for "convenience" (Key Vault access, Storage Blob access, broader subscription Reader) is effectively granted to every workload on the cluster.

---

## 2. Risk Summary

### Default exposure on a stock AKS cluster

- Any pod can run `curl -H "Metadata: true" http://169.254.169.254/metadata/identity/oauth2/token?...` and get a bearer token.
- The token authenticates as the **kubelet identity of the VMSS the pod landed on**.
- No Kubernetes RBAC, namespace, or service account scoping applies — this traffic bypasses the API server entirely.
- Workload Identity does **not** close this hole by itself. It only provides a better alternative path for legitimate workloads.

### Multi-tenancy implications

On a shared platform cluster:

- Tenant A's pod can pull from ACR repos owned by Tenant B (since `AcrPull` is typically registry-scoped, not repo-scoped).
- Any SSRF vulnerability in a tenant workload becomes an Azure credential leak.
- Any role ever added to the kubelet identity is silently shared across all tenants on the cluster.
- Long-lived clusters accumulate role grants over time as engineers attach permissions for one-off integrations.

### Bypass: `hostNetwork: true`

Pods with `hostNetwork: true` share the node's network namespace and reach IMDS regardless of any CNI policy or iptables rule. Any IMDS control must be paired with admission policy (Kyverno/Gatekeeper) blocking unauthorised `hostNetwork` usage.

---

## 3. Assessment Commands

These commands are **read-only** and safe to run against production clusters. They establish current exposure without changing anything.

### 3.1 Identify the kubelet identity on each cluster

```bash
# Get both identities
az aks show \
  --resource-group <rg> \
  --name <cluster> \
  --query "{controlPlane: identity, kubelet: identityProfile.kubeletidentity}" \
  -o json

# Extract just the kubelet identity's principal ID (object ID)
KUBELET_PRINCIPAL=$(az aks show \
  --resource-group <rg> \
  --name <cluster> \
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

### 3.3 Audit the control plane identity (for completeness)

Not exposed via pod IMDS, but worth keeping tight.

```bash
CONTROL_PLANE_PRINCIPAL=$(az aks show \
  --resource-group <rg> \
  --name <cluster> \
  --query "identity.principalId" \
  -o tsv)

az role assignment list \
  --assignee "$CONTROL_PLANE_PRINCIPAL" \
  --all \
  -o table
```

### 3.4 Demonstrate exposure from inside the cluster

Create a non-privileged pod in a test namespace and prove it can reach IMDS. This is what every tenant workload can do.

```bash
# Run an ephemeral debug pod (no special privileges)
kubectl run imds-probe \
  --rm -it --restart=Never \
  --image=mcr.microsoft.com/azure-cli:latest \
  --namespace=default \
  -- bash
```

Then inside the pod shell:

```bash
# Confirm reachability
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Metadata: true" \
  "http://169.254.169.254/metadata/instance?api-version=2023-11-15"

# Pull instance metadata (no auth needed)
curl -s -H "Metadata: true" \
  "http://169.254.169.254/metadata/instance?api-version=2023-11-15" | jq .

# Request a token for ARM — this is the dangerous one
curl -s -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/" | jq .

# Request a token for ACR
curl -s -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://containerregistry.azure.net/" | jq .
```

If the token endpoints return a JSON object with `access_token`, the cluster is exposed. To prove blast radius, decode the token at [jwt.io](https://jwt.io) (do **not** paste production tokens into a public site — use a local JWT decoder or `jq` on the base64-decoded middle segment):

```bash
# Local decode of the JWT payload
TOKEN=$(curl -s -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/" \
  | jq -r .access_token)

echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq .
```

The `oid` claim is the kubelet identity's object ID. Confirm it matches `$KUBELET_PRINCIPAL` from section 3.1.

### 3.5 Demonstrate what the token can actually do

With the token from above, list resources the kubelet identity can see at subscription scope. If this returns anything, role assignments are too broad.

```bash
# From inside the pod, or anywhere with the token
SUBSCRIPTION_ID=<your-sub-id>

curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups?api-version=2021-04-01" \
  | jq '.value[].name'
```

A correctly-scoped kubelet identity should return an authorisation error (403) or an empty list.

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

## 4. Mitigation Options

### 4.1 Cilium egress policy (recommended for our platform)

Block egress to IMDS from tenant namespaces, allowlist system components. Per-namespace granularity, survives node reimage (policy is in etcd), and works alongside Flux/Azure Policy/Container Insights — none of which are excluded.

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: deny-imds-tenant-namespaces
spec:
  endpointSelector:
    matchExpressions:
      - key: io.kubernetes.pod.namespace
        operator: NotIn
        values:
          - kube-system
          - gatekeeper-system
          - flux-system
          - azure-workload-identity-system
          - cilium
          - kube-public
          # Add other infra namespaces as required
  egressDeny:
    - toCIDR:
        - 169.254.169.254/32
```

Roll out in audit mode first (Cilium `enable-policy=audit` or apply to a single namespace) to catch any legitimate IMDS usage before enforcing broadly.

### 4.2 Kyverno policy blocking hostNetwork

Closes the bypass. Required regardless of which IMDS control is chosen.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-host-network
spec:
  validationFailureAction: Enforce
  rules:
    - name: host-network
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
        message: "hostNetwork is not permitted in tenant namespaces."
        pattern:
          spec:
            =(hostNetwork): "false"
```

### 4.3 AKS native IMDS restriction (preview — not currently usable for our platform)

Microsoft offers `--enable-imds-restriction` on `az aks create` / `az aks update`. AKS manages iptables rules on each node to block non-hostNetwork pod egress to IMDS, restored on reimage.

**Why it doesn't fit our golden path today:**

- Still in **preview** (feature flag `IMDSRestrictionPreview`), excluded from AKS SLAs.
- **Unsupported add-ons** include: AKS Flux extension (GitOps), Container Insights, Azure Policy, Application Gateway Ingress Controller, AKS Backup, Dapr, App Configuration, ML, Container Storage, Virtual Nodes, App Routing, AI toolchain operator, Azure cost analysis.
- The Flux extension exclusion alone makes this incompatible with Tier 1 onboarding.

**Re-evaluate when:**
- The feature reaches GA.
- The Flux and Azure Policy exclusions are resolved.

Worth registering the feature flag in a non-prod subscription now and validating behaviour on a throwaway cluster without Flux, so the platform team has hands-on experience before GA.

### 4.4 Right-size the kubelet identity

Independent of network controls. Treat the kubelet identity as a privileged identity requiring change control. Target state:

- `AcrPull` on the specific ACR (not subscription-scoped).
- No other roles unless explicitly justified and documented.
- Periodic audit (quarterly minimum) against the output of section 3.2.

For workload-specific Azure access, use **Workload Identity** with per-workload federated UAMIs — not role grants on the kubelet identity.

### 4.5 Workload Identity as the only sanctioned path

Once Workload Identity is the default on Tier 1, no application pod has a legitimate reason to call IMDS. Any IMDS traffic from a tenant namespace is then a signal — either a misconfigured workload or an attack — and the Cilium deny policy is safe to enforce broadly.

---

## 5. Recommended Rollout Sequence

1. **Assess** — run section 3 commands against all production clusters. Document current kubelet identity role assignments per cluster.
2. **Trim** — remove any unjustified roles on kubelet identities. Move workload-specific Azure access to Workload Identity.
3. **Observe** — enable Hubble flow logs to `169.254.169.254` in audit mode. Build the allowlist of system namespaces that legitimately call IMDS.
4. **Enforce hostNetwork policy** — apply Kyverno policy section 4.2 in tenant namespaces.
5. **Enforce CNI deny** — apply Cilium policy section 4.1, starting with audit, then enforce per-region.
6. **Verify** — re-run section 3.4 from a tenant namespace. The token endpoint should time out.
7. **Track AKS IMDS restriction GA** — re-evaluate the native feature when Flux extension and Azure Policy support land.

---

## 6. References

- [Azure Instance Metadata Service overview](https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service)
- [Block pod access to the IMDS endpoint (preview)](https://learn.microsoft.com/en-us/azure/aks/imds-restriction)
- [Microsoft Entra Workload ID for AKS](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Cilium network policies](https://docs.cilium.io/en/stable/security/policy/)
- Capital One breach post-mortem (2019) — IMDS as the original attack vector
