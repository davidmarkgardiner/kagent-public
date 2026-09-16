# Workplace quick start

This is the short operator path. Use the full README and TEST-PLAN as the
acceptance authority.

## Pull only this folder at work

Before merge, pull the published review branch from our public work-bundles
repository:

```bash
git clone --branch cluster-health-daily-summary --single-branch \
  --filter=blob:none --sparse \
  https://github.com/davidmarkgardiner/kagent-work-bundles.git
cd kagent-work-bundles
git sparse-checkout set cluster-health-assessment-plan
cd cluster-health-assessment-plan
bash verify-all.sh
```

After the reviewed source change has been merged and mirrored to `main`, use:

```bash
git clone --filter=blob:none --sparse \
  https://github.com/davidmarkgardiner/kagent-work-bundles.git
cd kagent-work-bundles
git sparse-checkout set cluster-health-assessment-plan
cd cluster-health-assessment-plan
bash verify-all.sh
```

Do not put private values, tokens, hostnames or rendered workplace manifests
back into the public checkout.

## 1. Build the two internal images

Create an approved internal copy of Fox at pinned commit
`7c785b574c36f7100ae321ec0f880782dfead311`, apply and test
`FOX-STATE-ONLY-ADAPTATION.md`, then run:

```bash
workplace-bundle/scripts/build-fox-image.sh \
  /path/to/internal/autonomous-monitor \
  {{WORK_REGISTRY}}/platform/autonomous-monitor-state-only:{{BUILD_ID}} \
  {{WORK_REGISTRY}}/mirror/golang@sha256:{{GO_BUILDER_DIGEST}} \
  {{WORK_REGISTRY}}/mirror/distroless-static@sha256:{{RUNTIME_DIGEST}}

workplace-bundle/scripts/build-assessor-image.sh \
  {{WORK_REGISTRY}}/platform/cluster-health-assessor:{{BUILD_ID}}
```

Run tests, vulnerability/licence scans and SBOM generation, push only to the
internal registry, and record returned registry digests. The assessor image
contains the B1 collector, daily controller and fixed GitLab writer.

## 2. Point the manifests at approved dependencies

Copy `values.example.json` to a private location. Fill in:

- the two new internal image digests plus approved Vector/toolbox digests;
- cluster identity and the worker AKS-MCP target;
- Kafka broker/topic/consumer group, port and exact egress CIDR;
- worker/manager API CIDRs, agentgateway Service/Gateway details, the internal
  listener name, Service and target ports, management OIDC issuer/JWKS and a dedicated
  Kubernetes projected-token `api://` audience;
- the dedicated AKS-MCP ServiceAccount, instance label and port; disable its
  chart-created broad RBAC;
- GitLab HTTPS origin, SRE project and exact egress CIDR;
- the exact Alloy event/log namespace count.

Keep `GITLAB_WRITE_ENABLED=false`. Deliver Kafka and GitLab credentials through
the existing approved Secret mechanism; do not put them in the values file.
Render and validate:

```bash
python3 workplace-bundle/scripts/render.py \
  --values /secure/path/cluster-health-values.json \
  --output-dir /secure/path/cluster-health-rendered

python3 workplace-bundle/scripts/verify.py

workplace-bundle/scripts/verify-live.sh \
  {{CLUSTER_CONTEXT}} {{CLUSTER_CONTEXT}} \
  /secure/path/cluster-health-rendered {{AKS_MCP_SERVER_NAME}}
```

Passing the same context twice is correct while one cluster represents both
worker and manager. If work separates them, stop and redesign the worker-side
MCP authentication and authorization boundary before deployment.

## 3. Deploy, connect and prove the path

Commit the rendered/adapted resources through the owning workplace GitOps
flow. Do not use an ad-hoc long-lived `kubectl apply` as the production owner.

Run:

```bash
workplace-bundle/scripts/verify-running.sh \
  {{CLUSTER_CONTEXT}} {{CLUSTER_CONTEXT}} \
  /secure/path/cluster-health-values.json
```

Then prove each boundary in order:

1. Fox collectors update state but make no Kafka connection.
2. B1 produces fresh five-minute snapshots.
3. Vector produces and a disposable consumer consumes the daily contract.
4. Many snapshots/restarts still produce one record for one UTC date.
5. No token/wrong audience returns 401 and the wrong ServiceAccount returns
   403 at agentgateway; the Workflow identity reaches only the fixed agent.
6. The dedicated MCP identity reads approved namespaces and nodes but is
   denied `default`, Secrets, ConfigMaps and all writes.
7. Argo creates one replay-safe Workflow only for an unhealthy record.
8. The Agent targets the worker alias and returns one bounded read-only summary.
9. In a disposable GitLab project, create the exact stable labels and enable
   `GITLAB_WRITE_ENABLED=true`; first unhealthy day creates one issue and the
   next updates it.
10. Remove the fault; the next daily record is healthy and invokes neither the
   Agent nor GitLab writer.

Only after the full soak and approval should the GitLab writer target the real
SRE project or the existing individual Alloy/Vector incident lane be reduced.
