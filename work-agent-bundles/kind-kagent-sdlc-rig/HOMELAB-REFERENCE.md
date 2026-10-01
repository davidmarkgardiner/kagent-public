# Home-lab reference for sequential workplace installation

Use this with [WORK-AGENT-START-PROMPT.md](WORK-AGENT-START-PROMPT.md).
The completed run is [RUN-2026-10-01.md](evidence/RUN-2026-10-01.md).
This file supplies exact lab identities, receipts and repeatable command shapes;
it is not an instruction to overwrite the work environment with lab settings.
Replace context/project/model/Secret/endpoint values with discovered work values.
Secret **names and keys** are recorded; real Secret values are never included.
Read-only inspection on 1 October confirmed the wiring below. No new issue or
agent turn was executed when preparing this reference.

## Recorded environment and wiring

| Item | Verified Proxmox lab value |
|---|---|
| Context / namespace | `proxmox-k8s` / `sdlc-rig` |
| Kubernetes / kagent | 1.31.14 / controller 0.7.13 |
| Planner / workers | `sdlc-pm`; `sdlc-builder`, `sdlc-tester`, `sdlc-reviewer`, `sdlc-worker-echo` |
| Active PM ModelConfig | `sdlc-work-model`, provider `OpenAI`, model `kimi-for-coding` |
| Model client Secret / key | `agentgateway-client-key` / `api-key` |
| GitLab Secret / key | `gitlab-project-token` / `token` |
| MCP Deployment / RemoteMCPServer | `sdlc-gitlab-mcp` / `sdlc-gitlab-mcp`; 14 discovered tools |
| Poller / ServiceAccount / Lease | `sdlc-board-poller` / `sdlc-board-poller` / `sdlc-board-poller` |
| Settings / Python ConfigMaps | `sdlc-rig-settings` / `sdlc-board-poller-code` |
| Schedule / concurrency / Lease | `*/2 * * * *` / `Forbid` / 240 seconds |
| GitLab sandbox | `davidmarkgardiner/debt-payoff-calculator-agentic-factory`, project ID 85221780 |
| Fresh demo parent / child / MR | #53 / #54 / draft !14 |
| Current demo commit | `96c281d1765fc15f2f6ef32db15e80f6f091d75d` |
| Pipeline / job / review note | 2902446117 / 16875271522 / 3939955463 |

The Mac context `kind-agent-cage-health` was separately verified for kagent/model
routing; it does not have the SDLC rig. Do not point independent cluster pollers
at the same project queue: the Lease coordinates only within one cluster.

## YAML excerpts: compare with the installed work setup

These are selected fields from the live lab resources, not complete applyable
manifests. Endpoint and credential values are explicit placeholders. Obtain
complete target manifests with `render-work-bundle.py` and the discovered private
profile; inspect/dry-run them before installation. The original raw lab YAML uses
`kimi-gateway` and differs from the hardened rendered live deployment: do not
blindly apply `00-foundation.yaml` or `30-board-cronjob.yaml` to reproduce it.

```yaml
apiVersion: kagent.dev/v1alpha2
kind: ModelConfig
metadata:
  name: sdlc-work-model
  namespace: sdlc-rig
spec:
  provider: OpenAI
  model: kimi-for-coding
  apiKeySecret: agentgateway-client-key
  apiKeySecretKey: api-key
  openAI:
    baseUrl: '{{EXISTING_MODEL_BASE_URL}}'
    timeout: 300
    maxTokens: 2048
```

```yaml
# Schema example only: provision values through the target secret mechanism.
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-project-token
  namespace: sdlc-rig
type: Opaque
stringData:
  token: '{{EXISTING_GITLAB_TOKEN_PROVISIONED_SECURELY}}'
```

Both the live MCP container and poller use this exact reference:

```yaml
env:
  - name: GITLAB_TOKEN
    valueFrom:
      secretKeyRef:
        name: gitlab-project-token
        key: token
```

The live PM references `sdlc-work-model` and includes Agent tools for the four
workers. This selected builder tool illustrates actual A2A role delegation:

```yaml
# Inside spec.declarative of Agent/sdlc-pm
modelConfig: sdlc-work-model
tools:
  - type: Agent
    agent:
      apiGroup: kagent.dev
      kind: Agent
      name: sdlc-builder
      namespace: sdlc-rig
```

The hardened live poller uses its narrow Lease ServiceAccount. Its token automount
is true so it can use the Kubernetes API for that Lease; worker/build permissions
are separate. Do not replace it with cluster-admin or confuse it with the
CI build ServiceAccount, whose token automount is false.

```yaml
# Selected CronJob and Job pod fields, not a complete resource
spec:
  schedule: '*/2 * * * *'
  concurrencyPolicy: Forbid
  suspend: false  # live lab after proof; KEEP TRUE during work installation
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: sdlc-board-poller
          automountServiceAccountToken: true
          containers:
            - name: poller
              image: docker.io/library/python@sha256:236173eb74001afe2f60862de935b74fcbd00adfca247b2c27051a70a6a39a2d
              env:
                - name: BOARD_LEASE_REQUIRED
                  value: 'true'
                - name: PM_A2A_URL
                  value: '{{DISCOVERED_PM_A2A_URL_WITH_TRAILING_SLASH}}'
```

