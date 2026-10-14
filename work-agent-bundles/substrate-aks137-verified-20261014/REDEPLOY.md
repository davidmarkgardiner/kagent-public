# Repeat the verified installation and demonstration

Use a fresh, approved disposable evaluation cluster. These sample installers
create cluster-wide CRDs, certificate signers and the standard `ate-system`,
`podcertificate-controller-system` and `kagent` namespaces. They are not a
cleanup script for an existing shared installation. The work agent must
produce its environment-specific cleanup plan first.

Prerequisites are Kubernetes 1.37 with the served PodCertificateRequest and
ClusterTrustBundle APIs, `kubectl`, Helm, Git, Go 1.27.0, Python 3 with
PyYAML, and the pinned chart/image/runtime assets. `prepare.sh` fetches public
inputs and builds only the stock operator/bootstrap helpers. The runtime
images are the released digest-pinned images, not local source builds.

## 1. Name the target and prepare the inputs

Copy this entire folder. Run the following in Bash and replace the private
kubeconfig placeholder. It must identify the dedicated evaluation target.
Neither installer modifies your default kubeconfig or installs a global CLI.

```bash
set -euo pipefail
cd '{{BUNDLE_DIR}}'
export PROOF_KUBECONFIG='{{DEDICATED_EVALUATION_KUBECONFIG}}'
export PROOF_TARGET=work
kubectl --kubeconfig "$PROOF_KUBECONFIG" get --raw=/version
kubectl --kubeconfig "$PROOF_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$PROOF_KUBECONFIG" api-resources --api-group=certificates.k8s.io
bash ./prepare.sh
```

On AKS the target must report version 1.37.0, `osSku: AzureLinux` and the
actual VM SKU. Compare its full node facts with the evidence, including
`Standard_D8s_v3`, node image, kernel and containerd. Do not infer the OS SKU
from a friendly cluster name. The local comparison used Kind 0.33.0 on an
ARM64 Docker VM; it does not establish AzureLinux host parity.

For a personal disposable AKS reproduction, the tested create inputs were:

```bash
az aks create \
  --resource-group '{{DEDICATED_RESOURCE_GROUP}}' \
  --name '{{DEDICATED_AKS_NAME}}' --location uksouth \
  --kubernetes-version 1.37.0 --os-sku AzureLinux \
  --node-vm-size Standard_D8s_v3 --node-count 1 --node-osdisk-size 64 \
  --tier free --enable-managed-identity --no-ssh-key \
  --network-plugin azure --network-plugin-mode overlay \
  --node-os-upgrade-channel None
```

The observed OS disk was Ephemeral. Node images may advance, so record the
actual image and any difference; a repeated version label is insufficient.
Do not run this provisioning block against an existing workplace cluster.

## 2. Install the matching version set

```bash
bash ./install-stock.sh
bash ./install-kagent.sh
kubectl --kubeconfig "$PROOF_KUBECONFIG" -n kagent get workerpools -o yaml
kubectl --kubeconfig "$PROOF_KUBECONFIG" get pods -A
```

Expect Ready Substrate components, a Ready kagent controller, and one Ready
`gvisor` worker. The stock `ate-setup create` commands create the required CA
pools and issuer configuration before Helm waits for the workloads. Run the
helper from the pinned source directory, as the installer does. The bootstrap
creates the certificate namespace; the installer assigns that **new lab
namespace** to the Substrate Helm release before Helm installs it.

Raw output goes under ignored `receipts/`. The values files deliberately omit
MCP servers and use a nonfunctional Ollama endpoint. No real model is needed
for the runtime-only demonstration. Use approved workplace storage,
credentials and CA policy for a real deployment, and record those differences.

## 3. Load the exact synthetic fixture

Download `fixture.oci.tar` from the release, verify its SHA-256 and deploy
the disposable internal registry. This is only the fixture distribution
path; it does not replace the gVisor runtime or prove an air gap.

```bash
gh release download substrate-aks137-proof-20261014 \
  --repo davidmarkgardiner/kagent-public --pattern fixture.oci.tar --dir artifacts
python3 - <<'PY'
import hashlib, json
from pathlib import Path
expected = json.loads(Path('fixture-archive-lock.json').read_text())['sha256']
assert hashlib.sha256(Path('artifacts/fixture.oci.tar').read_bytes()).hexdigest() == expected
print('Exact tested fixture archive verified')
PY
kubectl --kubeconfig "$PROOF_KUBECONFIG" apply -f fixture-registry.yaml
kubectl --kubeconfig "$PROOF_KUBECONFIG" -n substrate-proof \
  rollout status deployment/fixture-registry --timeout=120s
```

In a second terminal keep this forward open:

