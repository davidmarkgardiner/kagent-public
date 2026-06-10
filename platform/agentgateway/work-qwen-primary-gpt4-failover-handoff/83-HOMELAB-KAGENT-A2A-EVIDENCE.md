# Home-Lab Kagent A2A Benchmark Evidence

Date: 2026-06-03
Cluster context: `proxmox-k8s`

## What Was Tested

Primary benchmark path:

```text
curl -> kagent-controller:8083 -> /api/a2a/kagent/k8s-agent/ -> k8s-agent -> Qwen model path
```

Command:

```bash
TOTAL=20 \
CONCURRENCY=20 \
AGENT_NAME=k8s-agent \
PROMPT="reply with exactly: ok" \
CURL_TIMEOUT=240 \
./bench-kagent-a2a.sh
```

Result:

```text
total=20
status_counts=000:20
state_counts=transport_error:20
```

Single-call baseline:

```bash
TOTAL=1 \
CONCURRENCY=1 \
AGENT_NAME=k8s-agent \
PROMPT="reply with exactly: ok" \
CURL_TIMEOUT=240 \
./bench-kagent-a2a.sh
```

Result:

```text
total=1
status_counts=000:1
state_counts=transport_error:1
```

## Interpretation

This is not a valid Qwen capacity ceiling. Because a single request also failed,
the local home-lab result means the current `k8s-agent` A2A path is not healthy
enough for capacity measurement.

Controller logs showed the request eventually failing after about 241 seconds:

```text
Unexpected error calling OnSendMessage for task:
a2aClient.SendMessage ... Post "http://k8s-agent.kagent:8080/": context canceled

Request completed:
method=POST
path=/api/a2a/kagent/k8s-agent/
status=500
duration=240.997s
```

The benchmark default timeout was raised to 300 seconds after this finding so
future runs can capture the controller-side `500` instead of timing out just
before it is returned.

## What The Work Agent Should Do

1. Run the 20-concurrent test against a known-good work kagent agent.
2. If 20 fails, immediately run `TOTAL=1 CONCURRENCY=1` against the same agent.
3. Only treat a 20-way failure as capacity evidence if the single-call baseline
   completes with A2A state `completed`.
4. If the single-call baseline fails, debug agent readiness, downstream agent
   service logs, model config, gateway route, and provider token path first.
