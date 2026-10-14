#!/usr/bin/env bash
# Runtime smoke only. The work agent adds real-model and disconnected-delivery receipts.
set -euo pipefail
umask 077
root=$(cd "$(dirname "$0")" && pwd)
: "${PROOF_KUBECONFIG:?Set the dedicated evaluation kubeconfig}"
: "${PROOF_ROUTER:?Set the running local router port-forward URL}"
agent_ns=${PROOF_AGENT_NAMESPACE:-kagent}
agent_name=${PROOF_AGENT_NAME:-substrate-stock-proof}
pool=${PROOF_WORKER_POOL:-kagent-default}
system_ns=${PROOF_SYSTEM_NAMESPACE:-ate-system}
full_template=${PROOF_FULL_TEMPLATE:-proof-counter-full}
data_template=${PROOF_DATA_TEMPLATE:-proof-counter-data}
run_id=${PROOF_SMOKE_RUN:-$(date -u +%Y%m%d%H%M%S)-$$}
out="$root/receipts/smoke-$run_id"
test ! -e "$out"
mkdir -p "$out"
stage=preflight
finish() {
  code=$?
  python3 - "$out" "$code" "$stage" <<'PY'
import datetime, json, sys
from pathlib import Path
out, code, stage = sys.argv[1:]
Path(out, 'smoke-result.json').write_text(json.dumps({
    'runtimeSmokePass': code == '0', 'exitCode': int(code), 'lastStage': stage,
    'finishedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'fullStackVerdict': 'PENDING_REAL_MODEL_AND_DISCONNECTED_DELIVERY_RECEIPTS' if code == '0' else 'FAIL_RUNTIME',
    'modelChat': 'NOT_TESTED_BY_THIS_RUNNER'}, indent=2))
PY
}
trap finish EXIT
k() { kubectl --kubeconfig "$PROOF_KUBECONFIG" --request-timeout=20s "$@"; }
k get --raw=/version > "$out/kubernetes-version.json"
k -n "$agent_ns" get workerpool "$pool" -o json > "$out/pool.json"
k -n "$agent_ns" get pods -l "ate.dev/worker-pool=$pool" -o json > "$out/worker-pods.json"
k get nodes -o json > "$out/nodes.json"
k -n "$agent_ns" get agent.api.kagent.dev "$agent_name" -o json > "$out/agent.json"
k -n "$system_ns" get deployments -o json > "$out/system-deployments.json"
k -n "$system_ns" get daemonsets -o json > "$out/system-daemonsets.json"
helm --kubeconfig "$PROOF_KUBECONFIG" -n "$system_ns" list -o json > "$out/substrate-releases.json"
helm --kubeconfig "$PROOF_KUBECONFIG" -n "$agent_ns" list -o json > "$out/kagent-releases.json"
python3 - "$out" "$root" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
root = Path(sys.argv[2])
read = lambda name: json.loads((out / name).read_text())
assert read('kubernetes-version.json')['gitVersion'] == 'v1.37.0', 'Wrong Kubernetes version'
pool = read('pool.json')
assert pool['spec']['sandboxClass'] == 'gvisor' and pool['spec']['replicas'] == 1
assert pool['status']['readyReplicas'] == 1
worker_lock = next(x for x in json.loads((root / 'image-lock.json').read_text()) if '/ateom-gvisor:' in x['reference'])
worker_digests = {worker_lock['digest']} | {x['digest'] for x in worker_lock['platforms'] if x.get('platform', {}).get('architecture') == 'amd64'}
assert pool['spec']['workerImage'].split('@')[-1] in worker_digests, 'Wrong or mutable worker image'
releases = read('substrate-releases.json') + read('kagent-releases.json')
expected = {'substrate-0.4.0-alpha1', 'substrate-crds-0.4.0-alpha1', 'kagent-1.0.0-alpha8', 'kagent-crds-1.0.0-alpha8'}
assert expected <= {r['chart'] for r in releases if r['status'] == 'deployed'}, 'Missing exact deployed chart versions'
for deployment in read('system-deployments.json')['items']:
    assert deployment['status'].get('readyReplicas', 0) == deployment['spec'].get('replicas', 1), deployment['metadata']['name']
for daemonset in read('system-daemonsets.json')['items']:
    assert daemonset['status']['desiredNumberScheduled'] >= 1
    assert daemonset['status'].get('numberReady', 0) == daemonset['status']['desiredNumberScheduled']
