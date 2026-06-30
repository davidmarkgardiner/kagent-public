# Team Message: Review New AKS Features During Version Upgrades

Hi team,

As part of the AKS `1.34` release planning, Azure Container Linux ACL is a good example of something we should be actively reviewing rather than discovering later.

More generally, when a new AKS version becomes available, we should create backlog tickets for the notable new platform features and review them as part of the upgrade cycle. At the moment, it feels like we mostly do the version upgrade itself and do not consistently assess the new capabilities that arrive with that release.

That means we may be missing useful opportunities for the platform and for the customers who depend on it. New AKS features could improve security, reliability, cost, operations, developer experience, or managed-service coverage, but we only get that value if we deliberately review them and decide whether to adopt, pilot, defer, or reject them.

Proposal:

- For every AKS minor version upgrade, create backlog tickets for the major new AKS features and platform changes.
- Review each feature against our platform stack, customer use cases, security posture, and operational model.
- Record a decision for each feature: adopt, pilot, defer, reject, or no action needed.
- Treat this as part of doing the AKS upgrade properly, not as optional follow-up work after the version bump.

For AKS `1.34`, ACL should be one of those review tickets. The next step is to deploy a non-production ACL cluster, install our standard stack, test the Nexus image-pull certificate path, and confirm whether our add-ons and applications work before deciding whether ACL belongs in the `1.34` rollout.
