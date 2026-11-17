# AKS starter validation

Checked locally on 17 November 2026. This records source/rendering checks, not
AKS admission, installed-version compatibility, caller authentication or live
ServiceNow delivery.

| Check | Result |
|---|---|
| Renderer and response-verifier behaviour | 9 offline tests passed. |
| Four rendered resources | Passed the official structural schemas listed below. |
| JSON-to-A2A request transformation | Parsed mapping equals the live-tested Proxmox policy exactly. |
| Same-namespace backend | Produces three files and omits the unnecessary ReferenceGrant. |
| Missing placeholders, invalid ports/path/host, unknown settings | Rejected before files are written. |
| Existing render output | Preserved; renderer refuses a nonempty output folder. |
| HTTP 200 with failed, submitted or working task | Rejected as incomplete/failed execution. |
| Completed task without response text or expected markers | Rejected by the verifier. |

Offline helper tests require only Python 3:

```bash
python3 -m unittest -v test_helpers.py
```

Structural validation used these pinned upstream CRDs:

- Istio VirtualService, Istio 1.27.0:
  https://github.com/istio/istio/blob/1.27.0/manifests/charts/base/files/crd-all.gen.yaml
- HTTPRoute, Gateway API 1.3.0:
  https://github.com/kubernetes-sigs/gateway-api/blob/v1.3.0/config/crd/standard/gateway.networking.k8s.io_httproutes.yaml
- ReferenceGrant, Gateway API 1.3.0:
  https://github.com/kubernetes-sigs/gateway-api/blob/v1.3.0/config/crd/standard/gateway.networking.k8s.io_referencegrants.yaml
- AgentgatewayPolicy, agentgateway 1.7.0, local reference tag resolving to
  `26f5aebe99a36a037fe54f8080a608aca5547e15`:
  https://github.com/agentgateway/agentgateway/blob/v1.7.0/controller/install/helm/agentgateway-crds/templates/agentgateway.dev_agentgatewaypolicies.yaml

These schema versions are validation references, not instructions to install or
upgrade them. Structural schema checks do not execute Kubernetes CEL admission
rules or prove runtime policy attachment. The work agent must validate the
rendered/merged configuration against the actual installed versions.

The [existing live receipts](../poc/evidence/result.json) and
[clean replay receipts](../poc/evidence/replay-result.json) remain the evidence
for gateway 1.7.0 converting raw JSON and regular kagent 0.10.4 completing the
request. The new AKS entry point has not been deployed or tested against a target
AKS cluster as part of preparing this folder.
