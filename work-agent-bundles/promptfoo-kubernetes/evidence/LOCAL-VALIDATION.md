# Local container evidence — 2026-10-06

Verified source and image boundaries:

- Upstream source inspected: `832173001f660cf15f5b59b250d52fd42ef72486`.
- Official image: Promptfoo 0.122.2, OCI index `sha256:e0eb45e5fd4ae8243f01c307b455285eb4ce9b420134bdc43a573c667e80e709`; registry inspection confirms arm64 and amd64 manifests.
- Derived image built locally for **linux/arm64**, with RUN networking disabled. Local Docker image ID/index: `sha256:726bbd241ec9284f436be24eaeb871ef3d4ab7b8f2ce1a9ffec95050efe608e7`. This is not an internal-registry digest.
- Image runtime: Node v24.20.0, Python 3.14.7, Promptfoo 0.122.2. No npm install is performed in this derived image. Earlier upstream eval-package Node engine constraints apply to its npm CI path; the direct CLI/custom-provider smoke ran on this image's existing runtime.
- All four AKS custom provider modules (skill, router, judge, baseline) loaded from the baked bundle with NODE_PATH=/app/node_modules. No model calls were made.

Runtime tests used Docker --network none and the container's configured UID/GID 1000:1000:

- Deterministic custom-provider fixture passed one case and wrote JSON/HTML plus SQLite history to a dedicated test volume.
- Deliberately wrong expected output returned CLI exit 100 and retained the failed-case JSON.
- Exact run-aks-evaluation wrapper passed the substituted synthetic quality case and propagated its passing result checker.
- The wrapper propagated a substituted failing routing case as exit 1 and retained JSON/HTML reports.
- A second concurrent CLI runner was rejected with exit 2 while the first held the evaluation lock. The wrapper cleaned up its lock after pass/fail. This does not serialize UI-created runs.
- Persistent server started, /health returned HTTP 200 with version 0.122.2, and /api/results returned the saved synthetic pass/fail history. History survived server restart using the same volume.
- Two manifest regression tests passed: one-replica/Recreate server, matching image in both alternatives, separated RWO storage, disabled API-token automount, pinned-image requirement and valid suite selection.
- Shellcheck passed. Public-safety scan passed.

The synthetic fixtures prove packaging, dependency loading, failure propagation, server startup and persistence. They do not measure model quality, internal gateway connectivity or live kagent behavior.

Not performed: linux/amd64 derivative build/runtime test, image import into the workplace registry, target Kubernetes server-side schema/admission check, real PVC permissions, authenticated UI ingress, internal CA/credential setup, or model-backed AKS evaluations. Nothing was deployed to a Kubernetes cluster.
