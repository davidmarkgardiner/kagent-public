# App Onboarding — Interview Reference

## Agent: `app-onboarding-agent`
## Output: GitOps YAML for PR submission — nothing applied to the cluster

---

## Question → Output Mapping

| # | Question | Used In | Default |
|---|----------|---------|---------|
| 1 | Application name | Deployment/Service name, request.yaml `agentName` | — |
| 2 | Team | `platform.com/team` label, request.yaml `metadata.team` | — |
| 3 | Namespace | ALL manifests (namespace-anchored) | — |
| 4 | Container image + tag | Deployment `spec.containers[].image` | — |
| 5 | Port | Deployment `containerPort`, Service `port`/`targetPort` | 8080 |
| 6 | Protocol | VirtualService route type | HTTP |
| 7 | Istio ingress? | VirtualService + host/path | no |
| 8 | AuthorizationPolicy? | AuthorizationPolicy | no |
| 9 | Resource requirements | Deployment `resources`, request.yaml `budget` | 100m/500m/128Mi/512Mi |

---

## Generated Files

| File | Always | Condition |
|------|:------:|-----------|
| `deployment.yaml` | ✓ | — |
| `service.yaml` | ✓ | — |
| `virtual-service.yaml` | | Q7 = yes |
| `authorization-policy.yaml` | | Q8 = yes |
| `request.yaml` | | User requests triage agent (ask after YAML output) |

---

## Istio Precedents

Existing VirtualService and AuthorizationPolicy examples: `ai-platform/teams-hitl/istio/`

Use `spec.http` routing for HTTP/gRPC, `spec.tcp` for TCP.

---

## request.yaml Schema

See `assets/request-template.yaml` for the full template.

```yaml
metadata:
  agentName: <app-name>-triage-agent
  team: <team>
  costCenter: <cost-centre>        # ask if not already collected
target:
  clusters: []                      # user fills in
model:
  ref: shared/gpt-4o
tools:
  - catalogRef: "<name>@<version>"  # MUST be verified ToolCatalogEntry
    scopes: [...]
budget:
  cpu: <cpu-limit>
  memory: <memory-limit>
```

### Tool Reference Rules ⚠️

- Tool references **MUST** use verified `ToolCatalogEntry` values from the catalog
- New MCP tools must pass through `mcp-onboarding-template` quarantine before appearing in the catalog
- Do not invent tool names — reference only what exists in the catalog

---

## BYO-KAgent Workflow

`byo-kagent-onboarding-template` is a **PR-triggered review workflow**, not a deployment pipeline.

Submission path:
1. Save `request.yaml`
2. Open a PR labelled `byo-kagent` → triggers the review workflow
3. Platform team reviews and promotes

---

## Confirmation Phrase

User must type exactly: `yes, generate`

---

## Namespace Anchoring

CRITICAL: Use the exact namespace string from Q3 in every generated manifest.
Copy character-for-character. Do not slugify, lowercase, or modify.
