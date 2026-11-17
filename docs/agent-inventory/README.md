# Find and count agents on a Kubernetes cluster

Use pod names, container names, and image references to find unfamiliar agent
applications. Once you identify an application, count its pods using a confirmed
label selector. This works for standalone LangGraph applications, other custom
frameworks, and agents managed by kagent.

These commands only read Kubernetes resources. They query your current kubectl
context; this guide does not contain results from a live cluster.

## Configuration

You need `kubectl` and permission to list the relevant resources. JSON filtering
examples also require `jq`. Replace these placeholders with observed values:

| Placeholder | Meaning |
|---|---|
| `{{NAMESPACE}}` | Namespace containing the application |
| `{{POD_NAME}}` | A pod returned by the discovery command |
| `{{LABEL_SELECTOR}}` | Confirmed pod label selector, such as `app=example-agent` |
| `{{IMAGE_REFERENCE}}` | Complete image reference, including its tag or digest |

Confirm the context and enable pipeline error handling before counting:

```bash
kubectl config current-context
set -o pipefail
```

`pipefail` works in Bash and Zsh. If kubectl reports an error, the pipeline fails;
do not interpret a printed `0` as a successful inventory result.

## 1. Find agent pods and their images

List pod names, container names, and images across all namespaces:

```bash
kubectl get pods -A \
  -o custom-columns='NAMESPACE:.metadata.namespace,POD:.metadata.name,CONTAINERS:.spec.containers[*].name,IMAGES:.spec.containers[*].image'
```

Narrow the results using a recognisable application, framework, or image name:

```bash
kubectl get pods -A --no-headers \
  -o custom-columns='NAMESPACE:.metadata.namespace,POD:.metadata.name,CONTAINERS:.spec.containers[*].name,IMAGES:.spec.containers[*].image' \
  | grep -Ei 'langgraph|kagent|agent'
```

Replace the search terms with names you actually recognise. Framework names
may be absent from both pod names and image references, so no matches does not
prove that the framework is absent. With `pipefail`, grep also returns a nonzero
status when it finds no matches.

This output has one row per pod. A pod can contain several containers, including
sidecars; an image match alone does not prove that the application is an agent.
The image column shows the configured image reference, which may use an internal
mirror. These commands exclude init containers.

## 2. Inspect labels and the owner

```bash
kubectl get pod '{{POD_NAME}}' -n '{{NAMESPACE}}' --show-labels

kubectl get pod '{{POD_NAME}}' -n '{{NAMESPACE}}' \
  -o jsonpath='{range .metadata.ownerReferences[*]}{.kind}{"\t"}{.name}{"\n"}{end}'
```

For a Deployment-managed pod, the immediate owner is normally a ReplicaSet.
Check that ReplicaSet's owner if you need the Deployment identity. Other agents
may run under StatefulSets, Jobs, or other controllers.

Choose a selector from the pod's actual labels, for example `app=example-agent`
or `app.kubernetes.io/name=example-agent`. Confirm which pods it selects:

```bash
kubectl get pods -n '{{NAMESPACE}}' -l '{{LABEL_SELECTOR}}' --show-labels
```

Avoid selecting by `pod-template-hash`: it changes during Deployment rollouts.

## 3. Count the selected pods

Count pods whose phase is **Running**:

```bash
kubectl get pods -n '{{NAMESPACE}}' -l '{{LABEL_SELECTOR}}' \
  --field-selector=status.phase=Running --no-headers | wc -l
```

Running is a pod phase, not a health check. A Running pod can have an unready or
restarting container. To count only Running pods reporting **Ready**, excluding
pods marked for deletion:

```bash
kubectl get pods -n '{{NAMESPACE}}' -l '{{LABEL_SELECTOR}}' -o json \
  | jq '[.items[]
      | select(.metadata.deletionTimestamp == null)
      | select(.status.phase == "Running")
      | select(any(.status.conditions[]?;
          .type == "Ready" and .status == "True"))
    ] | length'
```

Replace `-n '{{NAMESPACE}}'` with `-A` for all namespaces, after checking that the
selector identifies the intended applications everywhere.

These are **pod counts**, not counts of distinct agent definitions, processes,
sessions, or models. One application can have multiple replicas, and a rollout
can temporarily increase its pod count. Readiness only reflects the configured
readiness checks; it does not prove a successful model or tool call.

## 4. Count by an exact image when labels are unavailable

```bash
kubectl get pods -A -o json \
  | jq --arg image '{{IMAGE_REFERENCE}}' \
    '[.items[]
      | select(.status.phase == "Running")
      | select(any(.spec.containers[]?; .image == $image))
    ] | length'
```

This counts each matching pod once, even if multiple containers match. It uses
the full configured image string, so different tags, digests, and registry
mirrors are separate matches. Several agents may share one image; an image
count therefore does not establish how many distinct agents exist.

## 5. Count kagent Agent resources separately

A standalone LangGraph or other custom application need not have a kagent
`Agent` resource. For an installation using the kagent 0.x `kagent.dev` API,
inspect and count Agent resources with:

```bash
kubectl get agents.kagent.dev -A
kubectl get agents.kagent.dev -A --no-headers | wc -l
```

Count only Agent resources reporting a Ready condition:

```bash
kubectl get agents.kagent.dev -A -o json \
  | jq '[.items[] | select(any(.status.conditions[]?;
      .type == "Ready" and .status == "True"))] | length'
```

If that resource type is unavailable, discover the installed API before assuming
there are no agents. Newer kagent APIs may use a different group or resource
model:

```bash
kubectl api-resources | grep -i agent
```

Regular Deployment-backed kagent agents run their runtime code in pods. The
standard kagent 0.x Python runtime image is `ghcr.io/kagent-dev/kagent/app`; the
Go runtime image is `ghcr.io/kagent-dev/kagent/golang-adk`. The installation
controls the version and can override the registry or image. BYO agents can
use custom images. Inspect the actual pod image instead of assuming a default.

The `kagent` namespace also contains supporting components, so counting every
pod there does not give the number of agents. Sandbox-backed execution also
has a different lifecycle; do not assume one ordinary pod per Agent resource.

## References

- Kubernetes pod phases and conditions: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- Kubernetes labels and selectors: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/
- kagent 0.x image configuration: https://kagent.dev/docs/kagent/0.x/introduction/installation/
- kagent 0.x Agent deployment and sandbox configuration: https://www.kagent.dev/docs/kagent/0.x/concepts/agents/
