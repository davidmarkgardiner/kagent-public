# Local validation receipt — 2026-10-06

Scope: isolated public-source worktree, no workplace deployment, model calls, Azure operations or connected GitLab writes.

- Microsoft upstream: `20bf35201a79b324d2ca3e00e5c82020ff362024`; full tracked snapshot copied unchanged and verified against `upstream.lock.json`. MIT attribution preserved.
- Local kagent source inspected: `8d44f9a67e66a43bd4a4767891818fd1aceaebaf`; verified Git auth Secret key `token`, native fetch/init behavior, Python discovery and additional Bash/file tools. This is source evidence, not an installed-runtime claim.
- Native full-SHA checkout command reproduced a pathspec failure. Bundle uses reviewed protected GitLab tags plus complete skill-content hashes.
- Ten bundle regression tests passed: complete inventory and file hashes for all three specialists; corrupt/missing/unexpected content blocks startup; source-snapshot integrity; invalid refs/URLs/paths/images rejected; promotion rejects empty/failed/error results; rendered manifests; evaluation case/config and custom-assertion resolution; Kyverno mutation order and wrong-service-account denial.
- Kyverno CLI 1.14.4: synthetic valid Pod passes both rules; init order is skills-init then verify-mounted-skills; synthetic wrong ServiceAccount fails admission validation. No cluster admission was tested.
- Microsoft contract lint: seven skills pass; 52 linter self-tests pass; seven backend-selection cases pass. Nine script-mode warnings before staging resolved after indexing source executable modes.
- Vally agentic-spec lint passes (two specs). This does not execute Copilot or a model.
- Autoscaler assertion regression: three cases pass.
- Packet capture injection/security and retrieval regression tests pass using upstream shims. Readiness redaction regressions pass; no live cluster was accessed.
- GitLab import tested in a synthetic local Git checkout: committed bundle source copied, clean commit created, dependencies excluded and existing destination rejected. No GitLab service contacted.
- Shellcheck at warning level passes for local, shared and upstream skill shell scripts.
- Public-safety scanner passes with narrowly documented exclusions for unmodified public Microsoft example addresses and npm version strings. Gitleaks directory scan reports no leaks.
- Host Node was v24.15.0 for these local checks. Upstream CI requires Node >=22.22.0 <23; the GitLab CI runner requirements preserve that supported range. Re-run in the approved runner before workplace promotion.

Pending evidence: intended GitLab repository and authenticated import (configured GitLab auth returned HTTP 401); CI runner/credentials; target CRD and admission webhook readiness; generated Pod mount/auth boundaries; bad-credential startup canary; actual runtime skill invocation traces; model-backed quality/routing/baseline/Copilot runs; lower-environment AKS/MCP scenarios and token telemetry.

Unmodified upstream whitespace findings are retained for source integrity; local additions pass whitespace checks.

No live performance, token savings, MTTR improvement or production readiness is claimed.
