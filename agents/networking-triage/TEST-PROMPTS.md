# Test Prompts

Curated prompts to validate the agent works and to get a feel for its
capabilities. Copy-paste into the chat UI.

**Rule of thumb:** start new conversations for unrelated issues. The chat
context window is ~15 exchanges, so long conversations about one problem
beats one long conversation about many problems.

## Smoke tests (run these first, any cluster)

| # | Prompt | What it proves |
|---|---|---|
| 1 | *"How many pods are running in `kube-system`?"* | Kubernetes API access works |
| 2 | *"Check CoreDNS health in this cluster."* | DNS diagnostic workflow runs |
| 3 | *"Is there any unusual packet loss on the nodes?"* | Packet drop DaemonSet deploys + cleans up |
| 4 | *"Show me the current network policies in the default namespace."* | Network policy reading works |

Expect each to return a structured report (evidence table + summary). Report
to the team if any fail — that's likely a platform config issue, not a usage
problem.

## DNS troubleshooting

| Situation | Prompt |
|---|---|
| DNS completely broken | *"All DNS is broken in the cluster"* |
| Pod can't resolve names | *"A pod in namespace `my-app` cannot resolve any DNS names"* |
| Specific name not resolving | *"DNS resolution for `backend.default.svc.cluster.local` is failing"* |
| Intermittent DNS failures | *"Pods in `production` have intermittent DNS failures"* |
| External DNS blocked | *"External DNS fails for pods in `my-namespace`"* |
| NodeLocal DNS issues | *"Can you check if NodeLocal DNS is working?"* |

## Packet drop / RX analysis

| Situation | Prompt |
|---|---|
| Drops on a specific node | *"I see packet drops on node `aks-nodepool1-12345678-vmss000000`"* |
| Latency spikes | *"My application is experiencing intermittent latency spikes"* |
| Cluster-wide performance | *"Network performance is degraded cluster-wide"* |
| After `iperf` test shows loss | *"I'm seeing packet drops and high latency. The iperf tests show significant packet loss."* |
| Proactive health check | *"Check network health on node `my-node`"* |

First packet-drop query takes 30–60s extra while the `rx-troubleshooting-debug`
DaemonSet schedules. Subsequent queries reuse the DaemonSet.

## Kubernetes networking / connectivity

| Situation | Prompt |
|---|---|
| Service unreachable | *"My client pod cannot connect to the `backend-service` in `production`. The connection times out."* |
| Traffic blocked | *"My client pod can't reach the `backend-service` anymore. It was working before."* |
| No endpoints | *"Service has no endpoints in namespace `my-app`"* |
| Pod stuck Pending | *"I deployed my app but the service has no endpoints and the pod doesn't have an IP"* |
| Pods not ready | *"Pods are not ready in namespace `staging`"* |
| Proactive check | *"Everything looks fine in namespace `production` — can you verify?"* |

## Useful patterns for production

### Pre-change validation

> *"I'm about to apply a NetworkPolicy that restricts egress from `api-services` namespace. Can you review what traffic is currently flowing out of that namespace via Hubble?"*

(Requires ACNS enabled for Hubble flow observation.)

### Post-incident evidence gathering

> *"We had a DNS incident in `production` around 14:00 UTC. Check the CoreDNS pod logs, recent config changes, and network policies that might have contributed."*

Copy the evidence table from the response into your incident ticket.

### On-call triage when "something feels off"

> *"Our latency dashboards show elevated p99 across services in the `platform` namespace for the last 20 minutes. Check pod health, network policies, and node-level packet drops."*

## Prompts that WON'T work

The agent is scoped to AKS networking. It will politely decline or give poor
answers for:

- Application code bugs / stack traces
- Storage / PVC / disk issues
- RBAC or secret management (except network-policy-related RBAC)
- Workload scheduling optimization
- Cost analysis
- Making changes (it only recommends; you apply)
- AWS / GCP / on-prem clusters

For those, use your other agents or tools.

## Calibration — is the agent confident?

The agent reports its confidence via structured output. Look for:

- **"All checks passing"** — high confidence nothing is wrong
- **"Evidence contradicts X"** — clear signal
- **"Insufficient data to confirm"** — can't decide, escalate to a human
- **"Multiple plausible root causes"** — ambiguous; agent lists them ranked

Treat "insufficient data" and "multiple plausible" as signals to dig deeper
manually — don't auto-remediate on ambiguous findings.

## Feedback

After each response, use the thumbs-up / thumbs-down in the UI. This trains
Microsoft's model and affects future diagnostic accuracy for everyone on the
preview.
