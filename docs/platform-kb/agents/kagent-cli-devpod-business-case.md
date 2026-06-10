# kagent CLI DevPod Evaluation

This note evaluates the kagent CLI from the upstream quickstart for a work DevPod trial. It separates the low-risk local CLI install from the higher-risk act of installing kagent and tool-capable agents into a Kubernetes cluster.

Sources checked on 2026-06-10:

- Upstream quickstart: `https://kagent.dev/docs/kagent/getting-started/quickstart`
- Upstream installation guide: `https://kagent.dev/docs/kagent/introduction/installation`
- Upstream architecture guide: `https://kagent.dev/docs/kagent/concepts/architecture`
- Upstream local development guide: `https://kagent.dev/docs/kagent/getting-started/local-development`
- Upstream release: `https://github.com/kagent-dev/kagent/releases/tag/v0.9.6`

## Executive View

The business case is not "install another chat tool." The case is to give platform engineers a Kubernetes-native way to build, test, and operate AI agents using the same controls we already use for workloads: CRDs, namespaces, RBAC, GitOps, admission policy, observability, and progressive rollout.

The CLI is useful as a developer and operator entry point:

- Install a minimal kagent control plane into a sandbox or management cluster.
- Open the dashboard through a local port-forward without exposing a public UI.
- List and invoke agents from a terminal.
- Scaffold, build, run, dry-run, and deploy BYO agent projects.
- Generate Kubernetes YAML with `kagent deploy --dry-run` so work adoption can stay GitOps-first.

For work use, the CLI should be approved first for DevPod-based evaluation, not for broad workstation or production-cluster installation. The DevPod trial should prove whether the CLI improves agent build/test speed and operational triage workflows before requesting a wider software-install approval.

## Benefits

| Benefit | Why it matters at work |
|---|---|
| Faster agent prototyping | Engineers can scaffold and run a BYO agent locally before asking for cluster resources. |
| GitOps-compatible output | `kagent deploy --dry-run` can produce manifests for review rather than applying directly. |
| Kubernetes-native governance | Agents and tools are represented as Kubernetes resources, so RBAC, namespaces, Kyverno, Flux, and audit controls can apply. |
| Lower onboarding friction | The CLI can port-forward the dashboard and invoke agents without teaching every tester the raw service topology. |
| Better platform fit than desktop-only agent tooling | The runtime sits with cluster operations, MCP tool servers, A2A workflows, and existing observability patterns. |
| Provider flexibility | kagent supports OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama, Vertex, Bedrock, and OpenAI-compatible providers, which keeps the work design from depending on one model vendor. |
| Clear path to internal platform service | A DevPod pilot can graduate into a managed cluster-side kagent front door where SREs use the UI, A2A, or curl without installing local MCP tools. |

## Costs And Risks

| Risk | Practical mitigation |
|---|---|
| Supply-chain approval needed for a new binary | Pin the version, record the upstream release, and install only inside DevPod during evaluation. |
| The upstream one-line installer executes a remote script | Use `scripts/install-kagent-cli-devpod.sh`, which downloads the version-pinned installer first and runs it with `--no-sudo`. |
| CLI can install a cluster control plane | Limit pilot kubeconfig access to a sandbox cluster and use `--profile minimal` unless demo tools are explicitly needed. |
| Agents can call powerful tools | Separate read-only agents from write-capable agents; do not bind apply/delete tools to read-only triage agents. |
| Secrets can be created by `kagent deploy` | Keep API keys out of Git, use placeholder docs here, and prefer external secret management for work adoption. |
| Direct CLI apply can bypass GitOps | Use CLI apply only in disposable sandbox clusters. For persistent environments, require generated YAML, MR review, and Flux reconciliation. |
| Version drift could break CRD examples | Pin CLI and chart versions for the pilot and validate CRDs against the installed kagent version. |
| Cost exposure from model calls | Route through approved provider endpoints and set budget/telemetry controls before team-wide use. |

## Recommended DevPod Pilot

Use the CLI in three stages.

1. CLI-only install inside DevPod.
   - No admin install on the laptop.
   - No cluster mutation.
   - Validate `kagent version`, `kagent help`, and command availability.

2. Local agent development.
   - Use `kagent init adk python {{AGENT_NAME}}`.
   - Use `kagent build` and `kagent run` for local testing if Docker is available in the DevPod.
   - Avoid real secrets in committed files.

3. Sandbox-cluster test.
   - Install kagent only into a non-production sandbox namespace.
   - Prefer `kagent install --profile minimal --namespace kagent`.
   - Use `kagent dashboard --namespace kagent` for a local port-forward.
   - For BYO agents, first run `kagent deploy . --env-file {{LOCAL_ENV_FILE}} --dry-run` and review the generated YAML.

## DevPod Install Path

The upstream installer supports non-root installation with `--no-sudo`, which installs the binary into `$HOME/bin`. The helper script in this repo wraps that path and pins the version.

```bash
./scripts/install-kagent-cli-devpod.sh
```

Override the version when needed:

```bash
KAGENT_VERSION=v0.9.6 ./scripts/install-kagent-cli-devpod.sh
```

If `$HOME/bin` is not on `PATH`, add it to the DevPod shell profile:

```bash
export PATH="$HOME/bin:$PATH"
```

The DevPod must have outbound HTTPS access to the upstream download endpoints used by the installer:

- `raw.githubusercontent.com`
- `api.github.com`
- `cr.kagent.dev`
- any GitHub release asset host reached by redirects from `cr.kagent.dev`

Then verify:

```bash
kagent version
kagent help
```

Expected current pilot baseline on 2026-06-10:

```text
kagent_version: 0.9.6
```

## Business-Case Position

Ask for approval in two tiers.

Tier 1: DevPod-only CLI approval.

- Scope: install `kagent` CLI in `$HOME/bin` inside DevPod.
- Purpose: agent development, dry-run manifest generation, sandbox dashboard access.
- Risk: low, because no workstation admin rights and no production cluster access are required.
- Evidence to collect: install transcript, version, generated dry-run manifests, time to scaffold/test one internal-style triage agent.

Tier 2: Managed cluster-side kagent service.

- Scope: platform-owned kagent installation managed by Helm/Flux with approved model provider, approved MCP tools, RBAC, admission controls, and observability.
- Purpose: SRE-facing UI/A2A/curl front door for triage, evidence collection, and governed remediation planning.
- Risk: medium, because tool permissions and model traffic must be governed.
- Evidence to collect: sandbox RBAC design, read-only/write-capable agent split, audit logs, token/cost telemetry, and GitOps deployment model.

## Decision

Proceed with a DevPod-only trial of the kagent CLI. Do not request broad production installation until the pilot proves:

- Non-root install works reliably in the DevPod image.
- The CLI can scaffold or dry-run deploy an agent without leaking secrets.
- Sandbox kagent can use a minimal profile and approved model provider.
- The platform can enforce the intended split between chat front doors and execution permissions.
- Persistent work adoption can be reconciled through GitOps rather than ad hoc CLI applies.
