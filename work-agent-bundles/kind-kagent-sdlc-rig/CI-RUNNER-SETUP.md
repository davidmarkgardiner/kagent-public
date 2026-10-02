# Sandbox CI runner prerequisite

Prefer the work environment's existing approved runner. A GitLab PAT and MCP
connection do not provide a CI executor. Verify a current target-branch pipeline
actually completes before admitting a demo issue.

The 2026-10-01 Proxmox rehearsal needed a dedicated runner: the hosted job stayed
pending without an assigned runner. The supplied values reproduce the tested
Kubernetes executor configuration, using chart 0.93.0 / Runner 19.4.0.
This is ordinary repository CI; it does not implement the separate agent quality
bridge or generated-test execution gate.

## Install when no suitable runner exists

1. Discover the exact sandbox project and approved GitLab URL. Create a project
   runner through GitLab's current UI/API (`POST /user/runners`), with an installer
   identity authorized to create runners. The rig's Developer project token is
   not assumed to have this permission. Set `runner_type=project_type`, `project_id` to the target project ID,
   locked=true, run_untagged=true and maximum_timeout=600. Accepting untagged jobs
   is appropriate only for this dedicated sandbox; workplace jobs may require tags.
2. Securely provision the returned runner authentication token into Secret
   `sdlc-ci-runner-auth` in dedicated namespace `sdlc-ci-runner`. Its keys are
   `runner-token` and an empty `runner-registration-token`. Use the target secret
   manager or an in-memory installer operation. Do not put the token in Helm
   values, terminal output, a public manifest, history or this repository.
3. Review `ci-runner-values.example.yaml` against the installed chart, target CA,
   proxy, image policy, network isolation and scheduling requirements. Change the
   public GitLab URL for the target. Keep the manager's RBAC namespace-scoped and
   builds on their separate ServiceAccount with token automount disabled.
4. Deliver the chart through the target's approved GitOps/Helm process. For the
   lab, the equivalent command was:

```bash
helm upgrade --install sdlc-ci-runner gitlab-runner \
  --repo https://charts.gitlab.io --version 0.93.0 \
  --kube-context '{{KUBE_CONTEXT}}' --namespace sdlc-ci-runner \
  --values ci-runner-values.example.yaml --wait --timeout 5m
```

5. Verify GitLab reports the runner online and assigned only to the sandbox.
   Inspect an actual build pod: nonprivileged, no privilege escalation, separate
   build ServiceAccount, automountServiceAccountToken=false, and no agent/provider
   secret mounts. Require a current-SHA successful pipeline and inspect test
   totals. Ready manager pods alone are insufficient.

This runner allows one concurrent job and caps build resources. Its manager can
manage pods and job secrets within its own namespace; builds have no Kubernetes
API permission. Those controls are not a complete hostile-code sandbox. Apply
workplace isolation policy before admitting untrusted projects or forks. Avoid
sharing the namespace with platform credentials.

Official references: [chart configuration](https://docs.gitlab.com/runner/install/kubernetes_helm_chart_configuration/),
[new runner creation](https://docs.gitlab.com/ci/runners/new_creation_workflow/),
and [runner creation API](https://docs.gitlab.com/api/users/#create-a-runner-linked-to-a-user).
