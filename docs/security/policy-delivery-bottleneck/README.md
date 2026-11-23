# Unblocking AKS delivery: why the policy decision process deserves priority

When Azure Policy exceptions repeatedly delay pods, applications and runtimes, the exception process can become a shared delivery constraint. Improving that constraint can unlock work across several teams at once.

This README explains the reasoning to managers and engineers, with a simple explanation first and the mathematics below. All numbers are illustrative. No workplace measurements or claims of measured savings are presented here.

## Compare the engineering cluster with a Linux server

Engineering teams deploy applications onto Linux servers as part of normal delivery. An engineering Kubernetes cluster also runs applications on Linux nodes, with an orchestration layer managing workloads. If equivalent deployments on servers are permitted while the cluster is routinely blocked, ask what additional risk each Kubernetes restriction addresses and whether the control is proportionate to this environment. This is an analogy, not an assertion that servers and clusters have identical risks or controls.

Shared clusters and environments with customer data need controls appropriate to those workloads. For an isolated engineering cluster without customer workloads or data, assess the actual network paths, outbound access, identities and permissions, and assume cluster access may lead to node access. Verify the boundaries before describing external impact as limited: network isolation alone does not prevent misuse of an authorised identity or an allowed external connection. Review blocking policies individually and agree exceptions or an engineering baseline with appropriate alternative controls, owners and review.

The [Teams draft](../engineering-policy-blocker-teams-message.md) puts this comparison to policy owners and asks for a decision.

## Explain it like I'm five

Imagine we build toy cars and send them through a safety gate before children can play with them.

We can build **20 cars a day**, but the gate can check only **4 cars a day**. So children get, at most, four checked cars each day.

If we build even faster, the children still get four. We just make a bigger pile of cars waiting at the gate.

We should help the gate work better: make the checking instructions clearer, give it the information it needs, and add another trained checker if needed. We can also build cars using a design that already has an agreed safety check.

**Helping the slowest part helps the whole line. Making the fast parts faster mostly makes the pile bigger.**

At work, the toy cars are applications. The safety gate is the policy decision process. Our goal is to get safe applications through that gate predictably.

## What this means for management

The organisation benefits from usable changes reaching their intended environment. Starting more work has limited value when a shared gate prevents that work from being used.

