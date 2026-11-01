# Bootstrap Substrate locally with Go 1.27

Give this entire file to the work agent. It contains the instructions for
building the stock bootstrap helper, repairing the missing certificate
signer pools, checking other bootstrap resources and collecting results.
The 299 MB `substrate-prerequisites.tar.gz` is not required for this route.

## Scope and prerequisites

The reported failure is a running certificate controller with no
`service-dns-ca-pool`. The controller needs its CA pools to issue the
certificates that Substrate pods mount through projected volumes. Mirrored
images, snapshots and CRDs do not generate these signing keys.

This procedure is for the dedicated evaluation installation using:

| Component | Required version |
| --- | --- |
| Substrate and Substrate CRDs | `0.4.0-alpha1` |
| Substrate source commit | `c2e2e130606db615a553421b6352e47f49860870` |
| kagent and kagent CRDs | `1.0.0-alpha8` |
| Local Go toolchain | `1.27.0` or a compatible `1.27.x` patch release |

Do not use these commands for the older Substrate `0.0.9` / kagent `0.10.x`
pairing. Confirm the installed releases and rendered Secret references first.

The operator machine needs the matching source **including `vendor/`**, Go,
`kubectl`, Bash and access to the intended Kubernetes context. No OpenSSL,
Python, `kubectl-ate`, container build or public Go module download is needed
for these bootstrap commands. Go alone is insufficient without the source
and dependencies.

This replaces the bootstrap-helper part of the large archive only. It does
not supply missing runtime images, the gVisor archive, storage, snapshots or
registry credentials. Preserve the existing mirrored deployment. Do not
reinstall the stack, delete resources, rotate existing keys or change policy
to get past this blocker.

## 1. Locate and verify the source

Use the source checkout already available inside the bank if it matches the
commit above. For a transferred source tree without Git metadata, verify it
against its approved source archive checksum and recorded commit instead.
Do not claim an unverified tree matches the pin.

If an approved machine can reach GitHub and the source is missing, obtain
only the source checkout. This step is optional and requires network access;
the build in the next section does not.

```bash
git clone --depth 1 --branch v0.4.0-alpha1 \
  https://github.com/kagent-dev/substrate.git substrate-source
```

Run the following in Bash from the verified source root, retaining this
shell for the later commands:

```bash
set -euo pipefail
umask 077

go version
# Confirm Go 1.27.x before continuing.
test -f vendor/modules.txt
test -f cmd/ate-setup/main.go

# For a Git checkout, both checks must pass.
test "$(git rev-parse HEAD)" = c2e2e130606db615a553421b6352e47f49860870
git diff --exit-code HEAD
```

Do not change `go.mod` to force an older compiler to accept this source.
If source or vendored dependencies are missing, report that exact missing
input. Do not fall back silently to internet module downloads.

## 2. Build only the bootstrap helper

```bash
GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off CGO_ENABLED=0 \
  go build -mod=vendor -o ./ate-setup ./cmd/ate-setup

./ate-setup --help
./ate-setup create --help
```

`GOTOOLCHAIN=local` prevents automatic toolchain downloads. Vendoring and the
disabled module proxy make a missing dependency fail locally. The help
commands do not bootstrap or deploy anything. Keep running the helper from
the source root because its configuration loader locates repository files.

This is a native build for the operator machine. The helper talks to the
Kubernetes API; it does not need to match the cluster nodes' architecture.

## 3. Select the target and repair the reported CA blocker

Replace every placeholder below with private, verified values. Keep the
actual kubeconfig, identifiers and receipts inside the bank.

```bash
export BOOTSTRAP_KUBECONFIG='{{KUBECONFIG_PATH}}'
export BOOTSTRAP_CONTEXT='{{CONTEXT}}'
export ATE_NAMESPACE='{{ACTUAL_SUBSTRATE_NAMESPACE}}'

k() {
  kubectl --kubeconfig "$BOOTSTRAP_KUBECONFIG" \
    --context "$BOOTSTRAP_CONTEXT" "$@"
}
setup() {
  ./ate-setup --kubeconfig "$BOOTSTRAP_KUBECONFIG" \
    --context "$BOOTSTRAP_CONTEXT" --no-dev-env "$@"
}

k get --raw=/version
k get namespace "$ATE_NAMESPACE" podcertificate-controller-system
k -n podcertificate-controller-system get secrets \
  service-dns-ca-pool pod-identity-ca-pool --ignore-not-found

# Creates missing signer pools. Existing pools are preserved.
setup create podcertificate-controller-cas

# Print only types and key names, never Secret values.
k -n podcertificate-controller-system get secrets \
  service-dns-ca-pool pod-identity-ca-pool \
  -o go-template='{{range .items}}{{.metadata.name}} type={{.type}} keys={{range $key, $value := .data}}{{$key}} {{end}}{{"\n"}}{{end}}'
```

The pinned helper uses `podcertificate-controller-system` for these two
signer pools, independently of `ATE_NAMESPACE`. If the deployed controller
references a different namespace or Secret name, stop and reconcile that
configuration difference rather than creating unused keys.

Each CA pool Secret must have type `kubernetes.io/tls` and keys `pool`,
`tls.crt` and `tls.key`. New roots are generated locally with a one-year
validity. Existing Secrets are preserved by the helper, even if incomplete;
an existence check is not proof of valid contents. Report malformed pools
for a deliberate repair rather than deleting or replacing them.

