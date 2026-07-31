# AKS Fleet Policy — Node Patching Currency and Seccomp Posture

Azure Policy artifacts answering two fleet-wide questions:

1. **Are AKS node images being patched and kept up to date?**
2. **Is seccomp enabled?**

Everything here defaults to **Audit**. Nothing blocks a deployment until you deliberately change an effect parameter.

---

## 1. What is in this directory

| File | What it is |
|---|---|
| `policy-node-image-freshness.json` | Custom definition. Flags clusters with any Linux node pool whose node image build month is older than an approved minimum. |
| `policy-node-seccomp-default.json` | Custom definition. Flags Linux node pools that do not set `kubeletConfig.seccompDefault`. |
| `policy-watched-identity-attached.json` | Custom definition. Flags clusters and scale sets with a named managed identity attached. Assigned separately — see section 10. |
| `initiative-aks-patching-and-seccomp.json` | Initiative bundling the two patching/seccomp definitions plus three Azure built-ins. The identity policy is deliberately not in it. |
| `deploy.sh` | Creates the definitions and initiative, optionally assigns them. |

---

## 2. Coverage map — custom vs built-in

Two of the four controls already exist as Azure built-ins. Do not reinvent them.

| Control | Source | Definition ID |
|---|---|---|
| Node OS auto-upgrade is enabled (`NodeImage` / `SecurityPatch`) | **Built-in** | `04408ca5-aa10-42ce-8536-98955cdddd4c` |
| Cluster auto-upgrade channel is set | **Built-in** | `5c345cdf-2049-47e0-b8fe-b0e96bc2df35` |
| Pods use an allowed seccomp profile (Gatekeeper) | **Built-in** | `975ce327-682c-4f2e-aa46-b9598289b86c` |
| Node image build date is not stale | **Custom** — no built-in exists | `aks-node-image-freshness-audit` |
| Kubelet applies a default seccomp profile to all pods | **Custom** | `aks-node-seccomp-default-audit` |

The built-ins tell you a cluster is *configured* to patch itself. The custom freshness policy tells you whether it *actually did*. You want both: a cluster can have `nodeOSUpgradeChannel: NodeImage` set and still be months behind because its maintenance window never fires, or the node pool is stopped, or upgrades keep failing on PDBs.

There is also a DINE built-in that *sets* node OS auto-upgrade for you rather than auditing it: `40f1aee2-4db4-4b74-acb1-c6972e24cca8`. Not included in the initiative — that is a remediation decision, not a detection one.

---

## 3. How the node image freshness check works

AKS exposes the node image on each pool as a read-only ARM property. Format:

```
AKSUbuntu-2204gen2containerd-202506.10.0
AKSCBLMariner-V2gen2-202506.10.0
```

The build month is the leading `YYYYMM` of the final segment. The policy extracts it with:

```
first(split(last(split(current('...nodeImageVersion'), '-')), '.'))
```

and compares it ordinally against the `minimumNodeImageDate` parameter (default `202506`). Any Linux node pool sorting before that value makes the whole cluster non-compliant.

### Deliberate limitations

- **Audit only.** `nodeImageVersion` is read-only, so `Deny` would be meaningless. Enforcement lives in the auto-upgrade built-ins.
- **Windows node pools are excluded.** Windows uses `AKSWindows-2022-containerd-20348.2582.240610` — a different shape where the leading segment is a build number, not a date. Parsing it with the same expression would produce garbage comparisons. If you run Windows pools, they are silently not covered by this control; track them separately.
- **The threshold is a parameter, not a computed "N days old".** Azure Policy has no `utcNow()` in policy rules, so the minimum date cannot be derived at evaluation time. You bump `minimumNodeImageDate` on your patch cadence. Section 8 has a script for that.
- **Escape hatch.** Tag a cluster `nodeImageFreshnessExempt=true` to skip it. Change `excludedClusterTagName` to an unused name to disable the hatch entirely.
- **String comparison, not date comparison.** `less` on two `YYYYMM` strings is an ordinal compare, which is equivalent to a date compare only while both sides are six digits. Retired legacy images use a four-digit year (`AKSUbuntu-1804gen2containerd-2021.11.06` parses to `2021`), which still sorts correctly against any `202xxx` threshold you would realistically set. Verify the parse on one real cluster after assigning — section 8's Resource Graph query produces the same `buildMonth` value the policy computes, so the two should agree row for row.

---

## 4. How the seccomp checks work

Two layers, because "is seccomp enabled" has two different answers.

### 4a. Workload level — built-in `975ce327`, Gatekeeper mode

Evaluates every pod's `securityContext.seccompProfile` against an allowlist. Default allowlist here is `runtime/default` and `docker/default`. `unconfined` is deliberately excluded.

