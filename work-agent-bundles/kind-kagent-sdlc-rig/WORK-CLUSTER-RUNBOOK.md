# SDLC rig work-cluster transfer

This Git folder is a **non-production evaluation bundle** for one existing Kubernetes
cluster, one model route, and one dedicated GitLab sandbox project. It installs
a PM, builder, tester, reviewer, echo worker, fixed-project GitLab MCP, and an
annotated-board poller. The poller starts **suspended**. No manifest contains a
provider or GitLab token. No workplace deployment is claimed by this archive.

The lab proof and ticket links are in `evidence/2026-09-27-board-polling.md` and
`BOARD-POLLING-PRESENTATION.html`. In that proof, two GitLab parent issues
reached accepted with green CI, draft MRs, and reviewer notes. Their full runs
were supervised and manually accelerated. The new Lease and portable profile
were locally checked but have not had a workplace functional run.

## Inputs and boundaries

- A target kube context with kagent `kagent.dev/v1alpha2` Agent/ModelConfig and
  RemoteMCPServer CRDs, reachable kagent controller A2A endpoint, an existing
  agentgateway model route, and a worker node with capacity. Check the exact
  installed API schema before applying. The lab used kagent v0.7.13; a target
  version change needs a fresh canary.
- One **sandbox** GitLab project, a target branch, and 1–12 named files. A
  human must commit and verify `.gitlab-ci.yml` on the target branch before
  intake; the agent file profile and candidate diff checker reject CI changes. The
  project token belongs in a namespace Secret named `gitlab-project-token`,
  key `token`, scoped to that project with only the access the MCP calls need.
  The server exposes issue, branch, file, pipeline, draft MR, and note calls.
  It exposes no merge, delete, or project-settings tool. GitLab permission
  remains the outer bound. Keep protected branches and merge approvals in
  GitLab. The worker prompts and branch diff checker use the profile's file list.
- A model client Secret in `sdlc-rig` with the name and key declared in the
  profile. Its value is a target-local gateway client credential. The upstream
  provider credential stays in the existing gateway. Do not copy lab tokens.
- A digest-pinned Python image reachable from the target nodes. The included
  digest is an **observed lab amd64 image**, not a target image approval. Check
  architecture, registry trust, mirror, and pull policy before use.
- Namespace `sdlc-rig`, label `sdlc-rig.kagent.dev/worker=true`, board label
  `sdlc-rig-poc`, and branch prefix `agentic/sdlc-rig-` are fixed in this
  version. Use a dedicated namespace and project. Do not place a second copy
  against the same project without changing those identities and re-testing.
- Optional `ca_configmap` names a pre-provisioned ConfigMap with a **combined**
  CA bundle under `ca.crt`; it is mounted in the MCP and poller, and both use
  `SSL_CERT_FILE`. Optional `https_proxy` and `no_proxy` configure their
  outbound HTTPS calls. The renderer always bypasses the proxy for cluster DNS
  names; the poller's Kubernetes API call bypasses it directly. Keep proxy
  credentials out of the profile and provide target-specific `no_proxy` hosts.

## 1. Inspect and render offline

Use Python 3 with PyYAML, `kubectl`, `jq`, and `curl`. When cloning from Git,
pin the reviewed commit and run the checks below from this folder. A tar file
is optional; it was only a standalone handoff snapshot. If using the archive,
verify its `.sha256` sidecar and the extracted `MANIFEST.sha256` first.

```bash
cp work-profile.example.json work-profile.local.json
# Edit the local file for the sandbox project, model route, existing Secrets,
# target branch, approved files, image digest, PM URL and node policy.
python3 render-work-bundle.py --profile work-profile.local.json --output work-rendered.yaml
python3 -m unittest discover -s . -p 'test_*.py'
```

Keep `work-profile.local.json` and `work-rendered.yaml` outside source control.
The example uses `gitlab.example.invalid` and cannot perform a live GitLab
turn. Inspect the rendered YAML for the exact project path, GitLab API URL,
model route, allowed paths, namespace, Secrets, image, schedule, and
`CronJob.spec.suspend: true`. The renderer rejects unpinned images and unsafe
file paths. It emits 19 resources, including MCP ingress NetworkPolicy, and no
Secret object.

## 2. Target preflight

Set `KUBE_CONTEXT` to the **work sandbox** context and confirm its identity.
These checks are read-only except the server dry-run, which does not persist
the objects. Do not pipe a manifest to `apply` until the context is confirmed.

```bash
kubectl config current-context
kubectl --context "$KUBE_CONTEXT" cluster-info
kubectl --context "$KUBE_CONTEXT" get crd agents.kagent.dev modelconfigs.kagent.dev remotemcpservers.kagent.dev
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -A | grep -E 'kagent|agentgateway'
kubectl --context "$KUBE_CONTEXT" apply --dry-run=client -f work-rendered.yaml
```

