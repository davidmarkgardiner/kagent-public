#!/usr/bin/env bash
# Isolated transport test only. Explicit homelab context; no Argo or tickets.
set -euo pipefail
CONTEXT=${1:?usage: bash home_lab_smoke.sh proxmox-k8s|red|kind-NAME}
case "$CONTEXT" in proxmox-k8s|red|kind-*) ;; *) echo "refusing non-lab context" >&2; exit 2;; esac
BUNDLE=$(cd "$(dirname "$0")" && pwd)
RUN="admission-proof-$(date -u +%Y%m%d%H%M%S)"
OUTPUT=$(mktemp -d)/rendered
K=(kubectl --context "$CONTEXT" --request-timeout=20s)
cleanup() {
  for ns in "$RUN" "$RUN-n1" "$RUN-n2" "$RUN-n3"; do
    "${K[@]}" delete namespace "$ns" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT
python3 "$BUNDLE/home_lab.py" "$RUN" "$OUTPUT"
python3 - "$OUTPUT" <<'PY'
import sys,yaml
from pathlib import Path
p=Path(sys.argv[1])
docs=list(yaml.safe_load_all((p/'pipeline.yaml').read_text()))
(p/'namespaces.yaml').write_text(yaml.safe_dump_all([d for d in docs if d['kind']=='Namespace']))
(p/'resources.yaml').write_text(yaml.safe_dump_all([d for d in docs if d['kind']!='Namespace']))
PY
"${K[@]}" create -f "$OUTPUT/namespaces.yaml"
"${K[@]}" apply --dry-run=server -f "$OUTPUT/resources.yaml" >/dev/null
"${K[@]}" apply -f "$OUTPUT/resources.yaml" >/dev/null
for name in pg kafka gate vector alloy; do
  if ! "${K[@]}" -n "$RUN" rollout status "deployment/$name" --timeout=180s; then
    "${K[@]}" -n "$RUN" get pods
    "${K[@]}" -n "$RUN" logs "deployment/$name" --all-containers --tail=30 || true
    exit 1
  fi
done
"${K[@]}" -n "$RUN" exec deployment/gate -- python /code/home_lab_runtime.py broker-ready
"${K[@]}" -n "$RUN" exec deployment/gate -- python /code/home_lab_runtime.py pin-topics > "$OUTPUT/topic-pins.json"
"${K[@]}" -n "$RUN" set env deployment/gate "KAFKA_TOPIC_IDS=$(cat "$OUTPUT/topic-pins.json")" >/dev/null
"${K[@]}" -n "$RUN" rollout status deployment/gate --timeout=180s
"${K[@]}" apply --dry-run=server -f "$OUTPUT/fixtures.yaml" >/dev/null
"${K[@]}" apply -f "$OUTPUT/fixtures.yaml" >/dev/null
for ns in "$RUN-n1" "$RUN-n2" "$RUN-n3"; do
  "${K[@]}" -n "$ns" rollout status deployment --timeout=120s >/dev/null
done
for i in 1 2 3; do
  "${K[@]}" -n "$RUN-n$i" get pods -o json > "$OUTPUT/pods-$i.json"
done
python3 - "$OUTPUT" <<'PY'
import json,sys,yaml
from datetime import datetime,timezone
from pathlib import Path
p=Path(sys.argv[1]); docs=[]
for index in (1,2,3):
 pods=json.loads((p/f'pods-{index}.json').read_text())['items']
 assert len(pods)==5,len(pods)
 for pod in pods:
  meta=pod['metadata']; now=datetime.now(timezone.utc).isoformat()
  docs.append({'apiVersion':'v1','kind':'Event','metadata':{'name':meta['name']+'-synthetic','namespace':meta['namespace']},
   'involvedObject':{'apiVersion':'v1','kind':'Pod','name':meta['name'],'namespace':meta['namespace'],'uid':meta['uid']},
   'reason':'Unhealthy' if index==1 else 'OOMKilled','message':'Synthetic admission transport proof; no fault injected',
   'type':'Warning','source':{'component':'admission-proof'},'firstTimestamp':now,'lastTimestamp':now,'count':1})
(p/'events.yaml').write_text(yaml.safe_dump_all(docs))
PY
"${K[@]}" create -f "$OUTPUT/events.yaml" >/dev/null
ready=false
for attempt in $(seq 1 30); do
  if "${K[@]}" -n "$RUN" exec deployment/gate -- python /code/home_lab_runtime.py intake-ready > "$OUTPUT/intake-check.txt" 2>&1; then
    ready=true; break
  fi
  sleep 2
done
if [[ "$ready" != true ]]; then
  "${K[@]}" -n "$RUN" exec deployment/gate -- python /code/home_lab_runtime.py snapshot
  "${K[@]}" -n "$RUN" logs deployment/alloy --tail=30
  "${K[@]}" -n "$RUN" logs deployment/vector --tail=30
  "${K[@]}" -n "$RUN" logs deployment/gate --tail=30
  exit 1
fi
cat "$OUTPUT/intake-check.txt"
# Allow the finite fixture log burst to finish before the deterministic slot.
sleep 15
"${K[@]}" -n "$RUN" exec deployment/gate -- python /code/home_lab_runtime.py prove > "$OUTPUT/result.json"
cat "$OUTPUT/result.json"
"${K[@]}" -n "$RUN" rollout restart deployment/gate >/dev/null
"${K[@]}" -n "$RUN" rollout status deployment/gate --timeout=180s
"${K[@]}" -n "$RUN" exec deployment/gate -- python /code/home_lab_runtime.py prove > "$OUTPUT/restart.json"
"${K[@]}" -n "$RUN" exec deployment/gate -- python /code/strict_soak.py > "$OUTPUT/strict.json"
cat "$OUTPUT/strict.json"
echo "Proof artifact: $OUTPUT/result.json"
cleanup
trap - EXIT
for ns in "$RUN" "$RUN-n1" "$RUN-n2" "$RUN-n3"; do
  "${K[@]}" wait --for=delete "namespace/$ns" --timeout=90s >/dev/null
done
echo "HOME_LAB_TRANSPORT_PASS: isolated namespaces removed; no Argo, agent, or ticket objects created."
