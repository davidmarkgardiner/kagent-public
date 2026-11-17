# AKS Istio PoC starter: fill values, render YAML, send JSON

Give the work agent this **whole folder** plus the linked
[lab proof](../poc/README.md). This starter supplies the example YAML files for
the workplace PoC. It reuses the existing ingress, agentgateway listener and
approved agent endpoint. There is no new receiver application, Argo installation,
agent runtime, model configuration, credential, or public LoadBalancer in these
templates. Python 3 is the only dependency of the renderer and test client.

```text
HTTPS JSON POST → existing AKS Istio ingress → VirtualService
  → existing agentgateway Service/listener → HTTPRoute + body policy
  → approved A2A entry point → selected agent
```

**Evidence:** the body transformation is the same mapping that passed live on
agentgateway 1.7.0 with regular kagent 0.10.4 in Proxmox. These parameterized AKS
templates are locally checked, not a completed AKS or ServiceNow deployment.
See [validation details](VALIDATION.md) for the nine offline checks and exact
upstream schema references. The target cluster still needs server validation.

## Files to use

| File | Purpose |
|---|---|
| [values.example.json](values.example.json) | One place to fill discovered workplace resource names, hostname, ports and agent path. |
| [01-virtualservice.yaml](templates/01-virtualservice.yaml) | Match the HTTPS host and POST path; forward to the existing agentgateway Service without changing the path. |
| [02-httproute.yaml](templates/02-httproute.yaml) | Attach to the existing gateway listener; rewrite only to the selected A2A endpoint. |
| [03-payload-policy.yaml](templates/03-payload-policy.yaml) | Convert the raw JSON body into an A2A `message/send` envelope. |
| [04-referencegrant.yaml](templates/04-referencegrant.yaml) | Allow the specific cross-namespace Service backend; omitted when namespaces match. |
| [render.py](render.py) | Render locally, reject unfilled/invalid values, refuse a nonempty output folder. |
| [incident.json](incident.json) | Synthetic request including a marker, quotes and a newline. |
| [smoke.py](smoke.py) | Send one HTTPS POST; check HTTP status, JSON-RPC errors, terminal A2A state, response text and optional expected markers. |
| [headers.example.json](headers.example.json) | Optional local caller-authentication header file; no actual credential supplied. |

The `.yaml` files under `templates/` contain placeholders. **Render them first;
do not apply that directory directly.** No script in this folder deploys or
deletes a Kubernetes resource.

## 1. Resolve the values against the existing installation

The work agent should inspect its authorized target using explicit kubeconfig
and context. Reuse the existing resources; fill `values.json` with their actual
names. The examples' port numbers are starting values, not discovered facts.

| Value(s) | What to discover |
|---|---|
| `VIRTUALSERVICE_API_VERSION` | Installed Istio API: `networking.istio.io/v1` or `v1beta1`. |
| `VIRTUALSERVICE_NAMESPACE`, `VIRTUALSERVICE_NAME` | Owning VirtualService or new PoC route object under the platform's normal ownership rules. |
| `INGRESS_HOST` | Approved DNS hostname covered by the existing Istio HTTPS server and certificate. |
| `ISTIO_GATEWAY_NAMESPACE`, `ISTIO_GATEWAY_NAME` | The existing **Istio** Gateway (`networking.istio.io`), not the agentgateway Gateway. |
| `GATEWAY_NAMESPACE`, `GATEWAY_NAME`, `GATEWAY_LISTENER` | Existing **agentgateway** Gateway (`gateway.networking.k8s.io`) and listener; HTTPRoute is rendered in that namespace. |
| `GATEWAY_SERVICE_NAME`, `GATEWAY_SERVICE_PORT` | The data-plane Service and its actual Service port, not a guessed container/HTTPS port. |
| `BACKEND_NAMESPACE`, `BACKEND_SERVICE_NAME`, `BACKEND_SERVICE_PORT` | Approved existing A2A entry-point Service. Preserve any facade that enforces approval/authentication. |
| `BACKEND_A2A_PATH` | Exact A2A path for the selected agent; keep the required trailing slash. A facade may use `/` instead of the controller path. |
| `ROUTE_NAME`, `POLICY_NAME`, `GRANT_NAME` | Unique names for this PoC delta. Do not take over an unrelated resource. |
| `REQUEST_TIMEOUT_SECONDS` | Gateway timeout, default 90 seconds. Istio receives five additional seconds; align the caller timeout too. |

