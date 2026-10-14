# Bank evaluation: clean reinstall and smoke test

David has authorized replacement of the **dedicated kagent/Substrate
evaluation installation** with the verified newer pairing. This guide covers
that application stack. It does not request deletion of the AKS cluster,
node pool or infrastructure shared with other workloads.

## 1. Record the target and prove the prerequisites

Complete [`PREREQUISITES.md`](PREREQUISITES.md) and the transfer checks first.
Write a private `SUBSTRATE-WORK-PARITY.md` with observed values, matches,
differences and receipt links. Compare against the personal AMD64 AKS
evidence, including node image/kernel/containerd as well as the requested
VM, Kubernetes and component versions.

Record these private mappings before commands run:

| Setting | Work value |
| --- | --- |
| Named kube context / dedicated kubeconfig | `{{CONTEXT}}` / `{{KUBECONFIG_PATH}}` |
| Evaluation namespaces and Helm releases | `{{OWNED_NAMESPACES_AND_RELEASES}}` |
| Selected worker node/pool | `{{NODE_AND_WORKERPOOL}}` |
| Mirror image/digest mapping and credentials path | `{{PRIVATE_IMAGE_LOCK_AND_AUTH_PATH}}` |
| Runtime archive delivery / node cache mount | `{{APPROVED_DELIVERY_AND_MOUNT}}` |
| Storage endpoint, database owner and fresh snapshot prefix | `{{STORAGE_REFS_AND_PREFIX}}` |
| API issuer/discovery/JWKS and CA policy | `{{AUTHENTICATION_REFS}}` |
| Real approved ModelConfig and application route | `{{MODELCONFIG_AND_ROUTE}}` |
| Evidence location and backup references | `{{PRIVATE_RECEIPTS_AND_BACKUPS}}` |

Stop before deletion if required images/artifacts, permissions, identity
discovery or storage are unavailable. An internal registry tag or a node-cache
directory is not a substitute for the prerequisite proof.

## 2. Inventory and remove the old owned evaluation stack

Save the old failed receipts and the configuration required to recreate the
evaluation. Preserve approved credential/CA/model references and required
private backups. List every object to remove with namespace/name, owner and
UID, including Helm resources, agent CRs, workers, storage and old goldens.
Do not put Secret values in chat, the public repository or the source bundle.

Use this order in the private, environment-specific command sheet:

1. Stop only the evaluation callers/reconcilers that could recreate its old
   resources, using their desired configuration or GitOps source.
2. Delete the owned old agents/harnesses while their matching kagent
   controller is still running. Wait for normal cleanup finalizers and save
   the result. Never force-clear a finalizer to make the reinstall look clean.
3. Remove the old evaluation kagent release, then its owned workers and the
   dedicated Substrate runtime release after their lifecycle cleanup completes.
4. Reset only the evaluation's owned database/PVCs and snapshot prefixes that
   are listed for deletion. Preserve required backups and shared stores.
   Do not carry old Valkey state or old goldens into the new PostgreSQL backend.
5. Remove obsolete CRD releases, certificate/RBAC resources and namespaces
   only when inventory proves they have no consumers outside this evaluation.
   Otherwise leave shared definitions under their platform owner's control
   and use an isolated evaluation target.
6. Read back the owned object inventory. Confirm deletion or record the
   remaining dependency and stop. Logical object deletion is not proof that
   every externally retained snapshot or backup has been erased.

This is authorized evaluation cleanup. Once the prerequisites and ownership
are established, carry out that scope without another blanket permission
request. Ambiguous/shared resources remain outside it. Return a concrete
dependency blocker rather than broadening deletion to the rest of the cluster.

## 3. Reinstall the matching desired configuration

The public installers show the verified canonical namespace layout. The work
agent must adapt a private copy when actual names, issuer, registry or storage
differ, then review the rendered resources and record those differences.
Do not use the connected download steps from `REDEPLOY.md` inside the bank.

```bash
set -euo pipefail
cd '{{BUNDLE_DIR}}'
export PROOF_KUBECONFIG='{{DEDICATED_EVALUATION_KUBECONFIG}}'
export PROOF_TARGET=work
export PROOF_IMAGE_LOCK='{{PRIVATE_DIGEST_PINNED_IMAGE_LOCK}}'
export PROOF_SUBSTRATE_VALUES='{{PRIVATE_SUBSTRATE_VALUES}}'
export PROOF_KAGENT_VALUES='{{PRIVATE_KAGENT_VALUES}}'
bash ./prepare.sh --offline
bash ./install-stock.sh
bash ./install-kagent.sh
```

Use the pinned chart/CRD versions, source helpers and digest-equivalent images.
The bootstrap commands create the new CA pools and API issuer configuration
from this target. Do not copy lab keys. Ensure the seeded gVisor tree is
available before atelet can make a public fetch attempt, including on every
future worker node. Record the private actor-image authentication setup.

Create a fresh synthetic Agent, its generated golden and the two exact
counter templates. The public samples use a nonfunctional Ollama ModelConfig
for runtime reconciliation. Retain that distinction; use a separate synthetic
Agent with the approved real ModelConfig for the application smoke.

Import/push the transferred fixture using the bank-approved registry path.
For the disposable reference fixture registry, the upload helper is:

```bash
python3 push-fixture.py --registry '{{LOCAL_FIXTURE_REGISTRY_FORWARD_URL}}' \
  --archive artifacts/fixture.oci.tar > receipts/fixture-loaded.json
```

Apply the privately adapted `agent.yaml`, `proof-counter-full.json` and
`proof-counter-data.json` using the installed 1.x/API CLI. Wait for current
Agent conditions and fresh golden tags. Discover generated template names;
do not copy an AKS or Kind auto-generated name from the example receipts.

## 4. Run smoke before the benchmark

Follow [`SMOKE-TEST.md`](SMOKE-TEST.md). The runtime runner starts five fresh
actors and reuses the verified lifecycle assertion helper. It stops on the
first failure. Complete the real-model and disconnected-delivery checks
before reporting the bank stack as fully working.

After smoke passes, run ten fresh counter actors per mode using the commands
in `REDEPLOY.md`, with private values, the actual template names and new run
IDs. Retain raw samples and failed attempts; compare client location and RTT
before comparing operator-path timings with the home-lab numbers.

## 5. Return a private completion record

Return `SUBSTRATE-WORK-REDEPLOY.md` with the exact commands, cleanup inventory
and results; `SUBSTRATE-WORK-PARITY.md` with each match/difference; and
`SUBSTRATE-WORK-RESULTS.md` with smoke verdicts, benchmarks and receipt hashes.
Link this bundle's home/personal-AKS evidence as the reference, not as the
workplace outcome. If a gate fails, preserve its first failing command/API
receipt and report that blocker. Do not repair runtime source during this run.
