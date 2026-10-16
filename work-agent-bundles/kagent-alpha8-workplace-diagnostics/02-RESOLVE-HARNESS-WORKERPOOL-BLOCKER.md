# Resolve the Alpha 8 Harness and WorkerPool deployment blocker

Prepared 2026-10-16. Hand this entire file to the workplace agent.

## Task and reported constraint

Find a supported route to restore a usable workplace agent while preserving Azure policy. The reported blocker is the native Alpha 8 seed AgentTemplate/Harness/Agent adapter. Its Harness schema requires a Substrate WorkerPool, while the worker pool is intentionally disabled because of Azure policy. An older regular Agent manifest cannot be applied directly.

Interpret "worker pull" as "worker pool" provisionally. Verify whether the actual problem is disabled worker provisioning, denied worker-pod admission, blocked image pulls, or a combination. These require different fixes.

Perform read-only discovery and prepare an implementation proposal with local manifest diffs. Do not enable workers, weaken policy, fabricate a WorkerPool, patch CRDs, install another controller, roll back a release, or apply the seed resources under this task. Use explicit target context on cluster commands. Keep raw evidence private and share only sanitized findings. Do not collect Secret values.

## What the pinned source establishes

The stock `v1.0.0-alpha8` API has these requirements:

- `api.kagent.dev/v1alpha3` `Agent` pairs behavior with a Harness. It requires exactly one of `template` or `templateRef`, and exactly one of `harness` or `harnessRef`.
- `Harness.spec` requires `workload` and `substrate`. The Substrate policy requires a nonempty `workerPoolRef.name` and a snapshot location. The pool reference is local to the Harness namespace.
- The choices `kagent`, `codex`, `claude` and `byo` select an execution adapter. They all retain the required Substrate policy. A `byo` image does not provide a built-in ordinary-Deployment escape route.
- The native translator resolves WorkerPool capacity, and the built-in and BYO compilers carry that placement into runtime revisions. Removing schema validation would leave runtime dependencies unresolved.
- `substrateWorkerPool.create: false` prevents this Helm chart from creating the pool. It allows externally managed capacity; it does not supply a substitute execution backend. `controller.substrate.enabled: false` does not restore the old deployment-backed API.

Inspect these pinned sources and compare them with the installed schemas and controller provenance:

https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/go/api/v1alpha3/agent_types.go
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/go/api/v1alpha3/harness_types.go
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/go/api/v1alpha3/runtime_types.go
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/go/core/internal/translator/validation.go
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/go/core/internal/translator/kagent/compiler.go
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/go/core/internal/translator/byo/compiler.go
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/helm/kagent/values.yaml

The practical conclusion is that a native Alpha 8 managed agent needs usable Substrate worker capacity. A schema-only manifest conversion cannot remove that infrastructure requirement. Workplace patches may change this contract, but require exact source and runtime evidence before relying on them.

## 1. Disambiguate versions before converting anything

Record these separately:

| Item | Required observation |
| --- | --- |
| Old manifest | Literal `apiVersion`, `kind` and field structure |
| Old release | Controller/chart version that actually ran that manifest |
| New release | Installed chart, controller image digest, UI and adapter image provenance |
| Installed API | Served/storage CRD versions, required fields, CEL rules and conversion configuration |
| Seed source | Owning repository, renderer/script and exact commit that generates the seed resources |

`kagent.dev/v1alpha2` is an API version. `1.0.0-alpha2` is a product release. They are not interchangeable. Do not label an old manifest as release Alpha 2 just because its API is `v1alpha2`. If it really came from release `1.0.0-alpha2`, compare that release's schema directly rather than assuming it was a regular deployment-backed agent.

Discover installed resource names before querying them:

```bash
export WORK_CONTEXT='{{WORK_CONTEXT}}'
export WORK_NAMESPACE='{{WORK_NAMESPACE}}'
kubectl --context "$WORK_CONTEXT" api-resources --api-group=api.kagent.dev
kubectl --context "$WORK_CONTEXT" api-resources --api-group=kagent.dev
kubectl --context "$WORK_CONTEXT" api-resources --api-group=ate.dev
```

Inspect the discovered Agent/Harness/AgentTemplate and WorkerPool schemas. Record missing API discovery permissions as UNKNOWN. Capture narrowly scoped admission errors, conditions, observed generations and controller errors. Schema rejection, unresolved references, preparation failure and a failed live invocation are separate failure stages.

## 2. Identify what policy actually blocks

Find the policy assignment or admission rule, exact denied field/resource, scope, enforcing component and owner. Use existing admission receipts, events and policy reports; do not generate a denied workload merely to obtain a message.

Distinguish:

- An intentionally false chart value, or a pool with zero desired capacity.
- A worker denied because of privileged mode, host paths, capabilities or runtime/node requirements.
- An image registry denial or image pull/authentication failure.
- Missing permissions, quota, node placement, network access or storage.

Inspect the rendered workload for the exact pinned Substrate version. List the specific policy conflicts rather than requesting a blanket privileged namespace. Check whether an existing approved WorkerPool is available in the required namespace, its actual capacity and health, and whether this agent is allowed to use it.

Do not disable Azure Policy, Gatekeeper, Kyverno or Pod Security enforcement. Do not relabel namespaces or replace the gVisor worker with a normal pod to make admission pass. A fake reference or idle pool object can satisfy part of validation while leaving agent execution unusable.

## 3. Select a viable path

Evaluate the paths below using current workplace evidence. Recommend the smallest path that both satisfies policy and provides the capability the user needs.

