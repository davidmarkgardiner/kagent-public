# Check Kyverno exposure and plan remediation

Use this runbook for GHSA-4c7q-j33x-866w, CVE-2026-122310, and its linked upstream advisory GHSA-3xfv-vq8x-qhg4. Sources were checked on 5 November 2026.

If the running version is `v1.19.1`, treat it as affected. The reported `1.9.19.1` is ambiguous. Confirm the exact image tag and digest below before choosing an upgrade path.

The upstream advisory lists versions **at or below 1.19.1 as affected** and **1.19.2 as patched**. It describes an authenticated user escaping a namespaced Policy's API-call boundary using the controller's identity. Default controller permissions enable a path to cluster-admin access. The linked CVE entry describes a narrower version range. Use the broader upstream range for triage. [Upstream advisory](https://github.com/kyverno/kyverno/security/advisories/GHSA-3xfv-vq8x-qhg4).

## 1. Run the read-only checks

Run this from an approved workstation with `bash`, `kubectl`, and `jq`. Edit the configuration at the top, then paste the **whole block** into your terminal. It runs in its own Bash process and does not change your current context.

- Set `WORK_CONTEXT` to the cluster context you intend to inspect. Use `kubectl config get-contexts -o name` to find local context names.
- Set `KYVERNO_NAMESPACE` to the installation namespace. The deployment discovery also looks across namespaces for names or images containing `kyverno`. Repeat for additional installations or renamed components.
- Optionally set `TENANT_CONTEXT` to a context authenticated as an ordinary application identity, and set `TENANT_NAMESPACE`. Leave both empty to skip this check. Do not use an administrator context as evidence of tenant permissions.
- Set `RUN_CONTROLLER_AUTH_CHECKS` to `yes` only if your identity can impersonate the controller service accounts. This performs authorization reviews, not resource creation.

The block makes GET requests and authorization reviews. It does not apply policies, execute the exploit, read Secret contents, restart components, or upgrade the cluster. It saves filtered RBAC evidence in a new local directory. Keep the output private and redact internal names and API paths before sharing it.

```bash
bash <<'BASH'
set -u -o pipefail

WORK_CONTEXT='{{WORK_CONTEXT}}'
KYVERNO_NAMESPACE='kyverno'
TENANT_CONTEXT=''
TENANT_NAMESPACE=''
RUN_CONTROLLER_AUTH_CHECKS='no'
REQUEST_TIMEOUT='30s'

for dependency in kubectl jq; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    printf 'STOP: install %s through your approved tooling process.\n' "$dependency"
    exit 1
  fi
done
if [[ -z "$WORK_CONTEXT" || "$WORK_CONTEXT" == *'{{'* || -z "$KYVERNO_NAMESPACE" ]]; then
  printf 'STOP: set WORK_CONTEXT and KYVERNO_NAMESPACE above.\n'
  exit 1
fi
if [[ "$RUN_CONTROLLER_AUTH_CHECKS" != yes && "$RUN_CONTROLLER_AUTH_CHECKS" != no ]]; then
  printf 'STOP: RUN_CONTROLLER_AUTH_CHECKS must be yes or no.\n'
  exit 1
fi
if [[ -n "$TENANT_CONTEXT" && -z "$TENANT_NAMESPACE" ]] ||
   [[ -z "$TENANT_CONTEXT" && -n "$TENANT_NAMESPACE" ]]; then
  printf 'STOP: set both tenant variables, or leave both empty.\n'
  exit 1
fi
if ! kubectl config get-contexts "$WORK_CONTEXT" -o name | grep -Fx -- "$WORK_CONTEXT" >/dev/null; then
  printf 'STOP: WORK_CONTEXT is not available in your kubeconfig.\n'
  exit 1
fi
if [[ -n "$TENANT_CONTEXT" ]]; then
  if ! kubectl config get-contexts "$TENANT_CONTEXT" -o name | grep -Fx -- "$TENANT_CONTEXT" >/dev/null; then
    printf 'STOP: TENANT_CONTEXT is not available in your kubeconfig.\n'
    exit 1
  fi
  if [[ "$TENANT_CONTEXT" == "$WORK_CONTEXT" ]]; then
    printf 'STOP: use a separate ordinary application identity for TENANT_CONTEXT.\n'
    exit 1
  fi
  work_server=$(kubectl --context "$WORK_CONTEXT" config view --minify -o jsonpath='{.clusters[0].cluster.server}')
  tenant_server=$(kubectl --context "$TENANT_CONTEXT" config view --minify -o jsonpath='{.clusters[0].cluster.server}')
  if [[ -z "$work_server" || "$work_server" != "$tenant_server" ]]; then
    printf 'STOP: contexts must target the same API server for a combined assessment.\n'
    exit 1
  fi
fi

umask 077
evidence_dir=$(mktemp -d ./kyverno-exposure.XXXXXX) || exit 1
k=(kubectl --context "$WORK_CONTEXT" --request-timeout="$REQUEST_TIMEOUT")
printf 'Context: %s\nKyverno namespace: %s\nLocal evidence: %s\n' "$WORK_CONTEXT" "$KYVERNO_NAMESPACE" "$evidence_dir"
date -u '+Checked at: %Y-%m-%dT%H:%M:%SZ'

printf '\nCHECK 1: deployment discovery and desired images\n'
if deployments=$("${k[@]}" get deployments.apps -A -o json); then
  printf '%s\n' "$deployments" | jq -r --arg ns "$KYVERNO_NAMESPACE" '
    .items[]
    | select(.metadata.namespace == $ns or
        (.metadata.name | test("kyverno"; "i")) or
        any(.spec.template.spec.containers[]; .image | test("kyverno"; "i")))
    | [.metadata.namespace, .metadata.name,
        (.spec.template.spec.serviceAccountName // "default"),
        ([.spec.template.spec.containers[].image] | join(",")),
        ((.status.availableReplicas // 0) | tostring),
        ((.spec.replicas // 1) | tostring)] | @tsv'
else
  printf 'GAP: deployment discovery failed. Check access and namespace.\n'
fi

printf '\nCHECK 2: running pods, images, digests, and readiness\n'
pods=''
if pods=$("${k[@]}" get pods -n "$KYVERNO_NAMESPACE" -o json); then
  printf '%s\n' "$pods" | jq -r '
    .items[] as $pod
    | $pod.spec.containers[] as $container
    | ([$pod.status.containerStatuses[]? | select(.name == $container.name)][0] // {}) as $status
    | [$pod.metadata.name, ($pod.spec.serviceAccountName // "default"),
        $container.name, $container.image, ($status.imageID // "UNKNOWN"),
        (($status.ready // false) | tostring)] | @tsv'
  if [[ $(printf '%s\n' "$pods" | jq '.items | length') == 0 ]]; then
    printf 'GAP: no pods found. Verify the installation namespace.\n'
  fi
else
  printf 'GAP: pod inventory failed. No running-version conclusion is possible.\n'
fi

printf '\nCHECK 3: candidate roles allowing Policy creation or modification\n'
if roles=$("${k[@]}" get roles.rbac.authorization.k8s.io,clusterroles.rbac.authorization.k8s.io -A -o json); then
  if printf '%s\n' "$roles" | jq '[.items[]
    | .rules = [.rules[]?
        | select(any(.apiGroups[]?; . == "kyverno.io" or . == "*"))
        | select(any(.resources[]?; . == "policies" or . == "*"))
        | select(any(.verbs[]?; . == "create" or . == "update" or . == "patch" or . == "*"))]
    | select(.rules | length > 0)
    | {kind, namespace: (.metadata.namespace // ""), name: .metadata.name, rules}
  ]' > "$evidence_dir/policy-writer-roles.json"; then
    cat "$evidence_dir/policy-writer-roles.json"
    printf '\nBindings to those candidate roles and their subjects\n'
    if bindings=$("${k[@]}" get rolebindings.rbac.authorization.k8s.io,clusterrolebindings.rbac.authorization.k8s.io -A -o json); then
      printf '%s\n' "$bindings" | jq --slurpfile candidates "$evidence_dir/policy-writer-roles.json" '
        [.items[] as $binding
        | select(any($candidates[0][];
            .name == $binding.roleRef.name and .kind == $binding.roleRef.kind and
            (.kind == "ClusterRole" or .namespace == ($binding.metadata.namespace // ""))))
        | $binding
        | {kind, namespace: (.metadata.namespace // ""), name: .metadata.name,
            roleRef, subjects: (.subjects // [])}]' |
        tee "$evidence_dir/policy-writer-bindings.json"
    else
      printf 'GAP: bindings could not be listed. Candidate roles alone do not prove a grant.\n'
    fi
  else
    printf 'GAP: role analysis failed.\n'
  fi
else
  printf 'GAP: RBAC inventory failed. Tenant permissions remain unknown.\n'
fi

printf '\nCHECK 4: effective permissions for the optional application identity\n'
if [[ -n "$TENANT_CONTEXT" ]]; then
  printf 'Identity context: %s; namespace: %s\n' "$TENANT_CONTEXT" "$TENANT_NAMESPACE"
  for verb in create update patch; do
    printf 'Can %s policies.kyverno.io?\n' "$verb"
    kubectl --context "$TENANT_CONTEXT" --request-timeout="$REQUEST_TIMEOUT" auth can-i \
      "$verb" policies.kyverno.io -n "$TENANT_NAMESPACE"
  done
else
  printf 'GAP: skipped. Set TENANT_CONTEXT and TENANT_NAMESPACE to test a real application identity.\n'
fi

printf '\nCHECK 5: controller ability to create cluster-wide admission webhooks\n'
if [[ "$RUN_CONTROLLER_AUTH_CHECKS" == yes && -n "$pods" ]]; then
  service_accounts=$(printf '%s\n' "$pods" | jq -r '[.items[].spec.serviceAccountName // "default"] | unique[]')
  for service_account in $service_accounts; do
    printf 'ServiceAccount: %s/%s\n' "$KYVERNO_NAMESPACE" "$service_account"
    for resource in mutatingwebhookconfigurations.admissionregistration.k8s.io validatingwebhookconfigurations.admissionregistration.k8s.io; do
      printf 'Can create %s?\n' "$resource"
      "${k[@]}" auth can-i create "$resource" \
        --as="system:serviceaccount:${KYVERNO_NAMESPACE}:${service_account}" \
        --as-group=system:serviceaccounts \
        --as-group="system:serviceaccounts:${KYVERNO_NAMESPACE}" \
        --as-group=system:authenticated
    done
  done
else
  printf 'GAP: skipped. Enable impersonation checks above, or have an authorized administrator run them.\n'
fi

printf '\nCHECK 6: existing namespaced Policies with API-call paths needing review\n'
if policies=$("${k[@]}" get policies.kyverno.io -A -o json); then
  printf '%s\n' "$policies" | jq '[.items[] as $policy
    | $policy.spec.rules[]? as $rule
    | ($rule | .. | objects | .apiCall? // empty) as $call
    | select($call.urlPath? | type == "string")
    | select($call.urlPath | test("[?#]|\\.\\.|%2e|%2f|%23|%3f"; "i"))
    | {namespace: $policy.metadata.namespace, policy: $policy.metadata.name,
        rule: $rule.name, method: ($call.method // "GET"), urlPath: $call.urlPath}]'
else
  printf 'GAP: Policies could not be listed. This check is inconclusive.\n'
fi

printf '\nCHECK 7: Flux HelmRelease ownership, if installed and readable\n'
if releases=$("${k[@]}" get helmreleases.helm.toolkit.fluxcd.io -A -o json); then
  printf '%s\n' "$releases" | jq -r --arg ns "$KYVERNO_NAMESPACE" '
    .items[]
    | select((.metadata.name | test("kyverno"; "i")) or
        ((.spec.chart.spec.chart // "") | test("kyverno"; "i")) or
        ((.spec.targetNamespace // .metadata.namespace) == $ns))
    | [.metadata.namespace, .metadata.name, (.spec.chart.spec.chart // "chartRef"),
        (.spec.chart.spec.version // "UNKNOWN"),
        ((.spec.suspend // false) | tostring)] | @tsv'
else
  printf 'GAP: Flux HelmReleases unavailable or unreadable. Identify the deployment owner separately.\n'
fi
printf '\nFinished collection. Use the decision table below. A skipped or failed check is not a PASS.\n'
BASH
```

Check 1 prints namespace, deployment, service account, desired images, available replicas, and desired replicas. Check 2 prints pod, service account, container, image, running digest, and container readiness. Check 7 prints namespace, HelmRelease, chart, chart version, and suspension state. Empty discovery output does not prove that Kyverno is absent.

## 2. Decide your exposure

Record these outcomes separately. Do not infer a fixed binary from a Helm chart label alone.

| Evidence | Decision |
|---|---|
| Any running admission-controller replica uses upstream `v1.19.1` | Affected software is running. Prioritize remediation. |
| An older version is running | Keep in scope under the upstream affected range. Review its supported migration path. |
| Version is `1.9.19.1`, a private tag, a prerelease, or only a digest | Version status is unknown until the artifact owner maps the digest to source and patch provenance. |
| All running controller binaries map to the upstream `1.19.2` fix or a verified later release containing it | The software fix for this advisory is present. Complete rollout and policy-behavior checks below. |
| Tenant `create policies.kyverno.io` returns `yes` on an affected installation | The policy-authoring prerequisite is present. Assess triggering resource access and controller permissions. |
| Tenant has `update` or `patch` on existing Policies | Review as an additional policy-authoring route. The published reproduction uses `create`. |
| Admission controller can create cluster-wide webhook configurations | A permission used by the published escalation path is present. This does not mean the controller has a direct cluster-admin binding. |
| RBAC candidates have bindings to application users, groups, or service accounts | Review the granted namespaces, subject ownership, and `resourceNames` restrictions. Wildcards are included in the candidate scan. |
| Application identity returns `no` | That action is denied for that identity and namespace. Repeat for other identities, namespaces, and CI accounts. |
| Controller webhook creation returns `no` | That escalation route is constrained. Other controller permissions can still permit unauthorized reads or writes. Upgrade affected software. |
| `Forbidden`, timeout, unknown version, failed collection, or skipped checks | Evidence gap. Keep the relevant conclusion unknown. |
| Suspicious path scan returns entries | Review the policy owner, history, and resolved API target. Query strings and encoded characters can be legitimate. A hit is not proof of exploitation. |
| Suspicious path scan returns `[]` | No paths matched this heuristic in the current snapshot. This does not prove safety or rule out deleted Policies or dynamically constructed paths. |

The RBAC scan covers Kubernetes Roles and ClusterRoles and their direct bindings. It is not a complete model of external authorizers such as Azure RBAC, identity-provider group membership, impersonation, indirect RBAC escalation, or an application's control of another service account. Authorization reviews use the effective authorizers for the tested identity. Existing-policy scans are supporting evidence, not prerequisites for a vulnerability finding.

## 3. Contain an affected installation

If affected software is running, raise a security remediation change. If untrusted identities can author Policies, prioritize temporary containment while preparing the upgrade.

1. Through the existing RBAC or Azure authorization owner, restrict untrusted creation and modification of namespaced `policies.kyverno.io`. Cover `create`, `update`, and `patch`, including wildcard grants and CI identities.
2. Kubernetes RBAC grants are additive. An extra restrictive Role does not cancel another grant. Edit the granting source through its normal delivery path.
3. Preserve trusted policy automation and review application impact before changing permissions. Do not remove controller webhook permissions blindly or disable Kyverno.
4. Rerun the tenant authorization checks after containment. An administrator's result is not evidence that an application identity was constrained.

These steps reduce attack opportunities. They do not patch the binary. Policy Audit mode and Pod Security restrictions alone do not establish that this issue is contained.

## 4. Prepare the upgrade through the existing delivery owner

For a confirmed `1.19.1` installation, use Kyverno `1.19.2` as the minimum fixed version for this advisory. The official chart `3.9.2` declares `appVersion: v1.19.2`. A later approved release containing the fix is also an option. [Release notes](https://github.com/kyverno/kyverno/releases/tag/v1.19.2). [Chart mapping](https://raw.githubusercontent.com/kyverno/kyverno/v1.19.2/charts/kyverno/Chart.yaml).

1. Identify whether Flux, Helm, another operator, or a managed service owns the installation. Check 7 is a discovery aid and can miss renamed releases or chart references.
2. Prepare a reviewed change to that owner's source. For a standard Flux HelmRelease using `spec.chart.spec`, change its existing chart version to `3.9.2`. Preserve the release name, namespace, source reference, values, and environment-specific settings. For `chartRef`, change the referenced artifact through its owner.
3. Review explicit image tags and digests in values and valuesFrom references. A chart bump can leave the old binary running if overrides remain pinned. Mirror all required fixed artifacts through your approved registry process.
4. Follow the chart's CRD and RBAC upgrade procedure. Kyverno's guidance says changing image tags alone is insufficient. Preserve your established CRD ownership, especially when `crds.install` is disabled. [Upgrade guidance](https://kyverno.io/docs/installation/upgrading/).
5. If the actual version is much older than `1.19.1`, review every intervening minor release and the documented migration requirements. Do not apply this patch-upgrade assumption to a `1.9.x` installation.
6. Render the proposed chart with the reviewed environment values. Validate its changes and test representative existing policies in a lower environment before the approved production rollout.
7. Apply the approved change through the existing delivery owner. Avoid a manual Helm upgrade alongside a Flux-managed release.

This runbook deliberately has no automatic production upgrade command. Your actual owner, values, image overrides, and CRD management determine the correct change.

## 5. Verify remediation and review possible prior activity

Rerun the collection block after the approved rollout. Keep before-and-after evidence in your internal incident or change record.

1. Verify every intended Kyverno deployment has its desired number of available replicas. Check that no old admission-controller pods remain, including during a mixed-version rollout.
2. Map running image digests to fixed artifacts. Confirm no stale image overrides or GitOps reconciliation can restore the vulnerable version.
3. Confirm the delivery owner reports successful reconciliation and that controllers are healthy. Test one known permitted request and one known denied request using your approved existing policy tests in a suitable test namespace.
4. Rerun identity authorization checks and retain any intended restrictions on tenant policy authoring.
5. If suspicious Policies or unexpected webhook configurations are found, preserve evidence and involve incident response. Review API audit records for Policy creation or modification, controller-originated webhook or PolicyException writes, and unexpected ClusterRoleBinding changes. Successful exploitation does not have to leave the original Policy present.
6. Treat patching and incident investigation as separate tasks. An upgrade prevents this flaw from being used again but does not remove an already-created malicious webhook or restore changed privileges.

Use this report structure when handing off internally:

```text
Cluster alias and collection time:
Running Kyverno versions and digests:
Software status: AFFECTED / FIX VERIFIED / UNKNOWN
Tenant identity and namespace coverage:
Policy authoring permissions and candidate bindings:
Admission-controller webhook permissions:
Suspicious policy paths and audit findings:
Evidence gaps:
Containment owner and status:
Upgrade owner, target artifacts, and change reference:
Post-rollout verification and incident-review status:
```