`--no-dev-env` prevents sourcing a local `.ate-dev-env.sh`. Exported process
environment still applies, so use a clean operator shell and review inherited
`ATE_*`, `EXPECTED_JWT_ISSUER` and cloud project/location settings privately.

## 4. Check the remaining bootstrap resources

If further pods report missing bootstrap Secrets, inventory them first:

```bash
k -n "$ATE_NAMESPACE" get secrets \
  actor-id-jwt-pool actor-id-ca-pool actor-id-ca-certs \
  egress-mitm-ca-pool --ignore-not-found
k -n "$ATE_NAMESPACE" get configmap ate-api-authentication --ignore-not-found
```

Use the following commands only when these resources are required by the
installed manifests. The three pool commands preserve existing pools:

```bash
setup create jwt-authority-pool
setup create actor-id-ca-pool
setup create egress-mitm-ca-pool

# Create the trust-only bundle only if it is absent. Errors stop the script.
actor_ca_bundle=$(k -n "$ATE_NAMESPACE" get secret actor-id-ca-certs \
  --ignore-not-found -o name)
if [[ -z "$actor_ca_bundle" ]]; then
  setup create actor-id-ca-certs
fi
```

The actor and pod-controller CAs use Ed25519. The egress MITM CA and JWT
authority use ECDSA P-256; the JWT authority uses ES256. Let the stock helper
write their exact pool formats. An arbitrary TLS Secret or base64-encoded
PEM file is not a substitute for a serialized pool.

The CA pools require `pool`, `tls.crt`, `tls.key`; `actor-id-jwt-pool` requires
`pool`; `actor-id-ca-certs` requires `ca.crt`. In particular, egress also
mounts the TLS keys directly. Do not copy signing keys from the lab.

For API authentication, preserve an existing reviewed configuration. The
helper's `create api-authentication-config` command **applies and can replace**
the ConfigMap; it does not have the pools' preserve-existing behavior.

If `ate-api-authentication` is absent, inspect the selected cluster's service
account issuer using this read-only discovery request:

```bash
k get --raw=/.well-known/openid-configuration
```

Confirm that issuer against the intended projected tokens and API settings.
The pinned helper defaults the audience to `api.ate-system.svc`. If the
deployment uses a different audience or namespace, prepare the matching
reviewed authentication configuration instead of running this default
command. `ATE_NAMESPACE` changes the destination namespace, not that audience.

For the canonical audience only, set the confirmed issuer and create the
ConfigMap only if absent:

```bash
export EXPECTED_JWT_ISSUER='{{VERIFIED_SERVICE_ACCOUNT_TOKEN_ISSUER}}'
api_auth_config=$(k -n "$ATE_NAMESPACE" get configmap ate-api-authentication \
  --ignore-not-found -o name)
if [[ -z "$api_auth_config" ]]; then
  setup create api-authentication-config
fi
```

If discovery is unavailable, obtain the issuer from the platform owner.
Do not guess an AKS issuer or accept the helper's fallback as verified.

## 5. Verify certificate issuance and runtime progress

```bash
k api-resources --api-group=certificates.k8s.io
k -n podcertificate-controller-system get pods
k -n podcertificate-controller-system logs \
  '{{CERTIFICATE_CONTROLLER_POD}}' --all-containers --tail=100
k get podcertificaterequests.certificates.k8s.io -A
k get clustertrustbundles.certificates.k8s.io
k -n "$ATE_NAMESPACE" get pods
k -n "$ATE_NAMESPACE" describe pod '{{PREVIOUSLY_BLOCKED_POD}}'
```

Use the actual pod name from `get pods`. Read issuance conditions and pod
events, and confirm the former missing-pool error has stopped, requests are
issued, trust bundles are present and certificate mounts succeed. A Running
controller alone does not prove certificate issuance. An absent API resource
is a separate prerequisite failure to report, not an empty success result.

Allow reconciliation and mount retries to progress. Do not restart everything
automatically. If a targeted rollout is still needed, use the evaluation's
existing delivery path after identifying the specific stale workload.

Once projections succeed, verify the affected workload's Ready conditions and
continue the existing runtime smoke test. Any image, storage, gVisor,
authentication or application failure remains a separate blocker.

## Return this result privately

Report the Go version, source commit or approved archive verification,
offline build result, exact target context and namespaces, resources created
versus preserved, current certificate-request conditions, projected-mount
events and workload readiness. Include the first remaining failing command
and error if progress stops. Do not print Secret values, private keys or
service-account tokens in chat or commit them to Git.

These instructions were checked against the pinned upstream source. No
local Go 1.27 build or bank-cluster execution is claimed by this document.

## Pinned upstream references

- Toolchain and dependencies: https://github.com/kagent-dev/substrate/blob/c2e2e130606db615a553421b6352e47f49860870/go.mod
- Vendored dependency lock: https://github.com/kagent-dev/substrate/blob/c2e2e130606db615a553421b6352e47f49860870/vendor/modules.txt
- Bootstrap implementation and preserve-existing behavior: https://github.com/kagent-dev/substrate/blob/c2e2e130606db615a553421b6352e47f49860870/cmd/ate-setup/internal/steps/create.go
- Bootstrap command names: https://github.com/kagent-dev/substrate/blob/c2e2e130606db615a553421b6352e47f49860870/cmd/ate-setup/internal/cmd/create.go
- Flags and environment handling: https://github.com/kagent-dev/substrate/blob/c2e2e130606db615a553421b6352e47f49860870/cmd/ate-setup/internal/config/config.go
