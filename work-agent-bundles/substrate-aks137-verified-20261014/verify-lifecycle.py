#!/usr/bin/env python3
"""Bounded synthetic lifecycle assertions and operator-path timings."""
import argparse
import datetime
import json
import math
import statistics
import subprocess
import time
import urllib.request
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--cli', required=True)
p.add_argument('--kubeconfig', required=True)
p.add_argument('--router', required=True)
p.add_argument('--atespace', default='kagent')
p.add_argument('--template', required=True)
p.add_argument('--prefix', required=True)
p.add_argument('--actors', type=int, default=3)
p.add_argument('--workload', choices=['adk', 'counter'], required=True)
p.add_argument('--evidence', required=True)
a = p.parse_args()
if not 1 <= a.actors <= 20:
    p.error('--actors must be between 1 and 20')
out = Path(a.evidence)
out.mkdir(parents=True, exist_ok=False)
base = [a.cli, '--kubeconfig', a.kubeconfig]
steps = []
measurements = []
stage = 'preflight'
created = []
def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def call(label, *args):
    global stage
    stage = label
    started = utc()
    start = time.perf_counter()
    r = subprocess.run(base + list(args), text=True, capture_output=True, timeout=180)
    elapsed = (time.perf_counter() - start) * 1000
    steps.append({'stage': label, 'utcStart': started, 'utcEnd': utc(), 'args': list(args),
                  'elapsedMs': elapsed, 'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})
    (out / 'steps.json').write_text(json.dumps(steps, indent=2))
    if r.returncode:
        raise RuntimeError(f'{label} exited {r.returncode}; see steps.json')
    if args[0] != 'get':
        measurements.append({'operation': label.split('/')[-1], 'elapsedMs': elapsed})
    return r.stdout

def actor(label, name, expected, uid=None):
    value = json.loads(call(label, 'get', 'actor', name, '-a', a.atespace, '-o', 'json'))
    assert value['metadata']['name'] == name
    assert value['metadata']['atespace'] == a.atespace
    if uid:
        assert value['metadata']['uid'] == uid, 'actor identity changed'
    status = value['status']
    assert status['state'] == 'ACTOR_STATE_' + expected, (label, status)
    if expected == 'SUSPENDED':
        assert status.get('externalSnapshot', {}).get('snapshotUri'), 'snapshot receipt missing'
        assert not status.get('workerAssignment'), 'worker assignment retained'
    if expected == 'PAUSED':
        assert status.get('localSnapshot', {}).get('snapshotName'), 'local snapshot receipt missing'
        assert status['localSnapshot'].get('nodeVmsWithLocalSnapshots'), 'snapshot node missing'
        assert not status.get('workerAssignment'), 'worker assignment retained'
    if expected == 'RUNNING':
        assert status.get('workerAssignment', {}).get('workerPodUid'), 'worker mapping missing'
    return value

def http(label, name, expected_pair=None):
    global stage
    stage = label
    path = '/.well-known/agent-card.json' if a.workload == 'adk' else '/'
    req = urllib.request.Request(a.router.rstrip('/') + path,
        data=None if a.workload == 'adk' else b'',
        headers={'ate-target-actor': a.atespace + '/' + name, 'X-Proof-Marker': 'SYNTHETIC-' + name})
    started = utc()
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        assert r.status == 200
        raw = r.read(1048577)
        assert len(raw) <= 1048576
    elapsed = (time.perf_counter() - start) * 1000
    data = json.loads(raw)
    (out / (label.replace('/', '-') + '.json')).write_text(json.dumps(data, indent=2))
    steps.append({'stage': label, 'utcStart': started, 'utcEnd': utc(), 'actor': name,
                  'httpStatus': 200, 'elapsedMs': elapsed, 'response': data})
    (out / 'steps.json').write_text(json.dumps(steps, indent=2))
    measurements.append({'operation': 'http-ready', 'elapsedMs': elapsed})
    if expected_pair:
        assert (data['memory'], data['durable']) == expected_pair, (label, data, expected_pair)
        assert data['marker'] == 'SYNTHETIC-' + name
    return data

try:
    before = json.loads(call('template-before', 'get', 'actor-template', a.template, '-a', a.atespace, '-o', 'json'))
    assert before['status']['goldenSnapshotStatus'].get('goldenTag'), 'golden not ready'
    (out / 'template-before.json').write_text(json.dumps(before, indent=2))
    pause_mode = before['snapshotConfig']['onPause'].split('_')[-1]
    commit_mode = before['snapshotConfig']['onCommit'].split('_')[-1]
    for i in range(1, a.actors + 1):
        name = f'{a.prefix}-{i:02d}'
        call(name + '/create', 'create', 'actor', name, '-a', a.atespace, '--template', a.template)
        initial = actor(name + '/read-created', name, 'SUSPENDED')
        uid = initial['metadata']['uid']
        created.append({'name': name, 'atespace': a.atespace, 'uid': uid})
        (out / 'created-actors.json').write_text(json.dumps(created, indent=2))
        call(name + '/resume-golden', 'resume', 'actor', name, '-a', a.atespace)
        actor(name + '/read-running', name, 'RUNNING', uid)
        first = http(name + '/initial', name, (1, 1) if a.workload == 'counter' else None)
        call(name + '/pause-' + pause_mode.lower(), 'pause', 'actor', name, '-a', a.atespace)
        paused = actor(name + '/read-paused', name, 'PAUSED', uid)
        assert paused['status']['localSnapshot']['contentScope'].endswith(pause_mode)
        call(name + '/resume-paused', 'resume', 'actor', name, '-a', a.atespace)
        actor(name + '/read-restored-pause', name, 'RUNNING', uid)
        memory = 2 if pause_mode == 'FULL' else 1
        second = http(name + '/after-pause', name, (memory, 2) if a.workload == 'counter' else None)
        call(name + '/suspend-' + commit_mode.lower(), 'suspend', 'actor', name, '-a', a.atespace)
        committed = actor(name + '/read-committed', name, 'SUSPENDED', uid)
        assert committed['status']['externalSnapshot']['snapshotUri'] != initial['status']['externalSnapshot']['snapshotUri']
        assert committed['status']['externalSnapshot']['contentScope'].endswith(commit_mode)
        call(name + '/resume-committed', 'resume', 'actor', name, '-a', a.atespace)
        actor(name + '/read-restored-commit', name, 'RUNNING', uid)
        third = http(name + '/after-commit', name, (memory + 1 if commit_mode == 'FULL' else 1, 3) if a.workload == 'counter' else None)
        if a.workload == 'adk':
            assert first.get('name') and first == second == third, 'agent card changed'
        call(name + '/final-suspend-' + commit_mode.lower(), 'suspend', 'actor', name, '-a', a.atespace)
        actor(name + '/read-final', name, 'SUSPENDED', uid)
        print(f'PASS {name}: same identity, golden restore, {pause_mode} pause, {commit_mode} commit, state assertions', flush=True)
    after = json.loads(call('template-after', 'get', 'actor-template', a.template, '-a', a.atespace, '-o', 'json'))
    assert before == after, 'template/golden changed'
    summary = []
    for operation in sorted({row['operation'] for row in measurements}):
        values = sorted(row['elapsedMs'] for row in measurements if row['operation'] == operation)
        summary.append({'operation': operation, 'samples': len(values), 'p50Ms': statistics.median(values),
                        'p95Ms': values[math.ceil(len(values) * .95) - 1], 'minMs': min(values), 'maxMs': max(values)})
    (out / 'benchmark.json').write_text(json.dumps({'measurement': 'Mac operator wall time; CLI includes process start, token acquisition, automatic port-forward and network RTT; HTTP uses an existing router port-forward', 'actors': a.actors, 'pauseMode': pause_mode, 'commitMode': commit_mode, 'summary': summary, 'raw': measurements}, indent=2))
    (out / 'result.json').write_text(json.dumps({'pass': True, 'actors': created, 'workload': a.workload, 'templateStable': True, 'modelCalls': False, 'finishedUtc': utc()}, indent=2))
except Exception as error:
    (out / 'result.json').write_text(json.dumps({'pass': False, 'stage': stage, 'error': str(error), 'createdActors': created, 'finishedUtc': utc()}, indent=2))
    raise