For a private discovered work profile, the complete render/dry-run commands are:

```bash
python3 render-work-bundle.py --profile '{{PRIVATE_WORK_PROFILE_JSON}}' \
  --output '{{PRIVATE_WORK_RENDERED_YAML}}'
kubectl --context '{{WORK_CONTEXT}}' -n sdlc-rig apply --dry-run=server \
  -f '{{PRIVATE_WORK_RENDERED_YAML}}'
```

The namespace and target Secrets must already exist for server dry-run. Preflight
checks references/readiness without sending a model or GitLab request; it was
repeated successfully while preparing this reference. It does not replace the
real checkpoint calls:

```bash
KUBE_CONTEXT=proxmox-k8s MODEL_CONFIG_NAME=sdlc-work-model \
  GATEWAY_NAMESPACE=agentgateway-system GATEWAY_DEPLOYMENTS='agentgateway agent-gw' \
  KAGENT_NAMESPACE=kagent KAGENT_CONTROLLER_DEPLOYMENT=kagent-controller \
  bash preflight.sh
```

## Checkpoint 1: real GitLab issue access

During the completed run, the installer created parent #53 unlabelled via GitLab
REST, and a real PM GitLab MCP turn read its exact title and labels before intake.
Do not claim the installer-side MCP create call was separately proven by that
run. Prove create and read through the work MCP at this checkpoint.
The bundled tool schemas are:

```json
{"tool":"gitlab_create_issue","arguments":{"title":"SDLC demo: record README verification evidence","description":"{{DEMO_CRITERIA_WITH_UNIQUE_RUN_MARKER}}"}}
{"tool":"gitlab_get_issue","arguments":{"iid":53}}
```

For work installation, use the IID returned by creation, not lab IID 53. The
create tool does not accept labels. Derive the criteria from the work repository;
use [DEMO-ISSUE-TEMPLATE.md](DEMO-ISSUE-TEMPLATE.md) as a starting point.

This read-only lab command checks the recorded issue using the MCP pod's existing
Secret-backed environment. It never prints the token. Run from a trusted terminal;
use the equivalent discovered Deployment/context for the work environment.

```bash
kubectl --context proxmox-k8s -n sdlc-rig exec -i deployment/sdlc-gitlab-mcp -- python3 - <<'PY'
import os, json, urllib.parse, urllib.request
api = os.environ.get('GITLAB_API_URL', 'https://gitlab.com/api/v4').rstrip('/')
project = urllib.parse.quote(os.environ['GITLAB_PROJECT_PATH'], safe='')
request = urllib.request.Request(
    f'{api}/projects/{project}/issues/53',
    headers={'Authorization': 'Bearer' + ' ' + os.environ['GITLAB_TOKEN']})
with urllib.request.urlopen(request, timeout=20) as response:
    issue = json.load(response)
print(json.dumps({key: issue[key] for key in ['iid', 'title', 'labels', 'web_url']}))
PY
```

Discover wiring without dumping Secret values:

```bash
kubectl --context proxmox-k8s -n sdlc-rig get deployment sdlc-gitlab-mcp -o json |
  jq '.spec.template.spec.containers[] | {name, secretRefs: [.env[]? | select(.valueFrom.secretKeyRef) | {name, ref: .valueFrom.secretKeyRef}]}'
kubectl --context proxmox-k8s -n sdlc-rig get secret gitlab-project-token -o json |
  jq '{name: .metadata.name, namespace: .metadata.namespace, keys: (.data | keys)}'
```

## Checkpoints 2–3: labels, pickup and planner

Preserve existing labels, then add `sdlc-rig-poc` and `agent:plan`. The installer
MCP update replaces the label array, so read/merge first; REST can use add_labels.
Do not use this example to relabel the already Accepted lab issue #53.

```json
{"tool":"gitlab_update_issue","arguments":{"iid":123,"labels":["{{PRESERVED_EXISTING_LABEL}}","sdlc-rig-poc","agent:plan"]}}
```

`board_poller.py` queries open issues with `labels=sdlc-rig-poc`, then requires
exactly one recognized `agent:*` state label. Pickup and PLAN occur in the same
Job, in that order. The completed run's 17:38 UTC scheduled Job was
`sdlc-board-poller-29847938`; the source-defined pickup receipt shape for the fresh parent is:

```json
{"child":null,"event":"picked","iid":53,"state":"agent:plan"}
```

PLAN created exactly child #54 and advanced the parent to Build. To inspect lab
runtime status without executing another turn:

```bash
kubectl --context proxmox-k8s -n sdlc-rig get agents,remotemcpserver,deployments
kubectl --context proxmox-k8s -n sdlc-rig get cronjob sdlc-board-poller
kubectl --context proxmox-k8s -n sdlc-rig get jobs --sort-by=.metadata.creationTimestamp
```