Confirm the gateway supports `traffic.transformation.request` with `json()`,
`toJson()` and `uuid()`, and that the agent accepts this A2A contract. Stop on a
version mismatch and report the missing capability rather than upgrading the
platform as part of this PoC.

These templates do not create authentication or network permissions. Reuse the
approved caller authentication and authorisation at Istio/agentgateway, including
permission for this new path. Verify listener hostname/allowedRoutes, existing
mTLS and NetworkPolicies, and policy ownership/precedence. A ReferenceGrant is
not caller authorisation. Avoid an anonymous bypass around an existing gate.

## 2. Render the four examples

From this folder:

```bash
cp values.example.json values.json
# Fill the placeholders and check every port in values.json.
python3 render.py --values values.json --out rendered
```

The renderer makes three files for a same-namespace backend, or four when the
backend Service requires a cross-namespace ReferenceGrant. Local values, rendered
files, credentials and evidence are gitignored. Do not commit workplace values
into this public repository.

## 3. Validate and deliver the small PoC change

Review the rendered files with the work agent. If an existing VirtualService
already owns the hostname, **merge only the incident rule** into it; applying a
new competing object or replacing its `spec.http` would risk existing routes.
Do the same ownership/merge check for policies. Keep `/incidents/triage/` intact
at Istio; its rewrite happens in agentgateway.

Use the workplace delivery tooling. Where direct server-side validation is
permitted, the equivalent check is:

```bash
WORK_CONTEXT='{{WORK_CONTEXT}}'
kubectl --context "$WORK_CONTEXT" apply --dry-run=server -f rendered/
```

`{{WORK_CONTEXT}}` is the verified workplace context. For a merged VirtualService,
validate the final merged object instead of blindly validating/deploying the
standalone example. Deliver the reviewed delta using the existing authorized
GitOps/release process. Check current-generation route `Accepted`/`ResolvedRefs`
and policy `Accepted`/`Attached` status before sending a test request.

No retry policy is added for agentgateway. The Istio example explicitly disables
retries for this submission; inspect inherited retries and client settings too.
Do not replay a timed-out request without reconciling whether it already ran.

## 4. Prove intake with one synthetic request

Choose an approved read-only/test agent that can answer the marker request.
The payload asks it not to call tools; actual permissions remain the enforcement
boundary. If its system instructions prevent marker echo, adapt the verification
to its documented response and correlate the gateway and agent receipts.

If the existing auth scheme uses a request header, copy `headers.example.json`
to `headers.private.json` and fill `{{AUTHORIZATION_VALUE}}` with the approved
caller's full header value. Keep it local and restrict file access. No token is
created by this package. For mTLS or another client-authentication mechanism,
use the platform's existing HTTP client with the same JSON fixture instead.

```bash
POC_HOST='{{INGRESS_HOST}}'
python3 smoke.py \
  --url "https://${POC_HOST}/incidents/triage/" \
  --headers-file headers.private.json \
  --expect-text AKS_JSON_A2A_POC \
  --expect-text INC-POC-AKS-001 \
  --out evidence/run-01
```

The client uses normal TLS verification, follows no redirects and makes no
automatic retries. A running/submitted task is not reported as completed.
Receipts contain request/response data and must remain private unless sanitized.
The reported PASS proves only this request's terminal response and markers;
also capture the corresponding Istio route, gateway route and agent task IDs.

The lab observed HTTP 503 for malformed JSON. This is a PoC limitation, not a
finished validation/error contract. It also does not provide durable dedupe,
asynchronous recovery or ServiceNow write-back.

## 5. Finish the handoff

Save the rendered/merged diff, target versions, route/policy status, HTTPS test
receipt and correlated agent result in the workplace repository's evidence area.
Then test a real ServiceNow delivery separately when available and authorized.
Rollback only this PoC delta through the normal delivery flow: restore the prior
VirtualService and remove the new incident route/policy/grant as applicable.
Leave shared Gateways, certificates, credentials, model wiring and agents intact.

Copy-ready work-agent request:

```text
Use this aks/ starter folder to prepare and set up the raw-JSON incident intake
PoC behind our existing AKS Istio ingress and agentgateway. Discover and fill
values.json, render the YAML, preserve existing ownership/authentication and the
approved agent entry point, and deliver only the reviewed route/policy/grant
delta through our existing process. Do not run the Proxmox lab scripts on AKS.
Do not introduce Argo, new credentials, a new provider, or a custom receiver.
Prove one synthetic HTTPS request reaches the selected agent over A2A, record
the terminal result and markers, and provide the rollback and evidence receipts.
```