This is the central idea of the [Theory of Constraints](https://www.tocinstitute.org/five-focusing-steps.html): find the limiting step, improve its operation, align other work around it, increase its capacity where needed, and reassess when the constraint moves.

It supports a focused improvement effort. It does not imply that every employee must stop every other task. Keep essential operations running and continue independent work that delivers value. Protect time from the people who can resolve the constraint, and reduce starts that merely add to the blocked queue.

Treat policy decision flow as a candidate constraint to verify. A long wait alone does not prove it is the largest limit on overall delivery.

## The mathematics

### 1. The slowest required stage limits throughput

Consider a simplified flow in which every change needs one policy approval and all approved changes can proceed:

| Stage | Capacity |
|---|---:|
| Build and test | 20 changes/week |
| Policy approval | 4 changes/week |
| Deploy | 15 changes/week |

```text
Maximum sustainable delivery <= min(20, 4, 15) = 4 changes/week
```

Making engineering 50% faster gives:

```text
Maximum sustainable delivery <= min(30, 4, 15) = 4 changes/week
```

Increasing policy capacity from four to eight could instead raise delivery to eight changes a week, if demand and the remaining stages support it. That is a potential 100% improvement in delivery capacity.

Measure comparable units. If only some deployments need exceptions, analyse that flow separately. Where one approval covers many deployments, measure that relationship rather than assuming one request equals one deployment. Rework, dependencies and rejected requests also affect the result.

### 2. A capacity deficit creates an accumulating backlog

```text
Backlog at end = backlog at start + new requests - resolved requests
```

If eight requests arrive and four are resolved each week, the backlog grows by four a week: approximately 40 additional requests after ten weeks, assuming no other exits.

Starting more upstream work can increase that gap. Moving one request to the front changes priority; it does not increase total decision capacity.

There are three direct improvements: reduce unnecessary exception requests, reduce the effort needed to resolve each request, or increase effective decision capacity.

Track decision outcomes separately. A justified rejection resolves a request but may leave the deployment blocked; approval alone also does not prove successful deployment.

### 3. A nearly saturated approval process can have very long waits

For a basic M/M/1 queue:

```text
rho = arrival rate / service capacity
W = s / (1 - rho)
```

Here, `s` is average service time and `W` includes waiting and service.

| Utilisation | Average total time |
|---|---:|
| 50% | 2 x service time |
| 80% | 5 x service time |
| 90% | 10 x service time |
| 95% | 20 x service time |

The model assumes one server, Poisson arrivals, exponential service times, an unlimited queue and stable load below capacity. It illustrates sensitivity to utilisation; it does not predict this organisation's turnaround. See [MIT's queueing notes](https://ocw.mit.edu/courses/2-854-introduction-to-manufacturing-systems-fall-2016/927056a1af54772a587fd84ad4951e71_MIT2_854F16_Mm1Queue.pdf).

The practical implication is to protect enough decision capacity to absorb variation, urgent work and absences.

## A practical two-week improvement experiment

Appoint one accountable owner for the improvement, with protected participation from platform engineering and policy decision makers. The owner needs access to the people authorised to make the relevant decisions.

| Period | Action | Output |
|---|---|---|
| Days 1-2 | Inspect recent blocked changes and current open requests. Identify the actual denying control and waiting stages. | Baseline and ranked causes of delay. |
| Days 3-5 | Standardise request evidence, name decision owners and backups, and agree how common cases are handled. | A clear route from request to decision. |
| Days 6-9 | Trial the agreed process on representative requests; verify permitted deployments through the normal delivery route. | Decision records and deployment outcomes. |
| Day 10 | Compare results with the baseline and check open-request ages. | Decision to retain, adjust or extend the improvement. |

Confirm whether each denial comes from Azure Policy, Gatekeeper, Kyverno or another admission control before choosing a technical remedy.

Useful changes include approved deployment patterns, policy checks before implementation, a complete evidence template, protected review slots, and delegated decisions within an agreed scope. Repeated requests for the same legitimate pattern should trigger review of the standard pattern or policy configuration.

For exceptional cases, agree scope, rationale, compensating controls, approval, expiry and review. Azure Policy supports exemption metadata and expiry; the correct scope and mechanism depend on the actual assignment and enforcement path. See [Microsoft's exemption documentation](https://learn.microsoft.com/en-us/azure/governance/policy/concepts/exemption-structure).

## How to measure success

| Measure | What it tells us |
|---|---|
| Requests arriving versus resolved each week | Whether the decision process keeps pace with demand. |
| Open backlog and oldest unresolved request | Whether old work is being cleared or hidden by recent completions. |
| Median and 90th-percentile decision time | Typical turnaround and the long waits teams experience. |
| Waiting time versus active review time | Whether delay comes from queueing, handoffs or difficult analysis. |
| Successful deployments previously blocked by policy | Whether faster decisions produce usable delivery. |
| Repeat request causes | Where standard patterns can remove recurring work. |

Include still-open requests in the review; measuring only completed requests can hide the worst delays. A small two-week sample provides directional evidence, not a guaranteed sustained improvement.

For an economic case, estimate the business value delayed and the effort needed to improve the process. Compare the expected value unlocked with the opportunity cost of diverted work. Avoid counting every waiting engineer's full salary as a loss when they can do other useful work, or double-counting business delay and staff costs.

Rebalance effort when turnaround meets the agreed target, the process can keep pace with demand, old requests are clearing, and previously blocked changes can deploy. Then identify the next limiting step.

## A message to the boss

> We appear to have a shared delivery constraint in the policy exception process. Several teams can build changes faster than those changes can obtain deployment decisions. Increasing development activity therefore risks increasing unfinished work without increasing delivered value.
>
> I propose a two-week priority involving platform engineering and the policy owners, with a named accountable owner and protected decision-making time. We will measure request arrivals, resolution rate, waiting time and successful deployments, then address the biggest repeat causes.
>
> The objective is a predictable, controlled route to deployment. Once the process keeps pace with demand and the backlog is falling, we can rebalance effort toward the next constraint.

**The decision is about improving delivery across the system. The strongest evidence will be fewer blocked changes and more usable outcomes.**
