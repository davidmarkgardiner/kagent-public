---
name: cluster-certification-runner
description: Run and interpret the uk8s cluster certification workflows. Use when asked to certify a cluster, run uk8s certification, or validate a freshly provisioned cluster.
---

# Cluster Certification Runner

The certification scripts already exist and are complete — this skill routes
to them and interprets their output. Do not re-derive the checks by hand.

## Scripts

All under `infra/kro-stack/certification/`:

| Script | Purpose |
|--------|---------|
| `deploy-certification.sh` | Deploy the certification WorkflowTemplates + RBAC to the target cluster |
| `example-run.sh` | Submit a certification run, watch it, and grep out the CERTIFICATION REPORT |

Read `infra/kro-stack/certification/README.md` and `QUICKSTART.md` for
parameters and prerequisites before running.

## Workflow

1. Confirm the target cluster/context with the user — certification submits
   Argo workflows to it.
2. Deploy (idempotent) and run:

   ```bash
   infra/kro-stack/certification/deploy-certification.sh
   infra/kro-stack/certification/example-run.sh
   ```

3. Interpret the `CERTIFICATION REPORT` output: every check line must PASS.
   For failures, investigate with the `aks-specialist` skill
   (`agents/skills/aks-specialist/scripts/aks-cert-check.sh` gives the quick
   sectioned health sweep) and report root cause + remediation, not just the
   failing line.

## For a quick non-Argo health sweep

When a full certification run is overkill, use:

```bash
agents/skills/aks-specialist/scripts/aks-cert-check.sh [--context CTX] [--json]
```
