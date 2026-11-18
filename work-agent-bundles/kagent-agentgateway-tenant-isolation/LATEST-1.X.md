# Isolation on the 1.0 platform

Use the [current MkDocs handbook](../agent-platform-mkdocs/README.md), particularly [isolation](../agent-platform-mkdocs/docs/isolation.md), [identity](../agent-platform-mkdocs/docs/identity.md) and [labs](../agent-platform-mkdocs/docs/labs.md), for new kagent 1.0.1 work.

This bundle's older manifests and isolation/Entra receipts remain historical named-version evidence. New AgentTemplate/Harness/Agent APIs, session-backed Actors, A2A routes, token propagation and worker privileges need a deliberate port and fresh denials/lifecycle tests. Readiness or a chart render cannot renew the old isolation proof. Preserve the policy blocker and platform/destination-owned security boundaries.
