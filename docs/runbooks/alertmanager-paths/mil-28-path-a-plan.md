# MIL-28 Path A Plan

## Goal

Prove Path A on `proxmox-k8s`: Alertmanager-compatible webhook payload ->
Redpanda Kafka -> Argo Events Kafka EventSource -> consumer pod. Stop after the
consumer pod logs the pod name and parseable alert JSON summary.

## Steps

1. Validate the existing Redpanda Kafka manifests render cleanly.
2. Deploy the Path A overlay to namespace `kagent-poc`.
3. Confirm Redpanda, topic bootstrap, bridge, EventSource, and Sensor become
   healthy.
4. Send the sanitized Alertmanager payload through the bridge endpoint.
5. Capture evidence from bridge logs, Redpanda topic state, EventSource/Sensor
   resources, and the consumer pod log.
6. Update the runbook/results docs with live evidence and any caveats.

## Caveats To Track

- The live cluster currently runs Argo Events controller image `v1.9.6`; the
  intake context requested `v1.9.10`.
- The repository includes an Alertmanager receiver example, but production
  Alertmanager routing should not be modified until the POC payload path is
  validated.
- The generated Argo EventSource/Sensor pods are pinned to `k8s-worker1` during
  this POC to avoid a node-local watcher limit hit observed on `k8s-worker2`.
- The namespace-local JetStream EventBus is single-node, so the stream config
  must set `replicas: 1`; the controller default uses three stream replicas.