**Requires the Azure Policy add-on on each cluster.** Without it, this definition reports nothing at all — not "compliant", just no data. Check before trusting a green dashboard:

```bash
az aks show -g <rg> -n <cluster> --query "addonProfiles.azurepolicy.enabled"
```

Note from `docs/imds/imds-aks-exposure.md`: the Azure Policy add-on is one of the add-ons that blocks `--enable-imds-restriction`. That trade-off is already documented there.

### 4b. Node level — custom `aks-node-seccomp-default-audit`

Checks `kubeletConfig.seccompDefault` on each Linux node pool. Setting it to `RuntimeDefault` makes the runtime apply a seccomp profile to every pod that does **not** declare one, which closes the gap 4a can only report on.

The `kubeletConfig.seccompDefault` alias was an open question in v1 of this directory. It is now confirmed to exist — the definition was accepted by ARM, and section 5b shows ARM rejects unknown aliases outright. What is *not* yet confirmed is the rule's matching behaviour at evaluation time; see section 5c. If the alias is ever absent in a different tenant, set `nodeSeccompDefaultEffect` to `Disabled` and rely on 4a.

---

## 5. Validation evidence

Dry run performed 2026-07-31 against subscription `133d5755` (Pay-As-You-Go). All artifacts created under a `zz-` prefix and deleted afterwards; residue check returned 0 definitions and 0 assignments.

### 5a. What was proven

| Check | Method | Result |
|---|---|---|
| All three definitions are valid ARM policy | `az policy definition create` | **Accepted** |
| Every alias used actually exists | negative control below | **Proven** |
| `kubeletConfig.seccompDefault` alias exists | accepted at create | **Resolved** — was an open question in v1 |
| `identityProfile` alias exists | accepted at create | **Confirmed** |
| Identity hunt by GUID on kubelet identity | `checkPolicyRestrictions`, synthetic cluster | **Fires correctly** |
| Identity hunt by GUID on cluster identity | same | **Fires correctly** |
| No false positive on a clean cluster | same | **Confirmed compliant** |

The identity fixtures were the decisive ones. GUID placed **only** in `properties.identityProfile.kubeletidentity.objectId` → flagged. GUID placed **only** in `identity.userAssignedIdentities` values → flagged. GUID absent → clean. This proves the `string(field(...))` + `contains` technique works at evaluation time, which was the main unknown in the design.

### 5b. Negative control — is ARM validation actually strict?

An "accepted" result is worthless if ARM accepts anything. Two deliberately broken policies were submitted:

| Broken input | Outcome |
|---|---|
| Non-existent alias `…/thisAliasDoesNotExistAtAll` | **Rejected** — `'field' property … doesn't exist as an alias` |
| `resourceGroup()` in a policy rule (deployment-only function) | **Accepted** |

So alias validation is strict and the alias results above are trustworthy. **Function validation is not.** A deployment-only function in a policy rule is accepted at create time and fails silently at evaluation. An earlier draft of the identity policy used `resourceGroup().name` to filter to `MC_*` node resource groups; it was removed on review, and this control confirms ARM would never have caught it.

### 5c. What could NOT be proven, and why

**The node image freshness and seccomp rules are unvalidated at runtime.** Both were accepted by ARM and both use only verified aliases, but neither produced a verdict in simulation.

Root cause, established by probe ladder rather than assumed: a policy containing nothing but `count` over `agentPoolProfiles[*]` `greater than 0` — the simplest possible array rule — did **not** fire against a payload that plainly contains one agent pool. `checkPolicyRestrictions` does not evaluate array-alias count expressions for synthetic resource payloads. This is a limitation of the simulator, not evidence of a defect in the rules.

Consequence: the date-extraction expression in section 3 and the `seccompDefault` check in section 4b are **syntactically validated and alias-validated, but their matching behaviour has not been observed**. To close this, assign both at Audit against a scope containing at least one real AKS cluster and run:

```bash
az policy state trigger-scan --no-wait
```

then confirm the reported non-compliant pools match what the section 8 Resource Graph query returns for the same clusters. Treat that as a required step before relying on either policy for a control narrative.

One caveat worth flagging on my own method: two intermediate probe runs produced false "nothing fired" results because a bash heredoc consumed the `[*]` in `$ALIAS[*]` as an array subscript, so the probes were never created. Errors had been suppressed. If you re-run this validation, check exit codes explicitly rather than trusting silent success.

---

## 6. Verifying aliases before you assign

Confirms every alias used here resolves in your tenant. Run before deploying.

```bash
az provider show \
  --namespace Microsoft.ContainerService \
  --expand "resourceTypes/aliases" \
  --query "resourceTypes[?resourceType=='managedClusters'].aliases[].name" -o tsv \
  | grep -E "nodeImageVersion|autoUpgradeProfile|seccompDefault|osType"
```

Expected:

