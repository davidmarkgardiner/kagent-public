# Kyverno exposure explained in plain English

**Restricting policy-writing permissions is the immediate containment. Upgrading to a fixed version is the lasting remediation.** RBAC restrictions reduce the opportunity to exploit the flaw but do not repair the vulnerable software.

## What is the problem?

Imagine the cluster is a building. Each application team has its own room, called a namespace.

Kyverno is the caretaker. It has powerful keys because it checks security rules across the building.

The bug lets someone who can write a Kyverno Policy give the caretaker an instruction that reaches outside their room. Kyverno can carry out that instruction using its own stronger permissions.

In Kubernetes terms, a policy author can cause Kyverno to make API requests outside their namespace using the controller's service account. Depending on that account's permissions, the result can include access to another team's information, changes to security controls, or a path to cluster-admin access. The attacker does not need to be an administrator already.

The published attack starts with an authenticated user who can create a namespaced Kyverno Policy. Merely being able to deploy an application does not establish that permission. [Upstream advisory](https://github.com/kyverno/kyverno/security/advisories/GHSA-3xfv-vq8x-qhg4).

## What does version 1.13.1 mean for us?

The upstream affected range is **at or below 1.19.1**, which includes **1.13.1**. It lists **1.19.2** as patched. Treat an upstream 1.13.1 installation as affected unless the artifact owner can demonstrate a relevant backported fix. The published reproduction uses 1.19.1; this document does not claim that the same reproduction was tested against your 1.13.1 installation. [Affected versions](https://github.com/kyverno/kyverno/security/advisories/GHSA-3xfv-vq8x-qhg4).

The reported workplace version still needs confirmation. Affected software is not evidence that anyone has exploited it.

## Contain the exposure now

Restrict ordinary application users and automation from creating or changing namespaced Kyverno Policies until the upgrade is complete.

- Review `create`, `update`, and `patch` on resource `policies` in API group `kyverno.io`. Policy modification is an additional route to review; the published reproduction uses creation.
- Cover users, groups, service accounts, CI identities, and wildcard grants. If Azure RBAC or another authorizer grants access, restrict that source too.
- Remove the unwanted grants through their existing owner. Kubernetes RBAC permissions are additive, so adding a restrictive Role does not override an existing grant.
- Retain policy management for the trusted platform identities that need it. Verify that ordinary application identities are denied in their actual namespaces.

The goal is to restrict who can instruct Kyverno. Do not blindly remove the controller's operational permissions or disable Kyverno, since that can disrupt security enforcement.

These restrictions contain future policy-authoring opportunities. They do not neutralize an already-created malicious Policy or webhook. Investigate unexpected existing objects separately.

## Complete the lasting remediation

Upgrade to **1.19.2 or a later approved release containing the fix** through the existing deployment owner.

From 1.13.1, review the intervening release changes and test existing policies before rollout. Include the chart or manifests, CRDs, RBAC, and any pinned image overrides. Changing only an image tag is insufficient according to Kyverno's upgrade guidance. [Upgrade guidance](https://kyverno.io/docs/installation/upgrading/).

After rollout, verify that every controller replica runs a fixed artifact and that expected policy enforcement still works. Keep policy-writing access limited to trusted identities.

Use the [read-only exposure runbook](kyverno-ghsa-4c7q-j33x-866w-runbook.md) to confirm images, permissions, and evidence gaps. Record software status, practical exposure, and evidence of exploitation separately.
