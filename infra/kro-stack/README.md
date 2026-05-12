# KRO Stack — AKS Cluster Provisioning

This directory contains KRO (Kubernetes Resource Orchestrator) ResourceGroupDefinitions (RGDs) for declaratively provisioning AKS clusters via ASO (Azure Service Operator). See the existing `README.md` in each subdirectory for full usage instructions.

The primary RGD for production use is `definitions/uk8scluster-public.yaml` — it enforces security defaults (local accounts disabled, Azure RBAC enabled, Defender enabled). Use `instances/dev/example-cluster.yaml` or `instances/production/example-cluster.yaml` as starting points for new cluster instances.

> **IMPORTANT:** Apply instances only on the management cluster running ASO + KRO. Never apply directly against a worker cluster. Always confirm cluster name, resource group, region, and purpose before deploying.
