# Hybrid Azure SRE Agent + kagent Recommendation

## Recommendation

Use a hybrid model.

Azure SRE Agent and the in-house kagent platform solve overlapping problems, but they are strongest in different places. The most robust position is to use Azure SRE Agent selectively for the highest-risk production support paths, while keeping kagent as the default platform for development, non-production, platform automation, and lower-cost agentic workflows.

This avoids turning Azure SRE Agent into a blanket platform dependency while still using it where the managed-service reliability and support model are worth paying for.

## Where Azure SRE Agent Fits Best

Use Azure SRE Agent for:

- Tier 1 production AKS applications.
- Critical tier 2 production applications where incident response speed matters more than agent cost.
- P1/P2 alert paths that already create or escalate through ServiceNow.
- App teams that want a managed SRE assistant and are prepared to own the Azure SRE Agent billing and configuration.
- Scenarios where Azure-native integration, managed reliability, audit posture, and always-on availability matter more than platform flexibility.

The cleanest operating model is:

```text
Critical production AKS alert
  -> Azure SRE Agent triage
  -> ServiceNow incident / update
  -> human or approved remediation path
```

This should be reserved for workloads where the cost and managed-service dependency are justified.

## Where kagent Fits Best

Use the kagent platform for:

- Development clusters.
- Test, staging, and lower-tier production workflows where Azure SRE Agent is overkill.
- Platform engineering use cases beyond incident triage.
- GitLab and Azure DevOps centric workflows.
- Argo Workflow based remediation and approval flows.
- LGTM / Grafana driven observability workflows.
- Security hardening, policy checks, advisory compliance, namespace onboarding, AKS platform automation, and custom app-team agents.
- Bring-your-own-agent patterns where the platform team provides the harness, guardrails, workflow patterns, and routing.

The default operating model is:

```text
Grafana / Alertmanager / platform event
  -> Kafka / Vector / Argo Events where applicable
  -> Argo Workflow
  -> kagent triage or specialist agent
  -> GitLab / Azure DevOps evidence and change path
  -> Teams / ServiceNow only when needed
```

kagent remains the better fit where we need control, portability, lower marginal cost, and integration with the tools we actually use.

## Why Hybrid Is Stronger Than Either Option Alone

Hybrid gives us:

- Faster delivery because we can use Azure SRE Agent where it is already strong.
- Better control because kagent remains our own platform layer.
- Better cost discipline because not every dev/test/internal workflow needs an always-on managed SRE agent.
- Better fit for our estate because we are AKS-focused and do not use GitHub at work.
- Better integration with our delivery model because code and operational evidence live in Azure DevOps and GitLab.
- A cleaner product story for app teams: use the platform default unless they explicitly need and fund the managed SRE path.

## Interchangeable Skills And Handoff

The hybrid model should not be treated as two isolated agent stacks. The stronger pattern is to make skills, runbooks, knowledge articles, and routing decisions reusable across both kagent and Azure SRE Agent wherever the interfaces allow it.

There is no obvious reason our existing Argo Workflows could not trigger Azure SRE Agent as another downstream action, in the same way they can trigger a kagent triage agent, specialist agent, GitLab update, Azure DevOps change, or ServiceNow escalation.

A useful escalation loop would be:

```text
Grafana / Alertmanager event
  -> Kafka / Vector / Argo Events where applicable
  -> Argo Workflow
  -> kagent triage / specialist agent
  -> safe remediation attempted or recommendation produced
  -> ServiceNow incident if human ownership is required
  -> Azure SRE Agent engaged for critical production follow-up where justified
  -> lessons learned captured back into shared knowledge / skills
  -> kagent can resolve the same or similar issue on the next run
```

This keeps kagent as the orchestration harness while allowing Azure SRE Agent to participate in the parts of the incident lifecycle where a managed SRE capability adds value.

The important design point is the feedback loop. If Azure SRE Agent, a human SRE, or an app team resolves a production issue that kagent could not fix, the outcome should update the shared knowledge base, runbook, policy, or agent skill. That converts an escalation into future automation rather than leaving the same issue to become another manual incident later.

## Suggested Routing Policy

| Workload / scenario | Recommended path | Reason |
|---|---|---|
| Tier 1 production AKS app | Azure SRE Agent | Highest reliability expectation, strongest case for managed support and ServiceNow integration |
| P1/P2 production incident | Azure SRE Agent first where justified, with kagent / Argo preserving platform context | Keep the managed incident path reliable while preserving internal evidence/remediation flows |
| Tier 2 critical production app | Case-by-case | Use Azure SRE Agent if the app team accepts cost and ownership |
| Tier 3 production / internal app | kagent | Managed SRE agent likely overkill |
| Dev / test / staging | kagent | Lower cost, more control, better for experimentation |
| Platform automation | kagent | Argo, GitLab/Azure DevOps, AKS-MCP, agentgateway, and LGTM are already our platform primitives |
| Security / compliance / hardening | kagent | More custom workflow control and easier integration with GitOps review |
| App-team bring-your-own-agent | kagent by default; Azure SRE Agent optional if app team funds it | Platform can provide guardrails without absorbing every team's agent cost |
| kagent cannot safely remediate a critical issue | Escalate through ServiceNow and optionally invoke Azure SRE Agent | Preserve formal ownership while feeding the resolution back into shared knowledge and skills |

## ServiceNow Position

ServiceNow should be treated as an escalation and accountability system, not the first proof that automation is working.

For kagent-led flows, the preferred pattern is:

```text
Detect -> triage -> attempt safe remediation or produce recommendation
```

Only create or update a ServiceNow incident when:

- the issue cannot be remediated automatically;
- human ownership is required;
- the incident is P1/P2 or policy requires formal tracking;
- the workflow needs an auditable hand-off to an app or service owner.

For Azure SRE Agent flows, ServiceNow is a better fit because the target workloads are the ones where formal incident management is expected anyway.

## Environment Constraints

Important assumptions for our environment:

- We are AKS-focused.
- We do not use GitHub at work.
- Source and delivery workflows are Azure DevOps and GitLab.
- Observability is Grafana / LGTM-oriented.
- Argo Workflows and Argo Events are already central to the kagent platform design.
- We want GitOps review for durable platform changes rather than opaque agent-side mutation.

These constraints make a pure Azure SRE Agent strategy less attractive, even if it is useful for a narrow production tier.

## Proposed Decision

Adopt this as the working policy:

> Azure SRE Agent is the premium managed path for critical production AKS incidents. kagent is the default agentic platform for development, platform engineering, custom workflows, GitLab/Azure DevOps integration, and lower-tier or non-production automation.

The two should share knowledge and skills where practical. kagent and Argo remain the orchestration layer, and Azure SRE Agent can be invoked as a managed SRE handoff path when an incident needs that level of production support.

This lets us move faster without giving up control of the broader platform.
