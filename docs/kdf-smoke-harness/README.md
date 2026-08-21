# Kubernetes Delivery Factory — Smoke Harness

## What this is

A disposable, fully-observable smoke test harness that validates a Kind cluster
endpoint before running any Kubernetes Delivery Factory (KDF) workload. It
creates short-lived, resource-limited test resources labelled specifically for
this run, observes their health, gathers evidence, then removes everything it
created.

## Authorised target

| Field | Value |
|---|---|
| Kubeconfig | supplied via `KUBECONFIG` env or `--kubeconfig` |
| Context | `kind-homelab` (hard-coded allowlist, non-negotiable) |
| Namespace | `kdf-smoke` (hard-coded allowlist, non-negotiable) |
| Evidence | `/tmp/kdf-smoke-<run-id>.*` — local filesystem only, never remote |

The harness **hard-refuses** any context or namespace that is not on this
allowlist. It also refuses API servers that are not local (localhost / 127.0.0.1)
to guarantee the smoke test never reaches into a production cluster.

## Safety properties

- **Fail-closed target validation** — context, namespace, API server host, and
  run-id format are all validated before any cluster call.
- **No Secret data** — logs and describe output are gathered but Secret keys
  are never read or emitted.
- **Run-scoped cleanup only** — the cleanup phase deletes only the exact
  generated ConfigMap, Deployment, and Service for this run. Each carries both
  `app.kubernetes.io/part-of=kdf-smoke-harness` and this run's
  `kdf.delivery/run-id` label; the final proof queries those labels for anything
  left behind.
- **Graceful termination** — the trap calls `kubectl delete --wait=true` with
  a 60-second timeout, so the 5-second pod grace period is always respected.
- **Dry-run / plan mode** — `--plan` validates all inputs and emits the
  manifest without creating anything.

## Resource footprint (per run)

All resources are created with strict resource requests/limits so they cannot
starve the node:

| Kind | Count | CPU request | Memory request | CPU limit | Memory limit |
|---|---|---|---|---|---|
| ConfigMap | 1 | — | — | — | — |
| Deployment | 1 | 10m | 32Mi | 100m | 64Mi |
| Pod | 1 | inherited | inherited | inherited | inherited |
| Service | 1 | — | — | — | — |

## Usage

### Prerequisites

```bash
# Verify kind-homelab context exists
kubectl --kubeconfig /path/to/kubeconfig config get-contexts

# Verify the kdf-smoke namespace exists
kubectl --kubeconfig /path/to/kubeconfig --context kind-homelab \
  get namespace kdf-smoke
```

### Plan mode (default — no cluster writes)

```bash
KUBECONFIG=/path/to/kubeconfig \
  bash scripts/kdf-smoke-harness.sh --plan
```

Exits 0 after printing the manifest and confirming all safety checks passed.

### Run mode

```bash
KUBECONFIG=/path/to/kubeconfig \
  bash scripts/kdf-smoke-harness.sh --run
```

Creates the test Deployment, observes readiness, gathers evidence, then
cleans up on exit.

### Options

| Flag | Default | Description |
|---|---|---|
| `--plan` | plan | Validate and print manifest only |
| `--run` | — | Execute the full smoke run |
| `--context NAME` | kind-homelab | Must be exactly `kind-homelab` |
| `--namespace,-n NAME` | kdf-smoke | Must be exactly `kdf-smoke` |
| `--kubeconfig PATH` | KUBECONFIG env | Path to kubeconfig file |
| `--evidence-dir DIR` | auto-temp | Directory for evidence files |
| `--run-id ID` | UTC timestamp | DNS-label-safe run identifier |
| `--timeout DURATION` | 120s | kubectl wait / rollout timeout |
| `--image IMAGE` | registry.k8s.io/e2e-test-images/agnhost:2.45 | Public test image |
| `--help` | — | Show full usage |

## Evidence files

Each run writes the following files under `--evidence-dir` (default
`/tmp/kdf-smoke-<run-id>.<random>/`):

| File | Contents |
|---|---|
| `run-metadata.txt` | mode, context, namespace, run_id |
| `manifest.yaml` | The exact manifest applied (run mode) |
| `before-nodes.txt` | Node allocatable/capacity at start |
| `before-namespace-resources.txt` | Namespace resources at start |
| `before-events.txt` | Namespace events at start |
| `apply.txt` | `kubectl apply` stdout |
| `rollout-status.txt` | `kubectl rollout status` stdout |
| `wait-available.txt` | `kubectl wait --for=condition=Available` stdout |
| `smoke-status.txt` | Live status of all labelled resources |
| `deployment-describe.txt` | Full deployment describe (no Secret data) |
| `pod-logs.txt` | Container logs, last 100 lines |
| `after-nodes.txt` | Node allocatable/capacity at end |
| `after-namespace-resources.txt` | Namespace resources at end |
| `after-events.txt` | Namespace events at end |
| `cleanup-delete.txt` | `kubectl delete` stdout for each resource |
| `cleanup-proof.txt` | Final `kubectl get` of labelled resources |

## Running the static checks

```bash
# YAML syntax check (no cluster access)
bash scripts/lint-yaml.sh

# Shellcheck (if available)
shellcheck scripts/kdf-smoke-harness.sh
```

## Reproducing the test evidence

```bash
# 1. Verify cluster readiness
kubectl --context kind-homelab get namespace kdf-smoke

# 2. Run plan mode first
KUBECONFIG=/path/to/kubeconfig \
  bash scripts/kdf-smoke-harness.sh --plan

# 3. Run the smoke
KUBECONFIG=/path/to/kubeconfig \
  bash scripts/kdf-smoke-harness.sh --run

# 4. Inspect evidence (replace run-id with actual)
RUN_ID=$(ls -td /tmp/kdf-smoke-* | head -1 | xargs basename)
echo "Evidence in /tmp/$RUN_ID"
cat /tmp/$RUN_ID/cleanup-proof.txt
```

## Adding the harness to a CI pipeline

```bash
- name: KDF smoke (kind-homelab)
  env:
    KUBECONFIG: "{{KUBECONFIG_SECRET}}"
  script: |
    set -euo pipefail
    # Pull the repo at the commit under test
    git clone https://github.com/<org>/<repo>.git /tmp/kdf
    cd /tmp/kdf
    git checkout "$COMMIT_SHA"

    # Static checks first
    bash scripts/lint-yaml.sh

    # Plan gate — must succeed before any cluster write
    bash scripts/kdf-smoke-harness.sh --plan

    # Run gate — evidence collected on success; cleanup runs on exit
    bash scripts/kdf-smoke-harness.sh --run

    # Archive evidence
    cp -r /tmp/kdf-smoke-* "$ARTIFACTS_DIR/"
```

## Extending the harness

To add a new smoke resource (e.g. a Job or additional Container):

1. Add the resource definition inside the `manifest()` function in
   `scripts/kdf-smoke-harness.sh`, mirroring the existing label pattern:
   ```yaml
   labels:
     app.kubernetes.io/part-of: kdf-smoke-harness
     kdf.delivery/run-id: "${RUN_ID}"
   ```
2. Ensure `automountServiceAccountToken: false` is set.
3. Add resource limits under `resources.requests` / `resources.limits`.
4. Do **not** add Secrets, ConfigMaps with sensitive keys, or any resource
   that may persist beyond the `--timeout` window.
5. Update `cleanup()` to capture any new resource kind in the delete/get loop.
6. Run `--plan` and `--run` end-to-end and verify `cleanup-proof.txt` shows
   all resources removed.
