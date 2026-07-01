# Team Message: Hybrid Azure SRE Agent + kagent

I think the right recommendation is a hybrid model rather than choosing one platform for everything.

Azure SRE Agent looks like the better fit for tier 1 production AKS applications and selected tier 2 services where we need a reliable, always-on managed SRE capability, especially for P1/P2 paths that already need ServiceNow tracking and formal incident ownership.

kagent should remain our default platform for dev, test, staging, platform automation, security/compliance workflows, GitLab/Azure DevOps integration, and cases where paying for a managed SRE agent would be overkill. It gives us more control, lower marginal cost, and fits the AKS + Argo + LGTM + GitLab/Azure DevOps stack we already use.

I would also position this as an interchangeable skills and handoff model, not two separate stacks. There is no reason our current Argo workflows could not trigger Azure SRE Agent as another downstream action when a kagent workflow has reached the point where a ServiceNow incident or formal production escalation is needed.

The useful loop would be: kagent triages first, attempts safe remediation or produces the recommendation, escalates through ServiceNow where required, and then Azure SRE Agent or a human SRE can help take the issue forward. The outcome should then feed back into the shared knowledge base, runbooks, or agent skills so kagent can fix the same or similar issue automatically on the next run.

For app teams, Azure SRE Agent can still be an option if they want a managed agent and are prepared to own the billing and configuration. Otherwise, the platform default should be kagent and the bring-your-own-agent pattern.

So the split would be:

- Critical production / P1-P2 / ServiceNow-led incident paths: Azure SRE Agent where justified.
- Dev, non-prod, platform workflows, lower-tier services, custom automation, and GitOps-based remediation: kagent.
- App-team managed use cases: optional Azure SRE Agent if the app team funds and owns it; otherwise kagent.
- Shared skills / knowledge base / runbook learning: common across both paths wherever practical.

This feels like the most robust direction. We can use the managed Microsoft capability where it genuinely reduces risk, while keeping our own kagent platform as the core agentic harness for the broader estate.
