# Azure Policy Exceptions — kagent + agentgateway

## 1. Identify policy violations on your cluster

These commands surface Azure Policy denials and audit events for a namespace:

```bash
# Show recent policy denial events (admission webhook blocks)
kubectl get events -n {{NAMESPACE}} --field-selector reason=PolicyViolation

# If Azure Policy add-on is installed, check constraint violations
kubectl get constrainttemplate
kubectl get k8sazurev2podenforcepss -A          # PSS constraints
kubectl get k8sazurev2blocknodesyscalls -A       # sysctl constraints
kubectl get constraintviolation -A 2>/dev/null   # if Gatekeeper CRD exists

# Check Azure Policy compliance in the portal (CLI alternative)
az policy state list \
  --resource-group {{RESOURCE_GROUP}} \
  --resource-type "Microsoft.ContainerService/managedClusters" \
  --resource {{AKS_CLUSTER_NAME}} \
  --filter "complianceState eq 'NonCompliant'" \
  --query "[].{policy:policyDefinitionName, resource:resourceId, details:additionalInfo}" \
  -o table

# Dry-run a manifest against admission to see what blocks
kubectl apply --dry-run=server -f {{MANIFEST_PATH}}

# Check what policies are assigned to the cluster's resource group
az policy assignment list --scope /subscriptions/{{SUBSCRIPTION_ID}}/resourceGroups/{{RESOURCE_GROUP}} -o table
```

---

## 2. Current pod security posture

### kagent namespace

| Pod | podSecurityContext | Container securityContext | Violations |
|---|---|---|---|
| `kagent-controller` | `{}` | `null` | runAsNonRoot, seccompProfile, capabilities.drop, allowPrivilegeEscalation |
| agent pods (all) | `{}` | `null` | same |
| `kagent-tools` | `{}` | `null` | same |
| `kagent-ui` | `{}` | `null` | same |

### agentgateway-system namespace

| Pod | podSecurityContext | Container securityContext | Violations |
|---|---|---|---|
| `agent-gw` (data plane) | `sysctls: [{net.ipv4.ip_unprivileged_port_start: "0"}]` | `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `readOnlyRootFilesystem: true`, `runAsNonRoot: true`, `runAsUser: 10101` | **unsafe sysctl** (cannot fix), missing `seccompProfile` (fixable) |
| `agentgateway-controller` | `{}` | `null` | runAsNonRoot, seccompProfile, capabilities.drop, allowPrivilegeEscalation |

---

## 3. Fixable violations — Helm values

These can be resolved without an exception by overriding Helm chart defaults.

### 3a. kagent — add security context

Create or extend your `kagent-values.yaml`:

```yaml
# kagent-values.yaml (security additions)
podSecurityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
```

Apply:
```bash
helm upgrade kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --namespace kagent \
  -f kagent-values.yaml \
  --reuse-values
```

Verify:
```bash
kubectl get pod -n kagent -l app.kubernetes.io/name=kagent \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.securityContext}{"\n"}{end}'
```

### 3b. agentgateway-controller — add security context

The agentgateway Helm chart exposes `controller.podSecurityContext` and `controller.securityContext`:

```yaml
# agentgateway-values.yaml
controller:
  podSecurityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  securityContext:
    allowPrivilegeEscalation: false
    capabilities:
      drop:
        - ALL
    readOnlyRootFilesystem: true
    runAsNonRoot: true
```

Apply:
```bash
helm upgrade agentgateway oci://cr.agentgateway.dev/charts/agentgateway \
  --version v1.3.1 \
  --namespace agentgateway-system \
  -f agentgateway-values.yaml \
  --reuse-values
```

### 3c. agentgateway data plane — add seccompProfile

The data plane pod already has most controls. Only `seccompProfile` is missing:

```yaml
# agentgateway-values.yaml (add to above)
podSecurityContext:
  seccompProfile:
    type: RuntimeDefault
  sysctls:
    - name: net.ipv4.ip_unprivileged_port_start
      value: "0"   # retain — required for port binding; exception needed (see §4)
