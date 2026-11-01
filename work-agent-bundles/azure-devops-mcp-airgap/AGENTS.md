# Work-side execution contract

Start with FRONT-SHEET.md and HELM-OCI-WORK-AGENT.md for the current code workflow. The older
WORK-START-HERE.md describes the v2 read/draft-PR image only. This is a
replication bundle, not proof of work-side
readiness. Confirm Azure DevOps Services reachability and installed kagent schema.
Use the existing work delivery/secret/identity mechanisms. Preserve existing
Agent, gateway and ModelConfig names/configuration unless explicitly targeting
those resources. Adapt only this new scoped integration.

Do not add real organization values, repository IDs, private registry/cluster
addresses, credentials or raw A2A results to the public bundle. Keep rendered
configuration and receipts outside the repository. Never build with a PAT.

No cluster-time apt/npm/npx and no startup package downloads. Build the complete
image in the approved work builder or import the complete archive, then deploy
by the destination registry digest. The offline Dockerfile assumes the matching
dependencies image is already loaded. Changing dependencies requires rebuilding
that image.

Give the agent only the reviewed project/repository/branch/path scoped code
workflow tools, plus exact-scope draft creation if enabled. Do not add merge,
autocomplete, reviewer, arbitrary repository/SQL or Kubernetes write permissions.
Require actual kagent invocation and independent Azure DevOps commit/file/PR
readback before marking complete.
If disconnected from cloud Azure DevOps, report the network gap; do not claim
catalog discovery proves API access. On-prem Azure DevOps needs a separate adapter.
