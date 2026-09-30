# Start here — Radar topology workplace trial

**Goal:** one approved development cluster, a browser topology map, and one
kagent Agent querying a known resource's connections through read-only MCP.

Start with [README.md](README.md). Review the [local proof](VERIFICATION.md)
and [known coverage gaps](../kubernetes-topology-poc/RADAR-EVALUATION.md).

1. Choose the approved cluster/context, dedicated Radar namespace, kagent
   namespace, existing accepted ModelConfig, and approved image/chart source.
2. Fill `config.local.json`, render, verify the chart and permissions, and check
   the workplace CRD schemas. Keep generated workplace files outside public Git.
3. Deliver through existing Flux for permanent installation, or the README's
   Helm path for an approved development trial. Use no external ingress initially.
4. Prove readiness, RBAC denials, NetworkPolicy enforcement, UI navigation,
   a direct bounded MCP query, kagent discovery, and one real Agent tool call.
5. Record scope/errors and classify the result. A ready Agent alone is not a
   completed triage proof. Do not enable writes on this Agent.

**Included now:** standard inventory collection, relationship UI, current graph
queries, inline investigation instructions/rubric, and install/verification assets.

**Next phase:** guidance lookup using the existing approved KB/querydoc service,
versioned skill packaging, custom AgentgatewayBackend relationships, and fleet
availability/scaling decisions. The `knowledge/` catalog is a proposed format.

## Work-agent handoff prompt

```text
Use this Radar topology MCP bundle on the approved development cluster.
Inspect the existing delivery pipeline, installed kagent CRDs/runtime, model
configuration, image restrictions, and namespace policies before adapting files.
Keep permanent changes in the workplace's GitOps repository. Preserve existing
Agent/ModelConfig/Gateway objects and create the bundle's separate read-only Agent.
Render only non-secret inputs and reject unresolved placeholders. Review selected
inventory reads and enforce the ingress policy before giving the Agent access.
Run the documented checks and inspect a real get_neighborhood tool trace.
Report live proof, missing scope, unsupported edges, and provider failures separately.
Do not claim installed knowledge lookup or runtime skills: those are a next phase.
Do not enable apply/delete/exec tools or broaden the Agent's tool allowlist.
Stop before an unapproved workplace deployment or external publication.
```

Use [GITLAB-TICKET.md](GITLAB-TICKET.md) for the team's installation work item.