| Alias | Status |
|---|---|
| `Microsoft.ContainerService/managedClusters/agentPoolProfiles[*].nodeImageVersion` | confirmed to exist |
| `Microsoft.ContainerService/managedClusters/agentPoolProfiles[*].osType` | confirmed to exist |
| `Microsoft.ContainerService/managedClusters/autoUpgradeProfile.nodeOSUpgradeChannel` | confirmed — used by built-in `04408ca5` |
| `Microsoft.ContainerService/managedClusters/agentPoolProfiles[*].kubeletConfig.seccompDefault` | **verify in your tenant** |

---

## 7. Deploying

```bash
# Management group scope — the right choice for a fleet
./deploy.sh --mg <management-group-id>

# Review the definitions in the portal, then assign
./deploy.sh --mg <management-group-id> --assign --min-node-image 202506

# Or subscription scope for a trial run
./deploy.sh --sub <subscription-id> --assign
```

Requires `az` and `jq`. `--assign` is the only step that produces compliance data.

Force an evaluation instead of waiting up to 30 minutes:

```bash
az policy state trigger-scan --no-wait
```

---

## 8. Reading the results

### Per-subscription compliance list

```bash
az policy state list \
  --filter "complianceState eq 'NonCompliant'" \
  --query "[?contains(resourceId,'managedClusters')].{cluster:resourceId, policy:policyDefinitionName}" \
  -o table
```

### Fleet-wide node image ages — Resource Graph, no policy needed

This is the fastest way to see the real spread across every subscription you can read. Useful as a cross-check that the policy threshold is set sensibly.

```bash
az graph query -q "
resources
| where type =~ 'microsoft.containerservice/managedclusters'
| mv-expand pool = properties.agentPoolProfiles
| extend poolName    = tostring(pool.name)
| extend osType      = tostring(pool.osType)
| extend nodeImage   = tostring(pool.nodeImageVersion)
| where osType != 'Windows' and isnotempty(nodeImage)
| extend buildMonth  = tostring(split(split(nodeImage, '-')[-1], '.')[0])
| extend upgradeChan = tostring(properties.autoUpgradeProfile.nodeOSUpgradeChannel)
| project subscriptionId, resourceGroup, cluster = name, poolName, buildMonth, nodeImage, upgradeChan
| order by buildMonth asc
" --first 1000 -o table
```

Anything at the top of that list is your patching backlog.

### Bumping the threshold each month

```bash
NEW_MIN=$(date -u -v-1m +%Y%m 2>/dev/null || date -u -d '1 month ago' +%Y%m)

az policy assignment update \
  --name aks-fleet-patching-seccomp \
  --scope /providers/Microsoft.Management/managementGroups/<mg-id> \
  --params "{\"minimumNodeImageDate\":{\"value\":\"${NEW_MIN}\"}}"
```

Run it from a scheduled pipeline. A static threshold decays into a policy that always passes.

---

## 9. Suggested rollout

1. Run the section 6 alias check.
2. Run the section 8 Resource Graph query with no policy deployed. This tells you today's real spread and what `minimumNodeImageDate` should start at — set it where roughly 80% of the fleet already passes, so the initial signal is actionable rather than 300 red rows.
3. `./deploy.sh --mg <id>` — definitions only. Review in the portal.
4. `./deploy.sh --mg <id> --assign` — all Audit.
5. Wait one full scan cycle. Triage non-compliant clusters.
6. Enable the DINE built-in `40f1aee2-4db4-4b74-acb1-c6972e24cca8` to auto-set `nodeOSUpgradeChannel` on the stragglers, if you want remediation rather than reporting.
7. Only after the fleet is green: consider flipping `seccompWorkloadEffect` to `Deny`. Check `docs/security/azure-policy-exceptions.md` first — the agentgateway data plane already needs one Azure Policy exception, and moving seccomp to Deny will surface more.
8. Tighten `minimumNodeImageDate` monthly on a schedule.

---

## 10. Finding a specific managed identity across the fleet

Separate concern from patching, so it is a standalone definition rather than part of the initiative. It answers: *"is identity X attached anywhere?"*

### What makes it work

Azure Policy exposes `identity.userAssignedIdentities` as a **dictionary keyed by identity resource ID**, and the `containsKey` operator reads it:

```json
{ "field": "identity.userAssignedIdentities",
  "containsKey": "/subscriptions/…/userAssignedIdentities/my-uami" }
```

This is the same mechanism the Azure built-in `516187d4-ef64-4a1b-ad6b-a7348502976c` uses, so the pattern is proven rather than inferred.

### Why it targets scale sets, not just clusters

Per `docs/imds/imds-aks-exposure.md`, the identities that matter for blast radius are attached to the **node VMSS**, not to the cluster resource: kubelet identity, `cost-analysis-identity`, AMA, AGIC, Key Vault CSI. Every one of those is reachable from any pod via IMDS. A policy that only looked at `Microsoft.ContainerService/managedClusters` would report clean while the real exposure sat one resource away.

