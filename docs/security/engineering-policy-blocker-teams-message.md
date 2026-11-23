# Teams message about the engineering policy blocker

Draft to copy into Teams. Updated 23 November 2026.

Hi [Name], could you help us resolve the recurring policy and change-process blockers affecting our engineering clusters? The current arrangement is becoming unsustainable. Routine changes repeatedly take weeks or months, disrupting our milestones and creating significant frustration and administrative effort without a clear benefit proportionate to the impact on engineering delivery.

This affects our ability to deliver across a range of requirements. We need an operating model that allows us to experiment and deliver effectively without repeatedly being blocked by dependencies within our own team or pod.

Fundamentally, we are deploying engineering applications onto Linux compute. Teams routinely deploy applications onto Ubuntu, Tomcat and other Linux servers; if those deployments were routinely blocked, we would have idle compute and frustrated users. Kubernetes adds an orchestration layer, but the applications still run on Linux nodes. If we deployed the same engineering tools directly onto a server, would the same restrictions apply? If not, what specific additional risk does Kubernetes introduce that each restriction is intended to address?

Strong controls remain essential for shared clusters and environments holding customer data. The proposed engineering environment has no customer workloads or data and is intended to have controlled network boundaries. We should verify those boundaries, including outbound connections and identities, and assume that someone with cluster access could reach a node. If the controls hold, external blast radius should be limited; it is not necessarily zero.

Could we review the policies blocking engineering work against the risks in this environment, and agree an exception or a separate baseline where an appropriate alternative control is available?

Two options are:

1. Approve a temporary exception on our existing dev/engineering clusters, with the agreed controls managed locally through Kyverno while the central process is resolved.
2. Establish a dedicated engineering management group and subscription boundary with an appropriate baseline and delegated authority for routine engineering changes.

Which approach would you prefer? Could you help bring the relevant owners together, agree a route and secure an implementation date? We need a durable resolution so that we can meet our commitments without having to escalate the same process constraints for every new requirement.

Option 1:
https://github.com/davidmarkgardiner/kagent-public/blob/main/docs/security/dev-engineering-policy-exception.md

Option 2:
https://github.com/davidmarkgardiner/kagent-public/blob/main/docs/security/engineering-management-group-option.md

Disposable cluster risk analysis:
https://github.com/davidmarkgardiner/kagent-public/blob/main/docs/security/disposable-engineering-cluster-risk.md
