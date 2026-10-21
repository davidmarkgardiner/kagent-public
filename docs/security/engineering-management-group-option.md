# Dedicated management group for engineering delivery

Updated 21 October 2026.

## Proposed option

Establish a dedicated Azure management group and subscription boundary for the team's engineering clusters, with an agreed engineering baseline and delegated authority for routine changes. Place it outside the hierarchy that applies the restrictive workload policies currently blocking experimentation and delivery, subject to approval from the relevant policy owners.

This is an alternative to the [temporary policy exception on existing clusters](dev-engineering-policy-exception.md). It addresses the recurring operating-model problem across engineering deliverables, rather than granting relief for one feature at a time.

Microsoft's Azure landing-zone guidance recommends a sandbox management group for experimentation. That provides a recognised model for separating engineering experimentation from environments that require the production governance baseline:

https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/resource-org-management-groups

## What moves in Azure

A management group contains subscriptions and other management groups. An AKS cluster belongs to a resource group within a subscription. The supported hierarchy change is therefore to move the **subscription** to the engineering management group.

| Existing arrangement | Implementation implication |
| --- | --- |
| The engineering clusters occupy a dedicated subscription | Move that subscription under the approved engineering management group. The clusters remain in the same subscription; the change affects inherited policy and access across the whole subscription. |
| Engineering shares a subscription with other workloads | Moving the subscription affects those workloads too. A new dedicated engineering subscription provides an independent boundary. |
| Existing AKS clusters need to be in that new subscription | AKS does not support moving a cluster between subscriptions. Deploy replacement clusters and migrate workloads and dependencies through a planned transition. |

Subscription moves require appropriate permissions at the subscription and relevant management-group scopes. Review inherited access, custom roles and policy dependencies before approving the move. A hierarchy change should not be treated as a guarantee that every workload dependency remains unaffected.

Microsoft's supported move procedure and AKS limitations are documented here:

https://learn.microsoft.com/en-us/azure/governance/management-groups/manage#move-management-groups-and-subscriptions

https://learn.microsoft.com/en-us/azure/aks/faq#can-i-move-or-migrate-my-cluster-between-subscriptions

## Policy inheritance and engineering authority

Creating a new management group does not automatically remove policy enforcement. Policies at the tenant root and other shared ancestors continue to apply. Direct assignments at subscription, resource-group or resource scope must also be assessed, together with existing Kubernetes admission controls. Placing the engineering group beneath the same restrictive parent would preserve the inherited restrictions.

Agree the actual policy boundary with the policy owners: the engineering subscriptions must be outside the unwanted assignment scopes or have approved exclusions or exemptions. Preserve an explicitly agreed baseline, with suitable identity, audit, network and cost controls. Assign engineering permissions at the subscription or resource scopes needed to operate the environment, and delegate routine Kubernetes policy management through reviewed GitOps changes.

The objective is an environment with the authority and flexibility needed to deliver engineering work. Recreating the existing approval queue in a new management group would leave the blocker unresolved.

The inheritance and assignment mechanisms are described here:

https://learn.microsoft.com/en-us/azure/governance/management-groups/overview

https://learn.microsoft.com/en-us/azure/governance/policy/concepts/scope

## Implementation decision

1. Confirm which subscriptions contain the engineering clusters and whether those subscriptions contain other teams' or production workloads.
2. Inventory the blocking policy assignments and their ancestors, direct assignments, inherited access and Kubernetes controls.
3. Agree the engineering management-group position, baseline, delegated authority and any ICV or SDLC exception required.
4. Select an existing-subscription move or a new-subscription deployment and migration, based on that inventory.
5. Assign an implementation owner and target date. Validate effective policy, access and representative engineering deployments before declaring the environment ready.

## Choosing between the options

Use the temporary exception to pursue immediate relief on the existing clusters. Assess the separate engineering management group as a durable boundary, particularly if dedicated engineering subscriptions already exist. If new subscriptions and replacement clusters are required, account for that migration effort when comparing the routes. Both can be pursued in parallel if immediate relief is needed while the longer-term arrangement is established.

Management sponsorship is needed to select a route, bring the relevant owners together and secure an implementation date. The required outcome is reliable engineering delivery without repeating the same approval escalation for each new requirement.

The [Teams message](engineering-policy-blocker-teams-message.md) presents both options and requests that decision.
