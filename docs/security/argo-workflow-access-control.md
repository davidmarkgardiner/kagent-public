# Argo Workflow access control and privilege escalation

Reviewed: 21 October 2026. This document records a repository-based assessment and
recommended controls. It does not establish the running cluster's configuration
or claim that these controls have been deployed.

## Why workflow creation is a security boundary

Permission to create an arbitrary Workflow effectively allows a caller to ask
Argo to create Pods in that Workflow's namespace. The caller does not need direct
Pod-creation permission because the controller creates Pods on their behalf.

Without admission restrictions, those Pods can select a service account in the
same namespace and mount namespace Secrets. Selecting a service account does not
require the caller to have Kubernetes impersonation permission. Mounting a Secret
does not require the caller to have direct API permission to read that Secret.

This can become privilege escalation when the namespace contains powerful service
accounts or credentials. Node access is another risk if admission permits
privileged containers, host namespaces, or host filesystem mounts. Workflow
creation does not automatically grant cluster-admin, and workflow containers do
not automatically inherit the controller's service account.

Argo documents this boundary in its security guidance:
https://argo-workflows.readthedocs.io/en/latest/security/

Kubernetes describes the corresponding workload-creation risks:
https://kubernetes.io/docs/concepts/security/rbac-good-practices/

## What the repository currently shows

The following observations were checked against `origin/main` at `ffcdf765`.
Deployment overrides and live admission policies remain unverified.

| Repository evidence | Security implication |
|---|---|
| [Namespace provisioning RBAC](../../platform/argo-workflows/rbac/rbac.yaml) puts `argo-namespace-provisioner` in `argo`, with cluster-wide Secret and workload permissions. | Arbitrary code running under this account has a broad impact across namespaces. |
| [ASO provisioning RBAC](../../platform/argo-workflows/rbac/aso-stack-rbac.yaml) binds `aso-stack-deployer` to the ASO manager role and additional Argo and namespace-provisioning roles. | Provisioning identities need protected execution and a review of their effective permissions. |
| [Workflow RBAC](../../platform/argo-workflows/rbac/workflow-rbac.yaml) lets `argo-workflow` create and modify namespaced WorkflowTemplates. | Template restrictions are weakened if execution identities can rewrite trusted templates. |
| [Chart metadata](../../platform/argo-workflows/install/Chart.yaml) specifies `v3.7.2`, and [chart values](../../platform/argo-workflows/install/values.yaml) leave `workflowRestrictions` empty. | The checked-in baseline predates published restriction-bypass fixes and does not enable template restrictions. |

## The recommended division of controls

Use Kubernetes RBAC to decide who can create Workflows. Use Kyverno to validate
what permitted callers submit. Enforce Pod security independently of both.

| Layer | Recommended responsibility |
|---|---|
| Kubernetes RBAC | Grant Workflow creation only to named operator groups and trusted automation accounts, within designated namespaces. |
| Argo SSO RBAC | Map authenticated users and groups to appropriately scoped Kubernetes service accounts. |
| Kyverno | Restrict callers, template references, execution identities, parameters, and security-sensitive overrides at admission. |
| Platform GitOps | Own execution templates, RBAC, admission policies, and submission-service configuration. |
| Pod admission | Enforce Restricted Pod Security and additional restrictions on service accounts, Secret mounts, and images. |

### Who can create Workflows

Ordinary users and agents should not have direct Workflow-creation permission in
the privileged execution namespace. A trusted submission service or Argo Events
Sensor can create approved workflows there. That service must authorize each
operation and validate its inputs. Moving creation behind a service does not make
untrusted requests safe by itself.

RBAC permissions are additive. Removing one RoleBinding does not cancel access
granted through another binding, an aggregated role, or wildcard permissions.
The review must cover Workflow creation, CronWorkflows, template modification,
and alternative routes through Pods, Jobs, Deployments, exec, and credential access.

RBAC reference:
https://kubernetes.io/docs/reference/access-authn-authz/rbac/

### What Kyverno can enforce

Admission rules can reject Workflow creation unless the authenticated caller is
an approved group or service account. Separate rules should validate changes to
execution-relevant fields, while permitting required controller reconciliation.

The policy contract should require the following:

- An allowlisted `workflowTemplateRef` for the caller and namespace.
- An approved execution service account, fixed by the trusted template.
- Bounded parameters that cannot become arbitrary commands, scripts, manifests,
  image names, or privileged targets.
- Rejection of unauthorized inline templates and security-sensitive overrides,
  including nested artifact-GC Pod patches and service-account settings.
- Protection of WorkflowTemplates, ClusterWorkflowTemplates, CronWorkflows,
  Sensors, and policy configuration from unauthorized modification.

Use enforcement mode to block requests. Audit mode only reports violations.
Identity-based Kyverno rules depend on AdmissionReview information and need
`background: false`. Configure the admission path to fail closed for protected
operations, with narrowly scoped exceptions and suitable availability.

Do not trust a caller-supplied creator label or approval parameter as identity.
Through Argo SSO, Kubernetes may see a mapped service account rather than the
human user. Check the actual admission identity before writing caller rules.
Apply those rules to Workflows: generated Pods arrive under the controller's
identity, so Pod admission alone cannot identify the original submitter.

Kyverno references:

- https://kyverno.io/docs/policy-types/cluster-policy/validate/
- https://kyverno.io/docs/guides/reports/
- https://argo-workflows.readthedocs.io/en/latest/argo-server-sso/

### Where privileged execution belongs

Keep the controller namespace separate from ordinary workflow execution and
privileged platform execution. Place provisioning accounts only in the protected
execution namespace. Give each execution account the smallest required resource
and namespace permissions. Review any associated Azure Workload Identity access.

A separate service account is insufficient if arbitrary workflow authors can
select that account. Similarly, `allowPrivilegeEscalation: false` and non-root
containers do not remove the account's Kubernetes API permissions.

Enforce Restricted Pod Security for generated Pods, including auxiliary Pods.
Add policies for permitted identities and Secret mounts because Restricted Pod
Security does not authorize service-account selection or Secret access. Protect
namespace labels and policy exceptions so submitters cannot disable enforcement.

Pod Security Standards:
https://kubernetes.io/docs/concepts/security/pod-security-standards/

### Argo template restrictions and version requirements

Use `templateReferencing: Secure` on a patched Argo release. This requires template
references and detects changes to the referenced template between operations.
It does not replace caller authorization, parameter validation, or Pod admission.

Published fixes for template-restriction bypasses include Argo `3.7.15` and
`4.0.6`. These are minimum versions for the cited bypass fixes, not a complete
upgrade recommendation. Select a maintained patch release after reviewing all
applicable advisories and testing compatibility.

- https://argo-workflows.readthedocs.io/en/latest/workflow-restrictions/
- https://github.com/argoproj/argo-workflows/security/advisories/GHSA-48p8-g2fx-3wwm

## Alternatives and proof still required

Kubernetes-native ValidatingAdmissionPolicy with CEL is an alternative for
straightforward validation rules. OPA Gatekeeper is another policy engine.
Given the repository's existing Kyverno patterns, RBAC plus Kyverno is the
recommended starting point.

Native admission policy reference:
https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/

The next verification needs the target cluster's deployed Argo version, effective
RoleBindings and ClusterRoleBindings, SSO account mappings, and admission policies.
Before calling the boundary enforced, prove that an approved submission succeeds
and that unauthorized callers, account selection, template changes, unsafe
parameters, Secret mounts, and privileged Pod settings are rejected. Cover both
direct Kubernetes submission and the Argo API, including relevant update paths.
Keep any runtime tests scoped to an explicitly authorized test environment.