VMSS evaluation is **not** filtered to `MC_*` resource groups. `--node-resource-group` lets an AKS node RG be named anything, so a prefix filter would silently miss clusters — a false negative on a security control is worse than a few extra rows.

### Assigning it

```bash
IDENTITY_ID=$(az identity show -g <rg> -n <identity-name> --query id -o tsv)

az policy assignment create \
  --name aks-watched-identity \
  --display-name "Watched managed identity attached to AKS" \
  --policy "${DEFINITION_SCOPE}/providers/Microsoft.Authorization/policyDefinitions/aks-watched-identity-attached-audit" \
  --scope /providers/Microsoft.Management/managementGroups/<mg-id> \
  --params "{\"watchedIdentityResourceIds\":{\"value\":[\"${IDENTITY_ID}\"]}}"
```

Matching is on the exact dictionary key. Paste the ID from `az identity show --query id -o tsv` rather than hand-assembling it.

### What this approach cannot do

Be clear on the boundary before relying on it:

- **You must already know which identity you are hunting.** `containsKey` tests for a known key. Azure Policy cannot enumerate the dictionary's keys, so "flag any identity outside an approved list" is **not** expressible. Discovery is Resource Graph's job — see below.
- **The kubelet identity is invisible at the cluster resource.** It lives at `properties.identityProfile.kubeletidentity`, and the AKS provider publishes no leaf aliases under `identityProfile` — only the container object. Confirmed by scanning all 650 `Microsoft.ContainerService/managedClusters` aliases. The VMSS path is what covers kubelet identity.
- **Audit only.** AKS itself writes the node VMSS. A Deny effect there would break cluster operations, node pool scaling, and upgrades.
- **Attachment is not permission.** The policy tells you an identity is attached, not what it can do. Blast radius still needs the `az role assignment list --assignee <principalId> --all` pass from `docs/imds/imds-aks-exposure.md` section 3.2.

### Discovery — enumerate every identity on every cluster and node pool

Resource Graph *can* read dictionary keys, so this is the tool for "what is attached that I did not expect":

```bash
az graph query -q "
resources
| where type =~ 'microsoft.containerservice/managedclusters'
     or type =~ 'microsoft.compute/virtualmachinescalesets'
| where isnotempty(identity.userAssignedIdentities)
| mv-expand identityId = bag_keys(identity.userAssignedIdentities)
| extend identityName = tostring(split(tostring(identityId), '/')[-1])
| project subscriptionId, resourceGroup, resource = name, type, identityName, identityId
| order by identityName asc
" --first 1000 -o table
```

Kubelet identity specifically, which the above misses because it is not in the cluster's own identity block:

```bash
az graph query -q "
resources
| where type =~ 'microsoft.containerservice/managedclusters'
| extend kubelet = properties.identityProfile.kubeletidentity
| project subscriptionId, resourceGroup, cluster = name,
          kubeletClientId = tostring(kubelet.clientId),
          kubeletObjectId = tostring(kubelet.objectId),
          kubeletResourceId = tostring(kubelet.resourceId)
" --first 1000 -o table
```

Run the discovery queries first, decide which identities should not be spreading, then assign the policy to hold that line going forward.

### Related built-in worth knowing

For Workload Identity the link between identity and cluster is a federated credential, and that **is** fully policy-visible — issuer URL, cluster, namespace, service account. Built-in `ae62c456-33de-4dc8-b100-7ce9028a7d99` ("Managed Identity Federated Credentials from Azure Kubernetes should be from trusted sources") constrains which clusters an identity will federate to. That is the forward-looking control; the VMSS policy above covers the legacy IMDS-shaped exposure you are trying to retire.

---

## 11. Sources

- [Azure Policy built-in definitions for AKS](https://learn.microsoft.com/en-us/azure/aks/policy-reference)
- [`AllowedSeccompProfile.json` built-in definition](https://github.com/Azure/azure-policy/blob/master/built-in-policies/policyDefinitions/Kubernetes/AllowedSeccompProfile.json)
- [Kubernetes cluster containers should only use allowed seccomp profiles — `975ce327`](https://www.azadvertizer.net/azpolicyadvertizer/975ce327-682c-4f2e-aa46-b9598289b86c.html)
- [Troubleshoot seccomp profiles in AKS](https://learn.microsoft.com/en-us/troubleshoot/azure/azure-kubernetes/security/troubleshoot-seccomp-profiles)
- [`Microsoft.ContainerService/managedClusters/agentPools` ARM reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.containerservice/managedclusters/agentpools)
- [AKS auto-upgrade node OS images](https://learn.microsoft.com/en-us/azure/aks/auto-upgrade-node-os-image)
