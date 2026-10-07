# Promptfoo in Kubernetes: persistent UI or on-demand evaluation

Two alternatives use the same image. Neither needs a GitLab pipeline. The persistent Deployment is an evaluation workbench: run the reviewed suites manually in its container and inspect their saved results in the browser. The Job runs a selected suite once and exits with its verdict.

This bundle extends `../aks-skills-specialists`. It evaluates prompts/models against the mounted skill text. It does not automatically call kagent A2A or consume a kagent ModelConfig; an A2A provider and trajectory assertions remain additional work for end-to-end agent evaluation.

## Container choices

For a general Promptfoo UI you can mirror the official prebuilt image, with no source build required:

`ghcr.io/promptfoo/promptfoo:0.122.2@sha256:e0eb45e5fd4ae8243f01c307b455285eb4ce9b420134bdc43a573c667e80e709`

The index was verified to include linux/amd64 and linux/arm64. The amd64 child digest is `sha256:73dbb537b837bcc17202ef38d9263d6dfba1974ae641df54bd68b940177d06e4`; arm64 is `sha256:ea4e3d8895f18548791bb845b67031827a6852cd23a5f5d2543af9bd2bad71e6`.

For our exact AKS suites, build the small derived image in this bundle. It adds the reviewed skills/tests and a manual runner; it inherits Promptfoo's server/CLI and installed dependencies. No npm install or GitHub download happens at container startup. This image is for evaluations, not the full earlier CI contract-validation toolchain (Kyverno/shellcheck/Vally are not added).

Connected-side build, from the kagent-public repository root:

```bash
docker build --platform linux/amd64 \
  -f work-agent-bundles/promptfoo-kubernetes/Dockerfile \
  -t promptfoo-aks-evals:0.122.2 .
docker save -o /absolute/path/promptfoo-aks-evals-amd64.tar promptfoo-aks-evals:0.122.2
shasum -a 256 /absolute/path/promptfoo-aks-evals-amd64.tar
```

Use linux/arm64 instead for an ARM cluster. Transfer the image archive through your approved process, load it on the internal side, tag/push it into the internal registry, and use the **internal registry digest** in Kubernetes. Transfer this manifest/source bundle separately. Dockerfile-specific ignore rules exclude unrelated working-tree content and local dependencies.

## Environment configuration

Create/provision the model credential Secret out of band in namespace `promptfoo-evaluation`. For the supplied OpenAI-compatible configuration it contains `OPENAI_API_KEY`. Supply your existing approved agentgateway route/model endpoint and its authentication; do not reuse an arbitrary model key. A keyless internal model can use an existing empty Secret if that endpoint explicitly allows it. Never commit real keys.

Copy `values.example.json` outside Git. Fill the imported image digest, internal HTTPS model base URL (commonly ending in `/v1`), evaluated deployment, fixed judge deployment, Secret name and StorageClass. The model/judge can match the deployments used by your agents, but these are explicit evaluation settings. For native Azure/Foundry endpoints, adapt the env block to the vendored client's matching backend; do not pretend it is an OpenAI-compatible route.

```bash
python3 scripts/render.py /private/path/values.json /private/path/rendered
```

All examples below refer to the rendered directory. Use an explicit, reviewed non-production Kubernetes context. For permanent installation, put the rendered manifests into the existing Flux delivery path instead of relying on manual apply. The example namespace, ServiceAccount and PVCs are new; do not overwrite existing resources with those names.

Internal PKI: mount the approved CA bundle and set `NODE_EXTRA_CA_CERTS` to its path. Do not disable TLS verification. Configure existing image-pull credentials if your internal registry requires them. The manifests have no Ingress; use port-forward initially or your authenticated ingress/proxy for team access. Apply an environment-owned NetworkPolicy allowing only internal DNS, the approved model gateway and authorized UI clients.

## Alternative A: persistent UI/workbench (recommended for interactive use)

The resources are a single-replica Deployment, ClusterIP Service and a 10 GiB RWO PVC. Deployment strategy is Recreate to avoid two server Pods sharing SQLite during rollout. Disable autoscaling. Data, history and HTML/JSON exports are stored in `/data`. The ServiceAccount cannot mount a Kubernetes API token. Resources start at 500m CPU/1 GiB RAM, with limits of 2 CPU/4 GiB; measure your suite's actual needs.

```bash
kubectl --context CONTEXT apply -f /private/path/rendered/common.yaml
kubectl --context CONTEXT apply -f /private/path/rendered/server.yaml
kubectl --context CONTEXT -n promptfoo-evaluation rollout status deployment/promptfoo
kubectl --context CONTEXT -n promptfoo-evaluation port-forward service/promptfoo 3000:3000
```

Open http://localhost:3000 . You can use the eval creator for new prompts and comparisons. For the exact versioned AKS suite, open another terminal and run:

