# MIL-128 POC Evidence

Date: 2026-05-13
Workspace: `/home/david/code/symphony-workspaces/MIL-128/kagent-public`
Branch: `symphony/MIL-128-kagent-knowledge-ui`

## Unit Smoke Tests

Command:

```bash
cd agents/kagent-knowledge-ui
PYTHONPATH=app python3 -m unittest discover -s tests -v
```

Output:

```text
test_required_queries_return_grounded_answers (test_smoke.KAgentKnowledgeSmokeTest.test_required_queries_return_grounded_answers) ... ok
test_stale_doc_feedback_can_open_simulated_pr (test_smoke.KAgentKnowledgeSmokeTest.test_stale_doc_feedback_can_open_simulated_pr) ... ok
test_unknown_query_uses_ticket_fallback (test_smoke.KAgentKnowledgeSmokeTest.test_unknown_query_uses_ticket_fallback) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.004s

OK
```

## Local UI/API Smoke

Server command:

```bash
cd agents/kagent-knowledge-ui
PYTHONPATH=app KB_LOCAL_PATH="$(git rev-parse --show-toplevel)" \
  EVIDENCE_DIR="$(git rev-parse --show-toplevel)/docs/poc-evidence" \
  uvicorn kagent_knowledge_ui.api:app --host 127.0.0.1 --port 18080
```

Health:

```text
{"ok":true,"chunks":13}
```

Example supported query:

```text
Question: How do I secure my pod?
fallback: false
confidence: 0.5
source: docs/platform-kb/aks/pod-security.md
answer excerpt: Run the container as non-root and set allowPrivilegeEscalation: false in the pod or container securityContext.
```

Required query coverage:

```text
How do I secure my pod?
  fallback: false
  source: docs/platform-kb/aks/pod-security.md

How do I bring my own domain?
  fallback: false
  source: docs/platform-kb/aks/custom-domains.md

How do I set up a pod disruption budget?
  fallback: false
  source: docs/platform-kb/aks/pod-disruption-budgets.md

What Kubernetes resources are available on the shared AKS platform?
  fallback: false
  source: docs/platform-kb/aks/shared-aks-resources.md
```

Fallback query:

```text
Question: How do I repair a PostgreSQL vacuum freeze issue?
fallback: true
answer: Sorry, we couldn't help solve your problem. Please raise a ticket here.
```

Simulated stale-doc PR:

```text
mode: simulated
branch: mil-128/kagent-kb-update-1778670658
pr_url: https://github.com/davidmarkgardiner/kagent-public/pull/simulated-mil-128
changed_file: docs/platform-kb/aks/pod-security.md
```

The simulation artifact is committed at `docs/poc-evidence/simulated-stale-doc-pr.json`.

## Kubernetes Deploy

Commands:

```bash
cd agents/kagent-knowledge-ui
docker build -t ghcr.io/davidmarkgardiner/kagent-knowledge-ui:mil-128 .
kind load docker-image ghcr.io/davidmarkgardiner/kagent-knowledge-ui:mil-128 --name homelab
kubectl apply -k k8s
kubectl -n kagent-knowledge-ui rollout status deployment/kagent-knowledge-ui --timeout=120s
```

Output:

```text
namespace/kagent-knowledge-ui created
serviceaccount/kagent-knowledge-ui created
service/kagent-knowledge-ui created
deployment.apps/kagent-knowledge-ui created
agent.kagent.dev/kagent-knowledge-ui created
deployment "kagent-knowledge-ui" successfully rolled out
```

Deployed resources:

```text
NAME                                       READY   STATUS    RESTARTS   AGE
pod/kagent-knowledge-ui-678955765f-xb5zc   1/1     Running   0          12s

NAME                          TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
service/kagent-knowledge-ui   ClusterIP   10.109.61.179   <none>        80/TCP    12s
```
