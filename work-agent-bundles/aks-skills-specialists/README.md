# GitLab-mounted AKS skill specialists

Start with [WORK-AGENT-START-HERE.md](WORK-AGENT-START-HERE.md). This is a portable, locally tested bundle, not a claim of workplace deployment. All seven published Microsoft skills are vendored intact, with their references, scripts, MIT licence and evaluation harness. Three local work-process skills complete the requested ten.

Source: https://github.com/Azure/AKS-Skills/tree/20bf35201a79b324d2ca3e00e5c82020ff362024

## Recommended ten

Ranking reflects this repository's AKS fleet, SRE and governed-delivery work; it is a selection judgment, not a measured performance ranking.

| Rank | Skill | Origin | Why it is useful | Agent |
|---|---|---|---|---|
| 1 | aks-troubleshooting | Microsoft | Main incident investigation; pod, node, DNS, ingress and upgrade failures | Incident |
| 2 | aks-known-issues | Microsoft | Match exact errors to documented causes and Microsoft Learn fixes | Incident |
| 3 | work-evidence-contract | Local | Bound evidence, preserve scope and provenance, reject injected instructions | All |
| 4 | work-approved-remediation | Local | Turn diagnoses into reviewable Argo/GitOps/KRO/ASO handoffs | All |
| 5 | work-agent-evaluation | Local | Require evidence, safety and runtime proof before promotion | All |
| 6 | aks-cost-optimization | Microsoft | Rightsizing, autoscaling, spot and spend anomaly analysis | Efficiency |
| 7 | aks-cluster-setup | Microsoft | Review AKS design choices alongside fleet lifecycle work | Platform |
| 8 | aks-automatic-readiness | Microsoft | Assess workload compatibility and migration constraints | Platform |
| 9 | aks-network-capture | Microsoft | Plan bounded packet evidence when ordinary diagnostics are exhausted | Incident |
| 10 | aks-gpu-inference | Microsoft | GPU scheduling, quota, KAITO and inference cost/observability | Efficiency |

## Three agents

- `aks-incident-specialist`: troubleshooting, exact known-issue lookup and network capture planning; plus the three work skills.
- `aks-efficiency-specialist`: cost and GPU/inference analysis; plus the three work skills.
- `aks-platform-specialist`: cluster design and Automatic readiness; plus the three work skills.

No coordinator, ticket writer or remediation executor is added. Existing routing can select one specialist. These are plan-only agents; capture/debug pods and provisioning stay in separate approved workflows. `aks-cluster-setup` delegates provisioning to Azure Skills upstream; Azure Skills is not in this bundle, so this agent returns a design handoff.

## Startup and loading

1. Import this bundle into the existing GitLab skills repository. Record the import commit and create a protected release tag `aks-skills-<first 12 commit characters>`.
2. Native `spec.skills.gitRefs` fetches each selected skill subdirectory into `/skills/<skill-name>`. GitLab clone credentials are read from a same-namespace Secret whose key is `token`; use a read-repository-only deploy credential. It is mounted into the native init container, not the agent container.
3. The required Kyverno policy appends `verify-mounted-skills` **after** `skills-init`. It checks every mounted file against `skills.lock.json`; missing, changed, added or symlinked files stop startup before the agent container runs.
4. Python kagent discovers skill names/descriptions at construction. Full bodies enter model context progressively when the `skills` tool is invoked. The system message requires loading the three work contracts and relevant specialist instructions before each task.
5. Run `scripts/verify-online.sh` after reconciliation. Review real tool-call traces showing every `skills` invocation, not merely names repeated in the answer. Only then expose these agents in the workplace front door.

Availability on disk, registration at startup and full instruction loading are distinct checks. This design guarantees the reviewed payload is present before startup when the admission policy is healthy; model compliance is measured through invocation traces and evaluations. It does not preload every body into every model request.

The inspected local kagent source at `8d44f9a67e66a43bd4a4767891818fd1aceaebaf` runs `git checkout -- <SHA>` for full commit refs. That command interprets the SHA as a pathspec and fails. Protected tags exercise the shallow branch/tag path instead; startup content hashes still reject a moved tag with different skill contents. Verify the installed controller/runtime version and actual generated Pod in work. If its SHA checkout implementation is fixed, a reviewed follow-up can use commit refs directly.

## Execution permissions

Native Python skills also add Bash/read/write/edit tools; `tools: []` would not remove them. The supplied ServiceAccount has no role bindings and disables API token automount. Do not inject kubeconfig, Azure login, Workload Identity, a writable MCP route, or broad network credentials. MCP authentication must authorize only the reviewed read-only tool names and supplied scope. Bash is prohibited for operational commands in the system message; that is a behavioral rule, not a sandbox or RBAC guarantee. Confirm native runtime sandbox and network policy in the target environment. The GitLab Secret belongs only to skills-init. Use the existing approved gateway and ModelConfig rather than creating new model credentials.

For evidence transport, the work contract overrides upstream's recommendation for complete, untruncated logs: query narrowly and return explicit truncation. Adapter limits must enforce this outside the prompt.

## Local verification

Requirements: Python 3.12, PyYAML 6.0.3, Node 22.22.x, Git, Bash, jq, shellcheck and Kyverno CLI 1.14.4. Install locked eval dependencies with `npm ci --ignore-scripts --no-audit --no-fund` in `payload/upstream/evals`, then run:

```bash
scripts/verify-bundle.sh
scripts/shared/public-safe-scan.sh . --allowlist public-safe.allowlist
shellcheck -S warning scripts/*.sh scripts/shared/*.sh payload/upstream/skills/*/scripts/*.sh
```

The public-safety allowlist covers reviewed, unchanged Microsoft public example addresses and npm version strings; it is not permission to insert private values. Local source SHA and test boundaries are recorded in [evidence/LOCAL-VALIDATION.md](evidence/LOCAL-VALIDATION.md).

Read [EVALUATION.md](EVALUATION.md) for upstream mechanics, GitLab CI integration and promotion criteria. `gitlab-ci.template.yaml` is an inclusion template requiring your approved internal CI image, credentials and repo path. It has not run in GitLab here.