```

---

## 4. Non-fixable violation — Azure Policy exception required

### Violation

**Component:** agentgateway data plane (`agent-gw` pod, `agentgateway-system` namespace)

**Sysctl:** `net.ipv4.ip_unprivileged_port_start=0`

**Why it exists:** agentgateway runs as a non-root user (`runAsUser: 10101`) but must bind to port 80 for LLM/MCP traffic. Linux normally requires root (UID 0) to bind ports < 1024. Setting this sysctl to `0` allows any user to bind privileged ports — it is the standard pattern for non-root gateway processes.

**Why it cannot be fixed:** The sysctl is required for the current architecture. Alternatives would require either running as root (worse) or reconfiguring the entire ingress path to use port 8080+ and adjusting all downstream clients and Istio routing (high effort, not upstream-supported).

**Azure Policy rule that blocks it:** `[Preview]: Kubernetes cluster containers should not use forbidden sysctls`
(Azure built-in policy definition — enforcement mode `Deny` blocks the pod from scheduling)

---

### Exception request template

Copy and adapt for the target environment's exception process:

---

**Azure Policy Exception Request**

**Date:** YYYY-MM-DD
**Requestor:** [your name / team]
**AKS Cluster:** [cluster name]
**Resource Group:** [rg name]
**Subscription:** [sub name / ID]

**Policy:** `[Preview]: Kubernetes cluster containers should not use forbidden sysctls`
(or the equivalent environment-specific policy ID)

**Scope of exception:**
- Namespace: `agentgateway-system`
- Workload: `agentgateway` Helm release, pod label `app=agentgateway`
- Sysctl: `net.ipv4.ip_unprivileged_port_start=0`

**Business justification:**
agentgateway is the AI platform's LLM/MCP proxy. It routes all agent-to-model and agent-to-tool traffic through a single, policy-enforced gateway. The component runs as non-root (`runAsUser: 10101`) with `capabilities.drop: [ALL]` and `allowPrivilegeEscalation: false`. The sysctl `net.ipv4.ip_unprivileged_port_start=0` is required solely to allow the non-root process to bind port 80 for HTTP traffic. Without it, the gateway cannot start.

This is a pod-level sysctl scoped to the gateway pod only. It does not affect the host kernel, other namespaces, or other pods.

**Compensating controls in place:**
- Container runs as non-root UID 10101
- `allowPrivilegeEscalation: false`
- `capabilities.drop: [ALL]`
- `readOnlyRootFilesystem: true`
- NetworkPolicy restricts ingress/egress to approved sources
- Istio AuthorizationPolicy restricts source principals to kagent service accounts
- Pod is in a dedicated namespace (`agentgateway-system`) with no tenant workloads
- All LLM/MCP traffic is logged and rate-limited via agentgateway policies

**Risk assessment:** Low. The sysctl enables non-root port binding within the pod network namespace only. All other security controls are in place and exceed baseline requirements.

**Exception duration:** Permanent (or until agentgateway upstream removes the sysctl requirement)

**Owner:** [name, team]
**Review date:** [annual review date]

---

## 5. Commands to copy manifests for your target cluster

### Pull running pod specs as YAML (to inspect exactly what's live)

```bash
# kagent-controller full spec
kubectl get deployment kagent-controller -n kagent -o yaml > kagent-controller-live.yaml

# agentgateway data plane
kubectl get deployment agent-gw -n agentgateway-system -o yaml > agent-gw-live.yaml

# agentgateway controller
kubectl get deployment agentgateway -n agentgateway-system -o yaml > agentgateway-controller-live.yaml
```

### Get the Helm values currently deployed

```bash
helm get values kagent -n kagent
helm get values agentgateway -n agentgateway-system
```

### Check what images are in use (for private registry mirroring)

```bash
kubectl get pods -n kagent -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | sort -u
kubectl get pods -n agentgateway-system -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | sort -u
```

### Mirror images to a private registry

```bash
# agentgateway data plane
AGENTGW_IMG=cr.agentgateway.dev/agentgateway:v1.3.1
docker pull $AGENTGW_IMG
docker tag $AGENTGW_IMG {{INTERNAL_REGISTRY}}/$AGENTGW_IMG
docker push {{INTERNAL_REGISTRY}}/$AGENTGW_IMG

# agentgateway controller
AGENTGW_CONTROLLER_IMG=cr.agentgateway.dev/controller:v1.3.1
docker pull $AGENTGW_CONTROLLER_IMG
docker tag $AGENTGW_CONTROLLER_IMG {{INTERNAL_REGISTRY}}/$AGENTGW_CONTROLLER_IMG
docker push {{INTERNAL_REGISTRY}}/$AGENTGW_CONTROLLER_IMG

# kagent controller
KAGENT_IMG=ghcr.io/kagent-dev/kagent/controller:0.9.10
docker pull $KAGENT_IMG
docker tag $KAGENT_IMG {{INTERNAL_REGISTRY}}/$KAGENT_IMG
docker push {{INTERNAL_REGISTRY}}/$KAGENT_IMG
```

Helm override to use private registry:
```yaml
# kagent: override image registry
controller:
  image:
    registry: {{INTERNAL_REGISTRY}}

# agentgateway: override image
image:
  registry: {{INTERNAL_REGISTRY}}
  repository: agentgateway
  tag: "v1.3.1"
```

---

## 6. Summary

| Component | Namespace | Fixable? | Action |
|---|---|---|---|
| kagent-controller | `kagent` | Yes | Helm values — add full securityContext |
| kagent agent pods | `kagent` | Yes | Helm values — same |
| agentgateway-controller | `agentgateway-system` | Yes | Helm values — add full securityContext |
| agentgateway data plane | `agentgateway-system` | Partial | Helm values for seccompProfile; Azure Policy exception for sysctl |

**One exception needed.** Everything else can be fixed before deploying to the target cluster.
