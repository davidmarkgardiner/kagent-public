# Disposable engineering cluster: node compromise and external risk

## Purpose and operating model

The proposed environment is a single-purpose engineering cluster for short proofs of concept. The team would create a vanilla cluster, deploy and test an application, document the result, and then destroy or rebuild the cluster for the next proof of concept. It is intended to run for no more than 24 hours, normally one working day, with a scheduled job destroying it each evening and a fresh cluster created for the next morning's work.

The team reports that RBAC and network controls are already in place. The intended scope is only the engineering team's cluster and its nodes, with no customer workloads or customer data. No private connected systems are intended out of the box; any external endpoints initially required are understood to be publicly exposed. These are design inputs to verify for the particular deployment, not evidence that the deployed environment has been tested.

## Assume a node is compromised

Access to a node does not automatically confer access to another cluster or an external system. The external impact depends on what the node and its workloads can reach and what their identities and credentials can do. A public endpoint is still an external system: reachability and any permission to read or change it matter. The cluster also has Kubernetes and AKS system components even before the proof-of-concept application is installed; inventory those components and their access rather than assuming the application is the only workload.

Within the cluster, a compromised node may expose workloads, credentials and data on that node and may provide a route to other nodes or cluster resources. The absence of customer workloads reduces the potential impact, but does not make engineering credentials, images, results or services valueless.

## What the security context contributes

Controls such as dropping Linux capabilities, restricting privilege escalation, running without privilege and using a read-only container root filesystem constrain a container process. They can reduce the chance or impact of a workload compromise and make some paths to the node harder. A read-only root filesystem does not automatically make mounted volumes read-only. These controls are defence in depth; they do not, by themselves, establish the boundary around a node that is already compromised.

For this disposable environment, review each blocking restriction against the specific risk it addresses, the work it prevents and the external controls available. Agree an engineering baseline or time-limited exception with the policy owners, rather than assuming that all restrictions can safely be removed or that an alternative control is automatically equivalent.

## Evidence needed before claiming containment

Record the cluster and subscription scope, owner, creation and destruction times, and the approved proof-of-concept workload. For each run, or through a verified repeatable baseline, establish:

- **Network:** node and pod routes, DNS, egress, private links, peering, proxies and reachable services; confirm that node-level traffic is covered by the intended boundary.
- **Identity and RBAC:** node, cluster, add-on and workload identities; accessible credentials; their actual Azure and Kubernetes permissions and scopes. Confirm there are no unintended permissions to other environments.
- **Inventory:** nodes, system and add-on workloads, mounts, secrets and external dependencies, including public services that can be changed using an available credential.
- **Lifecycle:** the scheduled destruction job's owner, execution record, failure alert and fallback. Verify actual deletion and residual resources after each run; a schedule is not proof of destruction. Enforce the 24-hour limit with a defined response when deletion fails.
- **Recovery:** identify separately managed identities, role assignments, credentials, logs and other resources that may survive cluster deletion. Revoke or clean them up as appropriate. Deletion cannot undo external changes or disclosure that already occurred.

If the boundary checks pass, the expected external blast radius is limited, subject to the recorded exceptions and residual risks. Short lifetime reduces exposure time; it does not prevent compromise during the working day. Preserve off-cluster evidence needed to investigate a compromise and confirm destruction without retaining unnecessary sensitive data.

The [engineering policy Teams draft](engineering-policy-blocker-teams-message.md) sets out the decision request and the comparison with deploying applications onto Linux servers.