Confirm the target worker has the `sdlc-rig.kagent.dev/worker=true` label and
room for the five agent pods, MCP, and poller. `allow_control_plane` should
stay `false` in the profile unless target policy explicitly permits it.
Check target DNS/TLS and network policy from pods to GitLab, model gateway,
kagent A2A, and Kubernetes API. For private GitLab, arrange trusted CA roots
for the MCP and poller via the optional combined CA bundle. Confirm the CNI
enforces NetworkPolicy and that agent pods carry the expected
`app.kubernetes.io/name` labels before relying on MCP ingress isolation.
Check the target's Secret provisioning path and RBAC policy. The poller's
ServiceAccount gets only `get` and `update` for its named Lease. It needs an
in-pod token to use that Lease; the other pods do not need a Kubernetes token.

## 3. Install suspended and verify execution

Create the dedicated namespace first if it does not exist. Provision the two
Secrets through the target's approved secret-management path. Never put token
values in commands, manifests, shell history, logs, or the archive. Apply the
reviewed manifest, then check scheduling and endpoints:

```bash
# Create sdlc-rig through the target namespace process first.
kubectl --context "$KUBE_CONTEXT" apply -f work-rendered.yaml --dry-run=server
# Provision the two Secrets and optional CA ConfigMap through target processes.
kubectl --context "$KUBE_CONTEXT" apply -f work-rendered.yaml
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig get agent,modelconfig,remotemcpserver,deploy,svc,cronjob,lease
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig get pods -o wide
GATEWAY_NAMESPACE=agentgateway-system GATEWAY_DEPLOYMENTS='agentgateway agent-gw' \
  MODEL_CONFIG_NAME=sdlc-work-model KUBE_CONTEXT="$KUBE_CONTEXT" bash preflight.sh
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig auth can-i get lease/sdlc-board-poller \
  --as=system:serviceaccount:sdlc-rig:sdlc-board-poller
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig auth can-i update lease/sdlc-board-poller \
  --as=system:serviceaccount:sdlc-rig:sdlc-board-poller
```

Pod Ready is only a readiness check. Invoke the PM and echo worker with a
unique nonce, and verify the PM returns the same nonce through its delegated
worker turn:

```bash
bash tools/kagent-a2a-invoke.sh --context "$KUBE_CONTEXT" --ns sdlc-rig \
  --agent sdlc-pm --text 'Delegate echo to sdlc-worker-echo. Return nonce WORK-CANARY-001.' --json
```

Check that the MCP can read the intended project through a real agent turn;
verify the returned issue or file directly in GitLab. Keep the CronJob
suspended. Create one narrow canary parent issue with labels `sdlc-rig-poc`
and `agent:plan`, and an acceptance criterion involving only approved paths.
Start a manual poller Job (unique name), inspect its logs and resulting GitLab
artifacts, then repeat one Job at a time until accepted or blocked:

```bash
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig create job \
  --from=cronjob/sdlc-board-poller sdlc-board-canary-001
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig logs job/sdlc-board-canary-001
```

Never start the next manual Job until the previous Job has finished. The
shared Lease prevents overlapping scheduled and manual turns when all Jobs
use this rendered profile. If a holder is stale, wait for its 240-second
expiry and check no Job is active before retrying. Do not delete or force a
held Lease as routine recovery. The holder timeout exceeds the Job's
210-second active deadline. Kubernetes Lease updates use resource-version
conflict control; verify this behavior in the target environment.

Acceptance requires independently checking exactly one child, a branch whose
diff stays within allowed files, a successful pipeline on the branch's current
SHA, an open **draft** MR on that SHA, a reviewer PASS note naming the parent
and SHA, and parent `agent:accepted`. Verify an induced failed-CI or requested
changes case routes to `agent:changes` and returns after repair. The poller
does not merge. Use at least two narrow issues in an unattended scheduled soak
before treating this as repeatable in the workplace.

Only after the canary passes, enable the schedule:

```bash
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig patch cronjob sdlc-board-poller \
  --type=merge -p '{"spec":{"suspend":false}}'
```

Observe at least two scheduled polls, including an idle poll. To pause intake
or investigate, set `suspend:true`; this does not stop an already running Job.
Wait for active Jobs to finish. Record issue/MR/pipeline URLs, image digests,
CRD/controller versions, pod logs, and actual resource usage as target evidence.

## Rollback and promotion

First suspend the CronJob and wait for active Jobs. Revoke its project token
through the target secret-management process if access must end. Remove the
dedicated `sdlc-rig` namespace only after checking for work artifacts that
must be retained. Draft MRs and branches in GitLab are separate artifacts and
need a deliberate owner decision; this bundle does not merge or delete them.

Promotion beyond this sandbox requires target-specific authorization policy
for the GitLab MCP, network policy, credential rotation, observability, image
provenance, retention, and an owner-controlled merge gate. The lab evidence
does not certify those controls or general software quality.
