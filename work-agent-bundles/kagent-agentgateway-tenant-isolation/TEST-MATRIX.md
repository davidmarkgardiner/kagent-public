# Test matrix

These are the gates implemented by `scripts/verify.sh`, plus lifecycle gate R01 captured by the before and after preflight inventories. Every negative data-plane test is paired with a positive end-to-end path or a backend counter witness.

| ID | Path | Expected result | Witness |
| --- | --- | --- | --- |
| S01 | five platform HTTPRoutes | Accepted and ResolvedRefs are true | live route status |
| S02 | two MCP backends | Accepted is true | live backend status |
| S03 | canary policies under the dedicated controller | Accepted and Attached are true | controller-scoped status ancestor |
| S04 | existing Substrate specialist, ActorTemplate, and WorkerPool | Accepted/Ready, one golden template, workers 3/3 | live CR status |
| S05 | runtime actor lifecycle after P04 | suspended with new external snapshot | successful `SuspendActor`, status 4, snapshot URI prefix |
| P01 | in-cluster event source to webhook adapter to event A2A to event MCP | 200, completed, incident fixture | event MCP counter increases |
| P02 | chat prompt to chat A2A to chat MCP | 200, completed, release fixture | chat MCP counter increases |
| P03 | valid event runtime token to allowed MCP tool | 200 and incident fixture | event MCP counter increases |
| P04 | valid platform token to Substrate security specialist | 200, completed, required headings, context ID | gateway log plus S05 lifecycle witness |
| N01 | no token to event MCP | 401 | backend counter does not change |
| N02 | wrong audience to event MCP | 401 | backend counter does not change |
| N03 | expired token to event MCP | 401 | backend counter does not change |
| N04 | valid signature and audience with rogue tenant claim | 403 | backend counter does not change |
| N05 | chat MCP token on event MCP | 401 | backend counter does not change |
| N06 | event A2A token on event MCP | 401 | backend counter does not change |
| N07 | valid MCP token calls a known tool outside the allowlist | protocol error or denial | backend request and forbidden-tool counters do not change |
| N08 | rogue Pod calls both team MCP Services directly | timeout or refusal | P01 to P03 remain positive controls |
| N09 | rogue Pod reaches the Gateway without a token | 401 | proves the policy boundary is reachable |
| N10 | rogue admin creates Role or RoleBinding, reads a cross-team Secret, or requests a token | Kubernetes API Forbidden | four real API requests |
| N11 | rogue admin creates an HTTPRoute | Kubernetes API Forbidden | server-side dry-run request |
| N12 | `RemoteMCPServer.allowedNamespaces.from: All` | admission denial | server-side dry-run request |
| N13 | cross-namespace backend reference without an exact ReferenceGrant | ResolvedRefs false, RefNotPermitted | live disposable route status |
| N14 | privileged Pod in a team namespace | Pod Security Admission denial | server-side dry-run request |
| N15 | rogue Pod calls the kagent controller directly | timeout or refusal | P01 and P02 prove proxied A2A works |
| N16 | rogue Agent references another namespace's RemoteMCPServer | admission denial | server-side dry-run request |
| N17 | six authentication and claim denials | 401 or 403 | total MCP request counter does not change |
| N18 | legitimate tenant Deployment puts the reserved kagent label only in its Pod template | targeted admission denial | proves the NetworkPolicy identity selector cannot be forged through a controller template |
| N19 | legitimate tenant creates a BYO Agent with an arbitrary image | targeted admission denial | shared platform lane permits Declarative Agents only |
| N20 | no token to Substrate A2A listener | 401 | dedicated listener is reachable but authenticated |
| N21 | valid chat A2A token on Substrate A2A listener | 401 | audience separation |
| N22 | valid signature and Substrate audience with rogue claims | 403 | claim authorization |
| N23 | rogue Pod calls shared kagent SandboxAgent endpoint directly | timeout or refusal | P04 proves the proxied path works |
| R01 | pre-existing non-canary HTTPRoutes before and after shared CRD upgrade | all 13 retain Accepted true | before and after preflight inventories |
| T01 | workplace Substrate target contract and source image lock | target consistency passes and 16/16 digests resolve | `verify-substrate-target.sh` and `verify-substrate-images.sh` |

The AKS Entra profile has a separate promotion gate because red has no workplace Entra tenant. The JWKS backend and five JWT policies passed server-side schema dry-run; the route overlay has an expected red-cluster gap because red has Gateway API v1.4 rather than the pinned v1.6.2 experimental CRDs. Production promotion must still pass target-cluster dry-run, interactive discovery and PKCE, app-role denial, service-to-service workload-token refresh across expiry, external TLS, and the same isolation matrix.