Historical Jobs may be removed by retention. The issue notes and committed run
record remain the durable evidence. For a new work supervised run, suspend the
CronJob, confirm there is no active poller, then create ONE uniquely named Job:

```bash
kubectl --context '{{WORK_CONTEXT}}' -n sdlc-rig patch cronjob sdlc-board-poller \
  --type merge -p '{"spec":{"suspend":true}}'
kubectl --context '{{WORK_CONTEXT}}' -n sdlc-rig create job '{{UNIQUE_CHECKPOINT_JOB}}' \
  --from=cronjob/sdlc-board-poller
kubectl --context '{{WORK_CONTEXT}}' -n sdlc-rig logs -f 'job/{{UNIQUE_CHECKPOINT_JOB}}'
kubectl --context '{{WORK_CONTEXT}}' -n sdlc-rig wait \
  --for=condition=complete 'job/{{UNIQUE_CHECKPOINT_JOB}}' --timeout=240s
```

If waiting fails, inspect the Job/PM evidence and retry hold; do not create another
Job blindly. CronJob Forbid does not serialize manually created Jobs; the shared
Lease and the one-at-a-time discipline are both necessary.

## Checkpoint 4: actual A2A delegation and branch commit

The source PM instructions require only the requested BOARD_STAGE: PLAN creates
the child without calling workers; BUILD calls `sdlc-builder` once; TEST calls
`sdlc-tester`; REVIEW calls `sdlc-reviewer`. Read the full instructions in
[10-a2a-agents.yaml](10-a2a-agents.yaml) and
[20-delivery-workers.yaml](20-delivery-workers.yaml), and compare installed CRs.

For a harmless routing smoke, the bundled helper owns the trailing slash,
JSON-RPC envelope and temporary port-forward. This is a repeatable command,
not a substitute for real BUILD evidence:

```bash
bash tools/kagent-a2a-invoke.sh --context proxmox-k8s --controller-ns kagent \
  --ns sdlc-rig --agent sdlc-pm --timeout 90 \
  --text 'Delegate to sdlc-worker-echo with nonce {{FRESH_NONCE}}; report its actual reply.'
```

The 1 October smoke used nonce `LIVE-20261001-1836` and completed in 13 seconds.
The real BUILD completed in 33.9 seconds at 17:40 UTC, creating branch
`agentic/sdlc-rig-53` and SHA `96c281d1765fc15f2f6ef32db15e80f6f091d75d`.
Independent comparison found exactly README.md changed; removing the one new
Verification bullet reproduced every existing README line.

## Checkpoints 5–6: tests, review, acceptance and idle

| Stage | Actual receipt from the 1 October run |
|---|---|
| CI | Pipeline 2902446117, job 16875271522: one test, one pass, zero failures/skips/cancellations, same full SHA |
| TEST | 17:52 UTC; A2A completed in 31.1 seconds; parent note records tester PASS for this pipeline/SHA |
| MR | 17:54 UTC; A2A completed in 16.9 seconds; exactly one open draft MR !14 at this SHA |
| REVIEW | 17:56 UTC; A2A completed in 43.9 seconds; bot note 3939955463 |
| ACCEPT | 17:58 UTC; A2A completed in 10.0 seconds; parent moved from agent:review to agent:accepted |
| Idle | 18:00 UTC Job sdlc-board-poller-29847960 logged idle; Lease holder and renewTime cleared |

Exact reviewer marker/verdict:

```text
<!-- sdlc-rig-review parent=53 sha=96c281d1765fc15f2f6ef32db15e80f6f091d75d -->
REVIEW_VERDICT: PASS
```

Exact acceptance and idle log receipts:

```json
{"completed":true,"elapsed_s":10.0,"event":"a2a","reply_chars":348,"stage":"ACCEPT"}
{"event":"transition","iid":53,"new":"agent:accepted","old":"agent:review"}
{"event":"idle"}
```

CI initially had no assigned runner. The dedicated project-locked runner 56962285
picked up the same job; [CI-RUNNER-SETUP.md](CI-RUNNER-SETUP.md) and
[ci-runner-values.example.yaml](ci-runner-values.example.yaml) provide the tested
chart 0.93.0 / Runner 19.4.0 setup. Its auth Secret is `sdlc-ci-runner-auth` in
`sdlc-ci-runner`, keys `runner-token` and `runner-registration-token` (the latter
empty for this workflow). The build ServiceAccount is `sdlc-ci-build`, with no
API-token automount. The runner credential is separate from the agent GitLab PAT.

Evidence links (lab access may be required):

- Parent: https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/work_items/53
- Child: https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/work_items/54
- Pipeline: https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/pipelines/2902446117
- Test log: https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/jobs/16875271522
- Draft MR: https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/merge_requests/14
- Board: https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/boards/11652698

These receipts prove the bounded lab orchestration flow. The tester marker still
records PM text, not an independent generated-test artifact. No GitLab MR was
merged. Repeat each checkpoint in the work environment before claiming it works.