```bash
kubectl --kubeconfig '{{DEDICATED_EVALUATION_KUBECONFIG}}' -n substrate-proof \
  port-forward service/fixture-registry 15014:5000
```

Return to the first terminal:

```bash
python3 push-fixture.py --registry http://127.0.0.1:15014 \
  --archive artifacts/fixture.oci.tar > receipts/fixture-loaded.json
```

Expect the same OCI index digest as `fixture-image-lock.json`. The stock
atelet option in `substrate-values.yaml` maps this fixture's loopback registry
reference to the disposable in-cluster service. It is the same option in
both verified environments. Do not use this unauthenticated HTTP fixture
registry as the workplace production registry.

## 4. Generate the agent and discover its actual template name

```bash
kubectl --kubeconfig "$PROOF_KUBECONFIG" apply --dry-run=server -f agent.yaml
kubectl --kubeconfig "$PROOF_KUBECONFIG" apply -f agent.yaml
kubectl --kubeconfig "$PROOF_KUBECONFIG" -n kagent \
  wait agent.api.kagent.dev/substrate-stock-proof --for=condition=Ready --timeout=180s
./bin/kubectl-ate --kubeconfig "$PROOF_KUBECONFIG" \
  get actor-templates -a kagent -o json > receipts/generated-templates.json
```

Choose the generated `substrate-stock-proof-*` template from that inventory
and copy its exact name into step 5. Verify its golden tag and snapshot
policy. In this version ActorTemplates live in the Substrate API; they are
not Kubernetes ActorTemplate CRs. An API or permission error is UNKNOWN.

Create the two fixture templates on this fresh target, then wait for each
golden before testing it:

```bash
./bin/kubectl-ate --kubeconfig "$PROOF_KUBECONFIG" create actor-template -f proof-counter-full.json
./bin/kubectl-ate --kubeconfig "$PROOF_KUBECONFIG" create actor-template -f proof-counter-data.json
for mode in full data; do
  python3 wait-golden.py --cli ./bin/kubectl-ate --kubeconfig "$PROOF_KUBECONFIG" \
    --template "proof-counter-$mode" --receipt "receipts/golden-$mode.json"
done
```

## 5. Run the short demo, then the benchmark

In a third terminal keep the router forward open:

```bash
kubectl --kubeconfig '{{DEDICATED_EVALUATION_KUBECONFIG}}' -n ate-system \
  port-forward service/atenet-router 18014:80
```

In the first terminal, use a fresh suffix and the actual generated template:

```bash
export PROOF_RUN="$(date -u +%Y%m%d%H%M%S)-$$"
export PROOF_ADK_TEMPLATE='{{ACTUAL_GENERATED_TEMPLATE}}'
python3 verify-lifecycle.py --cli ./bin/kubectl-ate --kubeconfig "$PROOF_KUBECONFIG" \
  --router http://127.0.0.1:18014 --template "$PROOF_ADK_TEMPLATE" \
  --prefix "work-adk-$PROOF_RUN" --actors 3 --workload adk \
  --evidence "receipts/$PROOF_RUN/adk"
for mode in full data; do
  python3 verify-lifecycle.py --cli ./bin/kubectl-ate --kubeconfig "$PROOF_KUBECONFIG" \
    --router http://127.0.0.1:18014 --template "proof-counter-$mode" \
    --prefix "work-$mode-$PROOF_RUN" --actors 10 --workload counter \
    --evidence "receipts/$PROOF_RUN/$mode"
done
```

For a quick visual check, use `--actors 1` for each counter mode first. The
fixture responses must be memory/file `1/1, 2/2, 3/3` for Full and
`1/1, 1/2, 1/3` for Data, with the same synthetic marker and actor UID.
The script verifies the local pause checkpoint, external commit snapshot,
worker assignment/release and unchanged template. It stops on failure and
writes a failing `result.json`. Use a new prefix and receipt directory for
any separately justified rerun; retain every previous result.

`benchmark.json` records each sample and its scope. Do not compare these
numbers with an advertised pure-runtime latency or call them a load test.
Record the VM, client location and resource samples alongside the timings.

## 6. Inspect and clean up the owned evaluation resources

```bash
./bin/kubectl-ate --kubeconfig "$PROOF_KUBECONFIG" get actors -a kagent -o json
kubectl --kubeconfig "$PROOF_KUBECONFIG" -n kagent get workerpools -o yaml
```

Expect this run's actors Suspended with no worker assignment. Save their
names/UIDs from `created-actors.json`. Delete only those verified owned actors
using `kubectl-ate delete actor NAME -a kagent`, and remove only the synthetic
Agent you created. Keep the controller running for its cleanup. Namespace,
database, snapshot and cluster teardown must follow the work agent's scoped
plan. Object deletion alone does not prove all retained snapshots were erased.