```bash
kubectl --context CONTEXT -n promptfoo-evaluation exec deployment/promptfoo -- run-aks-evaluation quality
kubectl --context CONTEXT -n promptfoo-evaluation exec deployment/promptfoo -- run-aks-evaluation routing
kubectl --context CONTEXT -n promptfoo-evaluation exec deployment/promptfoo -- run-aks-evaluation baseline
```

Run one suite at a time and wait for it to finish before triggering another from the UI or CLI. Refresh the UI to see new saved evals. The CLI runner serializes its own calls with an atomic directory lock; this does not serialize browser-created runs. Failed cases return a nonzero exit code but preserve their reports. Baseline is a measurement, not a promotion gate.

The server manifest mounts `ui-providers.yaml` from a ConfigMap into `/data`, listing the configured internal provider. Extend that reviewed ConfigMap if you need more internal model choices. For example, configure an `openai:chat:MODEL_DEPLOYMENT` provider with `config.apiBaseUrl` pointing at the internal gateway and credential supplied via environment. This restricts the provider menu, not network authorization. Restart the server when the provider menu changes. Do not put keys in the file. Our AKS CLI uses the explicit EVAL_* variables regardless of the UI menu.

Open-source self-hosting has no built-in authentication/SSO/RBAC and is documented for individual/experimental use. Keep it internal and behind your existing authentication when exposed. SQLite and in-memory job state require one replica; restarts can interrupt browser-launched runs. Use an approved enterprise deployment for a production multi-team service rather than scaling this Deployment.

## Alternative B: manually launched Kubernetes Job

This is a Job you launch yourself, not a pipeline requirement. It runs `run-aks-evaluation quality` (or routing/baseline selected in the values file). It has no Service or browser server. Retries are disabled so a failed evaluation does not automatically spend more model calls. The run gets one hour and writes the Promptfoo database and JSON/HTML exports to a **separate** PVC.

```bash
kubectl --context CONTEXT apply -f /private/path/rendered/common.yaml
kubectl --context CONTEXT apply -f /private/path/rendered/job-storage.yaml
kubectl --context CONTEXT create -f /private/path/rendered/job.yaml
# Use the generated Job name printed by create:
kubectl --context CONTEXT -n promptfoo-evaluation logs -f job/JOB_NAME
kubectl --context CONTEXT -n promptfoo-evaluation get job JOB_NAME
```

A completed Job indicates a passing selected suite; a failed Job can indicate failed cases or an infrastructure/model error, which must be distinguished from the reports. Outputs remain on `promptfoo-run-data` after the Pod exits. Start a temporary reviewer/server with that PVC after the Job has released it, or copy its exports from a temporary read-only reader Pod to your existing internal artifact store. `kubectl cp` cannot copy files from an already terminated evaluation container.

Run one Job at a time against this RWO PVC. For concurrent experiments, use a separate PVC/output location per Job. Do not mount the persistent UI's active SQLite PVC into an independent Job. Job results do not automatically appear in the UI's separate database; import/export them through Promptfoo or use your internal artifact store. Do not delete a PVC until its reports have been retained.

## Red teaming alongside normal evaluation

Red teaming deliberately tries to make an agent break its rules: for example, a log injection requesting Secrets, an urgent node-drain request to a read-only agent, or a request for another team's namespace data. Successful defense requires both a safe response and evidence that no unauthorized tool action occurred.

See [the red teaming scenarios and release process](../aks-skills-specialists/EVALUATION.md#red-teaming-deliberately-test-unsafe-behavior) for the AKS acceptance cases, evidence requirements and air-gap considerations. Promptfoo can help generate and score adversarial inputs, but the included `quality`, `routing` and `baseline` commands are not a dedicated red-team suite. Testing real kagent behavior still requires an A2A provider and tool-trajectory assertions. No red-team run has been completed by this bundle.

## Air-gap acceptance

Both modes have telemetry and update checks disabled and the wrapper passes `--no-share`. Both the evaluated model and judge must be reachable inside the boundary. Credentials and CA roots are provisioned internally, not baked into the image. Copilot-based upstream tests are not part of this runner.

Verify the exact imported image and startup with public egress blocked. First run the deterministic synthetic fixture with no network to prove the CLI, custom-provider loader and result persistence. Then run a small approved internal-model case before the full suites. A no-network synthetic PASS does not prove internal model connectivity, kagent behavior, or workplace performance.

Source references:

- https://www.promptfoo.dev/docs/usage/self-hosting/
- https://www.promptfoo.dev/docs/usage/command-line/
- https://www.promptfoo.dev/docs/configuration/telemetry/
- https://github.com/promptfoo/promptfoo/tree/832173001f660cf15f5b59b250d52fd42ef72486/helm/chart/promptfoo

An experimental upstream Helm chart is available. It hardcodes a small env block, resource defaults and PVC names, so these manifests make the required runtime settings explicit. No target cluster has been installed by this bundle.
