# Work-agent start prompt

Implement this separate GitLab CI evaluation workflow in a non-production work
sandbox. Read README.md, contracts/PROTOCOL.md and CHECKLIST.md first. This is an
implementation handoff; scripts/gate.py is ready client code, but there is no
bridge/test executor deployment supplied. Do not report it as installed.

1. Inspect existing kagent/controller version and schemas, model route, GitLab
   version/tier, CI policy and runner setup, Istio Gateway and identity provider.
2. Choose one sandbox MR project and a separately protected evaluator project.
   Populate placeholders privately. Use target secret management for a GitLab
   read-only identity; grant no merge or repository-write tools to review agents.
3. Implement the durable evaluation bridge contract and reviewer/test-design
   Agent CRs against installed schemas. Use bounded MCP reads or bounded GitLab
   REST reads; never expose arbitrary project/URL selection. Retain A2A task IDs.
4. Implement a disposable, credential-free language-specific test executor.
   Demonstrate baseline expected assertion failure and candidate success.
5. Expose only bridge submit/status routes through the reviewed VirtualService.
   Configure TLS, CI OIDC authentication and project/ref authorization. Verify
   policy is enforced by the actual ingress or bridge workload. A route alone
   is not secure. Keep controller API private.
6. Place scripts/gate.py and ci/authority-job.yml in operator-owned evaluator
   Git. Choose a digest-pinned approved Python image with target CA roots.
   Resolve upstream project/MR/current SHA through GitLab API before invocation;
   do not use downstream CI_COMMIT_SHA. Validate CI YAML on the actual GitLab.
7. Configure a mandatory gate that MR authors cannot remove, and protected-branch
   merge controls. Keep human approval separate. If the GitLab tier cannot
   enforce an external gate/CI policy, state the blocker; do not present a
   removable include as enforcement. Prove the latest head is checked.
8. Run every CHECKLIST.md target case and capture evidence in evidence/RUN.md.
   Begin with a deliberately broken change, then a corrected change. No auto
   merge, deployment, release or public publishing is authorized by this bundle.
9. Package the completed target manifests, application code and evidence through
   the existing GitOps delivery process. Record unresolved gaps explicitly.