pods = [p for p in read('worker-pods.json')['items'] if not p['metadata'].get('deletionTimestamp')]
assert len(pods) == 1, 'Expected exactly one current worker'
pod = pods[0]
assert pod['status']['phase'] == 'Running'
assert all(c['ready'] for c in pod['status']['containerStatuses'])
node = next(n for n in read('nodes.json')['items'] if n['metadata']['name'] == pod['spec']['nodeName'])
labels, info = node['metadata']['labels'], node['status']['nodeInfo']
assert labels['node.kubernetes.io/instance-type'] == 'Standard_D8s_v3', 'Wrong selected VM SKU'
assert labels['kubernetes.azure.com/os-sku'] == 'AzureLinux', 'Wrong OS SKU'
assert info['architecture'] == 'amd64' and info['kubeletVersion'] == 'v1.37.0'
agent = read('agent.json')
conditions = {c['type']: c for c in agent['status']['conditions']}
for name in ['Accepted', 'ResolvedRefs', 'Compatible', 'Ready']:
    assert conditions[name]['status'] == 'True', name
    assert conditions[name]['observedGeneration'] == agent['metadata']['generation'], name
(out / 'selected-node.json').write_text(json.dumps({'labels': labels, 'nodeInfo': info}, indent=2))
PY
stage=template-discovery
"$root/bin/kubectl-ate" --kubeconfig "$PROOF_KUBECONFIG" get actor-templates -a "$agent_ns" -o json > "$out/templates.json"
adk_template=$(python3 - "$out/templates.json" "$agent_name" "${PROOF_ADK_TEMPLATE:-}" "$full_template" "$data_template" "$root" <<'PY'
import json, sys
from pathlib import Path
file, agent, selected, full, data, root = sys.argv[1:]
templates = json.load(open(file))['actorTemplates']
matches = [t for t in templates if t['metadata']['name'] == selected] if selected else [t for t in templates if t['metadata']['name'].startswith(agent + '-')]
assert len(matches) == 1, 'Ambiguous or missing generated template; set PROOF_ADK_TEMPLATE explicitly'
assert matches[0]['status']['goldenSnapshotStatus'].get('goldenTag'), 'Golden not ready'
assert matches[0]['snapshotConfig']['onPause'] == 'SNAPSHOT_CONTENT_SCOPE_FULL'
assert matches[0]['snapshotConfig']['onCommit'] == 'SNAPSHOT_CONTENT_SCOPE_DATA'
adk_lock = next(x for x in json.loads(Path(root, 'image-lock.json').read_text()) if '/golang-adk:' in x['reference'])
adk_digests = {adk_lock['digest']} | {x['digest'] for x in adk_lock['platforms'] if x.get('platform', {}).get('architecture') == 'amd64'}
assert matches[0]['containers'][0]['image'].split('@')[-1] in adk_digests, 'Wrong or mutable Go ADK image'
fixture = json.loads(Path(root, 'fixture-image-lock.json').read_text())
fixture_digests = {fixture['digest']} | {x['digest'] for x in fixture['platforms'] if x['platform']['architecture'] == 'amd64'}
for name, mode in [(full, 'FULL'), (data, 'DATA')]:
    template = next(t for t in templates if t['metadata']['name'] == name)
    assert template['status']['goldenSnapshotStatus'].get('goldenTag'), name
    assert template['snapshotConfig']['onPause'] == 'SNAPSHOT_CONTENT_SCOPE_' + mode, name
    assert template['snapshotConfig']['onCommit'] == 'SNAPSHOT_CONTENT_SCOPE_' + mode, name
    assert template['containers'][0]['image'].split('@')[-1] in fixture_digests, 'Wrong or mutable counter image'
print(matches[0]['metadata']['name'])
PY
)
stage=generated-adk
python3 "$root/verify-lifecycle.py" --cli "$root/bin/kubectl-ate" --kubeconfig "$PROOF_KUBECONFIG" \
  --router "$PROOF_ROUTER" --atespace "$agent_ns" --template "$adk_template" \
  --prefix "smoke-adk-$run_id" --actors 3 --workload adk --evidence "$out/adk"
stage=full-state-counter
python3 "$root/verify-lifecycle.py" --cli "$root/bin/kubectl-ate" --kubeconfig "$PROOF_KUBECONFIG" \
  --router "$PROOF_ROUTER" --atespace "$agent_ns" --template "$full_template" \
  --prefix "smoke-full-$run_id" --actors 1 --workload counter --evidence "$out/full"
stage=data-state-counter
python3 "$root/verify-lifecycle.py" --cli "$root/bin/kubectl-ate" --kubeconfig "$PROOF_KUBECONFIG" \
  --router "$PROOF_ROUTER" --atespace "$agent_ns" --template "$data_template" \
  --prefix "smoke-data-$run_id" --actors 1 --workload counter --evidence "$out/data"
stage=runtime-complete
echo "RUNTIME_SMOKE=PASS Receipt: $out"
echo 'Full stack verdict still requires the real-model and disconnected-delivery checks in SMOKE-TEST.md.'
