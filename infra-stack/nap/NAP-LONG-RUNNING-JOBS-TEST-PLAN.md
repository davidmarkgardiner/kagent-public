# Test Plan: Verify NAP Does Not Evict Running Long-Running Jobs

Audience: work platform team validating AKS Node Auto-Provisioning behavior for batch workloads.

Last updated: 2026-05-13

## Safety Gate

Do not run this test on a production cluster first.

Running workload tests on a NAP-enabled AKS cluster can cause NAP to create or remove Azure VM capacity. Get explicit work approval for:

- Cluster name and subscription.
- Resource group.
- Test window.
- Maximum expected nodes or vCPU quota.
- Cleanup owner.
- Rollback contact.

This plan does not require creating AKS clusters, resource groups, VNets, managed identities, or other Azure resources manually. It assumes an existing NAP-enabled AKS test cluster.

## Success Criteria

The test is successful when:

- Long-running Job pods have `karpenter.sh/do-not-disrupt: "true"` on the pod.
- The batch `NodePool` uses `consolidationPolicy: WhenEmpty`.
- The batch `NodePool` does not use routine expiration for run-to-completion
  jobs, or the team has explicitly accepted the `terminationGracePeriod`
  behavior.
- NAP does not voluntarily evict the running Job pod.
- After the Job completes, empty nodes become eligible for normal cleanup.
- Events and Karpenter logs support the observed behavior.

## Phase 0: Confirm Context

Run:

```bash
kubectl config current-context
kubectl cluster-info
kubectl auth can-i get nodepools
kubectl auth can-i get nodes
kubectl auth can-i get pods --all-namespaces
```

Expected:

- The context is the approved test cluster.
- The operator can inspect `NodePool`, node, pod, event, and Karpenter log state.

Stop if the context is production or not explicitly approved.

## Phase 1: Baseline Current NAP Policy

Run:

```bash
kubectl get nodepools -o wide
kubectl get nodepool default -o yaml
kubectl get nodes -L karpenter.sh/nodepool,workload-type,kubernetes.io/os
```

Record:

- Which `NodePool` currently runs batch jobs.
- Whether any pool uses `WhenEmptyOrUnderutilized`.
- Whether `expireAfter` or `terminationGracePeriod` is configured.
- Whether Spot capacity is used.

If `terminationGracePeriod` is configured, record it as a potential hard
deadline: upstream Karpenter documents that it can bypass PDBs and
`karpenter.sh/do-not-disrupt` after a node has started draining.

## Phase 2: Check Existing Job Protection

Run:

```bash
kubectl get pods --all-namespaces \
  -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.nodeName,PHASE:.status.phase,DO_NOT_DISRUPT:.metadata.annotations.karpenter\.sh/do-not-disrupt' \
  | grep -v '<none>' || true
```

For any affected Job:

```bash
kubectl get job -n <namespace> <job-name> -o yaml
```

Expected:

- The annotation is present under `spec.template.metadata.annotations`.
- If it is only on `metadata.annotations` for the Job object, it is in the wrong place.

## Phase 3: Validate Proposed Manifests Without Applying

Create or review:

- `batch-nodepool.yaml`
- `long-running-job.yaml`

Run:

```bash
kubectl apply --dry-run=server -f batch-nodepool.yaml
kubectl apply --dry-run=server -f long-running-job.yaml
```

Expected:

- Both dry-runs pass.
- No live workload or node capacity is created by this phase.

## Phase 4: Apply Controlled Test Workload

Only run this phase after the safety gate is approved.

Run:

```bash
kubectl create namespace nap-disruption-test
kubectl apply -n nap-disruption-test -f long-running-job.yaml
kubectl get pods -n nap-disruption-test -w
```

Verify the annotation landed on the pod:

```bash
POD="$(kubectl get pod -n nap-disruption-test -l job-name=long-running-task -o jsonpath='{.items[0].metadata.name}')"
kubectl get pod -n nap-disruption-test "$POD" -o jsonpath='{.metadata.annotations.karpenter\.sh/do-not-disrupt}{"\n"}'
```

Expected:

- Output is `true`.
- The pod remains running until the test command completes.

## Phase 5: Observe NAP During the Test

Run:

```bash
kubectl get events --all-namespaces --sort-by='.lastTimestamp' \
  | grep -Ei 'karpenter|disrupt|consolidat|drift|nodeclaim' \
  | tail -50
```

Run:

```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter -c controller --tail=200
```

Expected:

- No voluntary eviction of the protected test pod.
- If consolidation is skipped, the logs or events should be consistent with the
  protected pod or `WhenEmpty` policy.
- If eviction still occurs, classify the reason before calling it a NAP
  consolidation issue. Check for expiration, node repair, Spot interruption,
  manual deletion, or NodePool deletion.

## Phase 6: Completion and Cleanup

Run:

```bash
kubectl wait -n nap-disruption-test --for=condition=complete job/long-running-task --timeout=70m
kubectl delete namespace nap-disruption-test
kubectl get nodes -L karpenter.sh/nodepool,workload-type
```

Expected:

- The Job reaches `Complete`.
- Test namespace is deleted.
- Empty nodes are eligible for cleanup after the pool's `consolidateAfter` duration.

## Phase 7: Evidence to Capture

Capture:

- `kubectl get nodepools -o yaml`
- The final Job YAML.
- Pod YAML showing the annotation.
- Relevant Karpenter events.
- Relevant Karpenter controller logs.
- Node list before and after cleanup.

## Rollback

Remove the test workload:

```bash
kubectl delete namespace nap-disruption-test --ignore-not-found
```

If a test-only batch NodePool was applied and is no longer needed:

```bash
kubectl delete nodepool batch-jobs
```

Deleting a `NodePool` can disrupt nodes owned by that pool. Confirm no important workloads are still using it before deletion.

## Final Recommendation

For work clusters, treat long-running batch as a separate scheduling class:

- Dedicated `NodePool`.
- `consolidationPolicy: WhenEmpty`.
- `karpenter.sh/do-not-disrupt: "true"` on the Job pod template.
- On-demand capacity unless the workload is explicitly checkpointed and retry-safe.
- No routine `expireAfter` for run-to-completion pools unless the team has also
  accepted the corresponding `terminationGracePeriod` tradeoff.
- Evidence captured before and after rollout.
