# Verify the workplace kagent UI upgrade

Prepared 2026-10-16. Hand this entire file to the workplace agent.

## Task and scope

Determine which frontend the user's existing browser URL actually serves, whether it matches the intended kagent `1.0.0-alpha8` deployment, and which upgrade gaps remain. The UI reportedly looks identical to the previous installation.

Start with read-only discovery. You may inspect the workplace repository, rendered manifests, installed schemas, release metadata, routes, pod images, scoped logs and browser network requests. A temporary port-forward for read-only comparison is appropriate if allowed locally. Do not upgrade, restart, apply manifests, alter routes or policy, send chat messages, create sessions, or change existing agents as part of this audit. Prepare proposed fixes as reviewable local diffs.

Keep raw evidence in an approved private location. Do not export credentials, cookie values, auth headers, Secret objects, private infrastructure identifiers or conversation content into a public report. Record missing permissions as UNKNOWN rather than treating them as proof of absence.

## Verified reference baseline

The Substrate work bundle pins kagent and its CRDs to `1.0.0-alpha8`, paired with Substrate `0.4.0-alpha1`. This is a specific prerelease, not a claim about the latest available release.

The bundle separately lists the controller, UI and Go ADK images. Its expected UI image is:

```text
ghcr.io/kagent-dev/kagent/ui:1.0.0-alpha8
```

The recorded Linux AMD64 UI manifest digest is:

```text
sha256:792430c2dd2003de7cdce94ee47ce4577843a705cdfdb1302c969d50025e1905
```

An internal mirror may have a different repository name. Compare platform manifests with platform manifests, not a multi-platform index with a platform manifest. If an approved rebuild or transformation changes the digest, require its provenance and source revision before declaring equivalence.

Reference image checklist:
https://github.com/davidmarkgardiner/kagent-public/blob/main/work-agent-bundles/substrate-aks137-verified-20261014/IMAGE-IMPORT.md

Reference digest list:
https://github.com/davidmarkgardiner/kagent-public/blob/main/work-agent-bundles/substrate-aks137-verified-20261014/images-linux-amd64.txt

## 1. Establish the actual installation

Discover the context, namespace, Helm release or GitOps owner, frontend URL, and controller endpoint. Do not assume the release or namespace is named `kagent`. Identify whether the old installation and the new evaluation coexist.

Report controller, UI, runtime, chart and CRD versions separately. A CLI version, chart label or controller log alone does not prove the frontend version. Inspect image IDs from running containers as well as desired Deployment images, including every serving replica and its rollout revision.

Useful read-only commands after setting the discovered values:

```bash
export WORK_CONTEXT='{{WORK_CONTEXT}}'
export WORK_NAMESPACE='{{WORK_NAMESPACE}}'
kubectl --context "$WORK_CONTEXT" -n "$WORK_NAMESPACE" get deployments,pods,services -o wide
kubectl --context "$WORK_CONTEXT" -n "$WORK_NAMESPACE" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.containerStatuses[*]}{.name}{"\t"}{.image}{"\t"}{.imageID}{"\n"}{end}{end}'
```

Use the explicit context on all later Kubernetes and Helm commands. Inspect only the required Helm values and manifest fields privately. Avoid dumping all release values into the report because they may contain credentials.

## 2. Trace the user's URL to serving pods

Trace the actual route in order:

1. Browser URL and any redirects or sub-path.
2. Reverse proxy, authentication proxy, Ingress or Gateway route.
3. Backend Service and port.
4. EndpointSlices and their target pods.
5. Each pod's owner, image ID and readiness.

Check whether the route points to an older release, a separate namespace, a stale Service selector, or mixed old/new replicas. Verify controller/API routing separately from frontend routing. Record the chain with private identifiers replaced by consistent placeholders in the shareable report.

Compare the routed frontend with a temporary direct connection to the discovered UI Service or pod. A direct connection helps isolate proxy/cache differences. If authentication or base-path assumptions make that comparison invalid, explain the limitation rather than disabling authentication.

## 3. Check rendered image selection and frontend assets

Compare the desired GitOps configuration, rendered chart, live Deployment and running image. Record any drift and identify the configuration owner that would overwrite a manual fix.

In the stock Alpha 8 chart, UI tag selection is the first nonempty value of top-level `tag`, `ui.image.tag`, then `Chart.Version`. Global image registry settings can also override the image registry. Inspect the installed chart's helpers, image rewrite rules and admission mutations; do not assume changing `ui.image.tag` alone would take effect.

Check the page HTML and loaded JavaScript URLs without copying auth material. The stock Alpha 8 frontend is a Vite static application served by nginx. It uses `/assets/` and `env-config.js`; the older frontend used Next.js assets such as `/_next/`. These are useful clues, not standalone version proof. A custom workplace build may change paths.

Compare a hard reload or private browser window with the direct frontend response. Check response cache headers, HTML asset references and proxy caching. Do not purge a shared cache or change routing during diagnosis. Inspect only the necessary runtime configuration fields and confirm the UI talks to the intended controller.

Pinned image helper source:
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/helm/kagent/templates/_helpers.tpl

Frontend rewrite and proxy migration notes:
https://github.com/kagent-dev/kagent/pull/2569

## 4. Verify visible changes without requiring a functioning worker

Use the pinned Alpha 8 source and the deployed build to check the following. Navigation may differ in a custom extension or under RBAC.

| Check | Evidence to record |
| --- | --- |
| Agent definitions and templates | Presence and read-only loading of `/agents` and `/agent-templates`; relevant API errors |
| Harness configuration | Harness selection/details exposed by agent/template forms; inspect without saving |
| Substrate inventory | `/substrate` loads, reports empty capacity, or returns a specific error |
| Schedules | `/schedules` is available or has a documented visibility restriction |
| Existing chat actions | Checkpoint/snapshot and fork controls where supported by the existing session/runtime; do not invoke them |
| API compatibility | Failed gRPC-Web requests, authentication errors or missing methods, correlated with the intended controller |

Do not mark frontend mismatch solely because no workers, agents, sessions or snapshots exist. A confirmed Alpha 8 UI can coexist with a blocked native runtime. Conversely, an empty screen or healthy controller does not establish UI parity. Treat controls absent because of RBAC, custom extensions or unsupported session state separately from old frontend assets.

Pinned route definitions:
https://github.com/kagent-dev/kagent/blob/v1.0.0-alpha8/ui/src/router/routes.ts

UI additions recorded upstream:
https://github.com/kagent-dev/kagent/releases/tag/v1.0.0-alpha1
https://github.com/kagent-dev/kagent/releases/tag/v1.0.0-alpha5

## Required output

Write `UI-UPGRADE-FINDINGS.md` in the approved private workspace with:

- A verdict of MATCH, MISMATCH or UNKNOWN for the frontend, supported by the URL-to-pod chain and image provenance.
- Separate findings for frontend build, controller/API compatibility, routing/cache, and runtime availability.
- A table of expected value, observed value, evidence location, verdict and next action for every gap.
- Proposed minimal repository/configuration diffs, their configuration owner, validation and rollback plan. Do not apply them in this task.
- The exact smallest next action and any required owner decision. Do not call this end-to-end agent success without a separately authorized completed conversation.

If the Harness/WorkerPool blocker is present, use `02-RESOLVE-HARNESS-WORKERPOOL-BLOCKER.md` for its independent investigation.
