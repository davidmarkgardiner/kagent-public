# Bring-Your-Own Agent Harness Boundaries

**Purpose:** Let a team bring its own agent or Hermes-style harness into the platform without giving that agent unrestricted tools, network access, cluster authority, or publication rights.

This is an onboarding and security design. It does not grant access or deploy a harness.

## The key rule

**Proposed design:** Treat skills, prompts, and agent instructions as guidance—not authorization. Enforce authority separately at the tool grant, Agent Gateway, MCP service account, network, Kubernetes RBAC, and workflow-executor layers.

An agent may be excellent at following a “read-only” instruction and still be unsafe if an attached MCP server holds broad Kubernetes credentials. The MCP server identity and gateway policy—not the agent prompt—decide what can actually happen.

## Desired onboarding outcome

```text
Team-owned agent or AgentHarness
  -> approved model route through Agent Gateway
  -> named skills loaded as guidance
  -> explicitly granted MCP/A2A tools only
  -> MCP policy and service account enforce allowed operations
  -> NetworkPolicy permits only approved destinations
  -> Kubernetes RBAC limits the target namespace/resources
  -> requireApproval + workflow executor gate every mutation
```

## Seven enforcement layers

| Layer | What it controls | Required rule | Classification |
| --- | --- | --- | --- |
| 1. Intake and tenant binding | Who owns the agent and where it may run | Require team, cost-centre, repo/image provenance, requested namespace, target cluster class, data classification, and acceptance tests. | **Proposed design** |
| 2. Harness/runtime | Where the untrusted agent process runs | Run each tenant agent/harness in its own namespace and sandbox/runtime boundary. Require resource limits and an approved image source. | **Proposed design** |
| 3. Skills | What the agent is instructed to know or do | Load only allow-listed, versioned skills. Skills do not grant MCP tools, Kubernetes verbs, or network access. | **Proposed design** |
| 4. Tool grants | Which tools an individual agent may invoke | Bind each agent to named, verified tools with an explicit allow-list and expiry. Deny admission if a required grant is absent or expired. | **Verified checked-in pattern** — `ToolGrant`, `ToolCatalogEntry`, and Kyverno policy exist under [`infra/byo-kagent`](../../../infra/byo-kagent/README.md). |
| 5. Agent Gateway and MCP policy | Which calls can traverse the gateway and reach a tool/provider | Route models and MCP traffic through Agent Gateway where supported; authorise by calling agent, namespace, tool/action, and target. | **Verified current capability** for Agent Gateway policy patterns; exact installed schema requires validation. |
| 6. Network and identity | Which endpoints and Kubernetes APIs are reachable | Apply default-deny NetworkPolicy, explicit egress allow-list, workload identity/service account, and namespace-scoped RBAC. | **Verified checked-in pattern** — BYO sandbox guidance describes these controls; target enforcement needs validation. |
| 7. Mutation/execution | Which state changes may actually occur | Keep tenant agents read-only by default. Send allowed mutations through a separately privileged workflow executor after exact approval and evidence checks. | **Proposed design** |

## What a team submits

**Proposed design:** A team should submit a pull request or equivalent reviewed request containing only placeholder-safe, declarative material:

| Submission item | Must state |
| --- | --- |
| Agent or AgentHarness manifest | Owner/team, namespace, pinned image/digest, resources, model reference, requested skills, and no embedded credentials. |
| Tool request | Catalog entry/version, exact tool names, purpose, read/write classification, expiry, and requested namespace/resource scope. |
| Network request | Required model, MCP, source-control, or internal service destinations; all other egress remains denied. |
| Identity request | Namespaced service account and minimum Kubernetes API verbs/resources, with no ClusterRoleBinding for a tenant. |
| Test plan | Positive read-only test, negative tool-denial test, negative network-denial test, and cleanup/rollback evidence. |
| Approval plan | Which action types require human approval, named approver role, expiry, and evidence retention path. |

## Tool and skill boundary model

| Concept | It does | It must not be trusted to do |
| --- | --- | --- |
| Skill | Gives the agent a reusable procedure, instruction, or domain knowledge | Authorise a tool, reveal a credential, override RBAC, or create a network route |
| `toolNames` on the Agent | Selects the tool names that agent may request from a referenced MCP server | Replace gateway-side or MCP-server-side authorization |
| ToolGrant/catalog | Records the approved agent-to-tool relationship and allowed tool names | Make a broad MCP service account safe by itself |
| Agent Gateway policy | Authenticates/authorises and governs routed model/MCP traffic | Replace Kubernetes RBAC or contain an endpoint that is reachable outside the gateway |
| MCP server service account | Executes the actual Kubernetes/API call | Grant broader authority than its least-privilege role |
| Kubernetes RBAC | Enforces API operations against the Kubernetes API | Restrict a non-Kubernetes external API or arbitrary egress |
| `requireApproval` | Stops a named tool before execution | Authorise an unauthenticated callback or validate the scope of a vague approval |

## Recommended access tiers