| Path | When it is viable | Required work and limitation |
| --- | --- | --- |
| Reuse approved capacity | A compatible, healthy Substrate WorkerPool already exists and this workload is authorized to use it | Keep chart pool creation disabled; reference real capacity in the Harness namespace; verify snapshot storage, controller integration, placement and runtime permissions |
| Obtain approved runtime capacity | Policy owners permit a narrowly scoped exception or a dedicated approved runtime boundary | Prepare exact workload requirements and a scoped exception/design proposal; enable only through the normal reviewed delivery path after authorization |
| Keep the last approved deployment-backed stack available | Substrate capacity is prohibited and operational agents are needed now | Prepare a separately owned, compatible deployment-backed stack using the actual last working version; preserve existing service and data; no native Alpha 8 lifecycle claim |
| Develop a different execution integration | Native Alpha 8 plus no permitted worker capacity is a firm requirement | Treat an ordinary-Deployment executor or external A2A bridge as a separate engineering project with API, routing, auth, state and UI compatibility proof; do not present it as an existing Helm switch |

For a dedicated or external runtime boundary, prove that the pinned controller/runtime supports the proposed topology, including WorkerPool discovery, identity, certificates, network routing, snapshot storage and policy scope. Do not promise that a remote worker or another cluster works simply because it is reachable.

If policy rules out all Substrate workers, the immediate recommendation is to retain or recover the approved deployment-backed service while leaving the Alpha 8 native seed blocked. A UI/control-plane deployment can remain available for evaluation, but it must report that managed-agent execution is unavailable. Do not downgrade shared CRDs or reuse an Alpha 8 database with an older controller without an explicitly reviewed compatibility and restore plan. A namespace alone does not isolate cluster-scoped CRDs.

## 4. Prepare the smallest valid seed migration

Do this only as a local proposal after identifying a viable runtime path. Preserve the approved model route, authentication, tools, grants, service accounts, namespaces and delivery ownership.

Read the old manifest and map its actual fields into the installed Alpha 8 `AgentTemplate` and `Harness` schema. Do not just change `apiVersion`. Record unsupported behavior, model/tool format changes and any required adapter/image changes. Use a digest-pinned image accepted by the selected adapter; a generic BYO image and the native kagent adapter have different contracts.

The following illustrates only the stock Alpha 8 resource relationship. It is deliberately incomplete, uses placeholders, and is not an apply-ready fix:

```yaml
apiVersion: api.kagent.dev/v1alpha3
kind: Harness
metadata:
  name: '{{HARNESS_NAME}}'
  namespace: '{{WORK_NAMESPACE}}'
spec:
  kagent: {}
  workload:
    image: '{{APPROVED_ALPHA8_ADAPTER_IMAGE_AT_SHA256_DIGEST}}'
  substrate:
    workerPoolRef:
      name: '{{EXISTING_APPROVED_READY_WORKERPOOL}}'
    snapshotPolicy:
      location: '{{APPROVED_SNAPSHOT_LOCATION}}'
---
apiVersion: api.kagent.dev/v1alpha3
kind: Agent
metadata:
  name: '{{AGENT_NAME}}'
  namespace: '{{WORK_NAMESPACE}}'
spec:
  templateRef:
    name: '{{REVIEWED_ALPHA8_AGENT_TEMPLATE_NAME}}'
  harnessRef:
    name: '{{HARNESS_NAME}}'
```

Create the separate AgentTemplate proposal from the installed schema and the old behavior. Notice that stock Alpha 8 uses top-level `templateRef`, while newer rolling documentation may show other shapes. Use the installed schema and the matching source tag as authority. Inline template/harness forms still require the same runtime dependencies.

Render and validate the proposal locally against captured schemas. If workplace rules permit admission-only checks, a server dry-run can validate schema and admission without persisting resources. Record whether it was run and its exact outcome. Neither local validation nor server dry-run proves controller reconciliation or runtime execution. Do not run the reproduction bundle's cleanup/reinstall scripts against shared workplace services as a shortcut.

## 5. Required findings and follow-up proof

Write `HARNESS-WORKERPOOL-FINDINGS.md` in the approved private workspace. Include:

1. The literal failure and its stage, installed version evidence and exact relevant schema fields.
2. A diagram or short chain showing seed Agent, AgentTemplate, Harness, adapter image, WorkerPool, Substrate control plane and snapshot store. Mark the missing/denied component.
3. A gap table with requirement, observed evidence, PASS/FAIL/UNKNOWN/NOT RUN, owner and smallest next action.
4. A decision for each candidate path and its concrete prerequisite. If none fits current policy, say native execution is blocked and name the exact decision required.
5. Reviewable seed/config diffs for the recommended path, preserving existing approved integrations; otherwise provide the exact missing inputs required to prepare them.
6. A staged validation and rollback plan. Distinguish schema admission, reference resolution, runtime preparation, and a real model-backed turn.

After a deployment path is separately authorized, the completion proof must include current resource conditions and observed generations, actual worker/runtime image IDs, successful preparation, one completed model-backed session through the intended user route, and a representative approved read-only tool call if tools are required. Test persistence/suspend/resume only when that capability is claimed and the test is authorized. Never report successful native operation from a seed that merely passes validation, a placeholder WorkerPool, a healthy UI or a fixture that makes no model calls.

## Related references

The known reproduction bundle requires real worker capacity and packaged gVisor assets. It is evidence for that architecture, not evidence of a workerless deployment:
https://github.com/davidmarkgardiner/kagent-public/tree/main/work-agent-bundles/substrate-aks137-verified-20261014

Rolling BYO documentation explains that a BYO image still executes inside a Substrate actor. Check the pinned source before copying examples:
https://kagent.dev/docs/kagent/1.x/agents/bring-your-own-agent/

Use `01-VERIFY-UI-UPGRADE.md` to diagnose the frontend independently. Fixing frontend routing does not resolve this capacity/policy blocker.