| Tier | Permitted work | Tool and cluster boundary | Human approval |
| --- | --- | --- | --- |
| T0 — isolated author | Generate or review code in a sandbox/worktree | No kube credential; no external write tools | Not applicable |
| T1 — evidence reader | Read approved namespace logs, events, objects, metrics, and deployment metadata | Read-only catalog tools; namespace-restricted MCP service account; default-deny egress | No, within intake scope |
| T2 — planner | Produce a proposed manifest, Helm values, or remediation plan | T1 plus repository read/write in dedicated worktree; no live apply | No live mutation |
| T3 — approved executor | Submit a narrowly scoped, reversible non-production change | Separate workflow executor identity; exact tool/action/target approval; post-action verification | Yes, required |
| T4 — prohibited by default | Production change, cluster-wide action, credential handling, external publication, or destructive operation | No tenant-agent direct route | Explicit owner approval and a separately reviewed execution path |

## Agent Gateway and MCP routing rules

**Proposed design:** A team agent does not receive raw provider credentials or direct unrestricted MCP URLs. Instead:

1. The team references an approved `ModelConfig` that routes through Agent Gateway.
2. The team references a verified `RemoteMCPServer` or a gateway-mediated MCP endpoint.
3. The Agent lists exact `toolNames`; wildcards and implicit full-server grants are rejected.
4. Gateway policy verifies the caller identity/namespace and permits only the registered tool/action set.
5. The downstream MCP service account independently permits only the approved Kubernetes resources and verbs.
6. NetworkPolicy permits only DNS, kagent/Agent Gateway, the approved MCP endpoint, and explicitly needed services.

**Verified checked-in pattern:** The BYO design describes catalog-verified tools, per-agent `ToolGrant` allow-lists, expiry, and Kyverno admission. It also calls out the key hazard: a tool server with broad RBAC can amplify an agent's effective privilege. See [BYO-KAgent architecture](../../../infra/byo-kagent/README.md) and [sandbox threat model](../../../infra/byo-kagent/SANDBOX-ONBOARDING.md).

## Admission and lifecycle flow

```text
Team request / pull request
  -> platform review: image, skills, tool request, network, RBAC, test plan
  -> quarantine/verify any new MCP service
  -> create immutable tool catalog entry
  -> create scoped ToolGrant with expiry
  -> GitOps reconciliation
  -> Kyverno admission checks
  -> deploy tenant agent/harness into tenant namespace
  -> run allow and deny smoke tests
  -> collect evidence and approve/deny promotion
```

| Gate | Block if | Classification |
| --- | --- | --- |
| Image and runtime | Image provenance/digest, resource limits, or isolation boundary is missing | **Proposed design** |
| Skills | Skill is not from an approved, versioned source or requests authority beyond the tier | **Proposed design** |
| MCP tool | Tool is not catalogued/verified, tool name is not explicit, grant is missing/expired, or service account is too broad | **Verified checked-in policy pattern** for catalog/grant admission; exact deployment requires validation |
| Model route | Model bypasses Agent Gateway without an approved exception | **Verified checked-in policy pattern** — BYO policy describes the route requirement; exact CRD behaviour requires validation |
| Cluster target | Tenant/team label, namespace, resource limits, or permitted target binding is missing | **Verified checked-in policy pattern** — `validate-agent-cluster-target` |
| Live proof | Read test, deny test, egress test, or audit evidence is absent | **Proposed design** |

## Required verification evidence

**Proposed design:** Do not accept “the Agent CR is Ready” as proof of safe access. Capture each of these outcomes:

| Test | Expected result |
| --- | --- |
| Admission | A valid scoped agent is accepted; an agent without a required ToolGrant is denied. |
| Tool allow | The agent can call one granted read-only tool in its approved namespace. |
| Tool deny | The same agent cannot call an ungranted/destructive tool, even if the MCP server advertises it. |
| RBAC deny | The tool service account cannot read or mutate an unapproved namespace/resource. |
| Egress deny | The agent cannot connect to an unapproved external or cluster endpoint. |
| Gateway audit | Model/MCP request is attributed to the agent/team and is visible in approved audit/observability evidence. |
| Approval | A state-changing test pauses, accepts one valid approval only, and remains unchanged on deny/expiry. |
| Cleanup | Test resources, approval records, and any temporary tool registration are removed or retained according to policy. |

## Decisions needed from the platform owner

| Decision | Why it is needed |
| --- | --- |
| Agent type | Decide whether teams bring a declarative kagent Agent, a container-based BYO agent, or an AgentHarness. |
| Tenant trust model | Decide whether the agent image is team-built but platform-scanned, or platform-built from a submitted source repository. |
| Tool publishing process | Define quarantine, catalog owner, review SLA, semantic versioning, and expiry/revocation behaviour. |
| Execution model | Confirm that all mutations use a separate workflow executor, or define the narrow exceptions and approval mechanism. |
| Private connectivity | Identify private model/MCP services, approved egress routes, DNS, and identity method. |
| Audit/retention | Set evidence retention, redaction, and which records are attached to Hermes/Kanban versus a central audit store. |

## Minimum safe first proof

**Proposed design:** Onboard one team-owned, read-only agent into a pre-approved non-production namespace. Grant only a single catalogued inventory tool and an approved model route. Demonstrate one allowed read and three denials: an ungranted tool, a different namespace, and unapproved egress. Promote no write tool until those results are independently reviewed.
