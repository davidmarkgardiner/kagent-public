# Help Request: Problem Statement and Investigation Template

## Teams Message

Hi team,

To help us understand the issue properly and give useful input, could you please capture this in a GitLab issue before our next discussion?

We have had a few conversations, but it is still difficult to separate the core problem from the surrounding context. A written issue with the background, problem statement, diagrams, evidence, and open questions will put us in the best position to identify any gaps, challenge assumptions, and suggest practical options.

Please include as much of the following as possible:

- Background and business or technical context
- Clear problem statement
- Current architecture, process flow, or sequence diagram
- Expected behavior vs actual behavior
- Relevant errors, logs, screenshots, alerts, traces, or pipeline output
- Steps to reproduce, if applicable
- What has already been tried or ruled out
- Specific questions or gaps you want help with
- Links to related repos, docs, dashboards, pipelines, or existing tickets

Once the GitLab issue is created, please share the link here. We can review it asynchronously first and then decide whether another meeting is needed.

---

## GitLab Issue Template

```markdown
# Help Request: [Short title of the issue]

## Summary

Briefly describe the issue in 2-4 sentences.

Example:
We are trying to achieve [desired outcome], but [actual behavior] is happening instead. This is affecting [users/services/process] because [impact].

## Background

Describe the system, process, or workflow involved.

Please include:

- What the component, service, or process does
- Who uses it
- Why it matters
- Any relevant recent changes
- Any important constraints or dependencies

## Problem Statement

Clearly describe the core problem.

Try to make this specific and testable:

- What is failing?
- Where is it failing?
- When does it happen?
- Is it consistent or intermittent?
- What is the impact?

## Current Architecture / Process Flow

Add a diagram, sequence diagram, screenshot, or link to a diagram.

If a diagram is not available yet, describe the flow in steps:

1. [Actor/system] does [action].
2. [Service/component] sends [request/event/data].
3. [Service/component] processes [request/event/data].
4. The issue occurs when [specific point in the flow].

## Expected Behavior

Describe what should happen.

Example:
When [trigger/event] happens, the system should [expected result].

## Actual Behavior

Describe what is happening instead.

Example:
When [trigger/event] happens, the system currently [actual result].

## Errors, Logs, and Evidence

Paste relevant errors, logs, screenshots, traces, alerts, pipeline output, or dashboard links.

```text
Paste error output here
```

Please include timestamps, environment names, correlation IDs, request IDs, pipeline IDs, or trace IDs if available.

## Steps to Reproduce

If applicable, list the steps needed to reproduce the issue.

1. Go to [system/page/service].
2. Run [command/action].
3. Submit [request/input].
4. Observe [result/error].

If the issue cannot be reproduced consistently, describe when it has been observed.

## Environment

Please include any relevant environment details:

- Environment: [dev/test/staging/prod]
- Application/service:
- Version/build/commit:
- Region/cluster/namespace:
- Browser/client/tool version, if relevant:
- Related configuration:

## Impact

Describe the impact.

- Is production affected?
- Is this blocking a release, migration, or operational process?
- How many users, teams, services, or workflows are affected?
- Is there a workaround?
- What is the priority or urgency?

## What Has Already Been Tried

List investigations, attempted fixes, theories, and anything already ruled out.

- Tried:
- Checked:
- Ruled out:
- Current theory:

## Help Needed

Be specific about what you want help with.

Examples:

- Validate whether the proposed architecture or flow is logically correct
- Identify missing dependencies, edge cases, or assumptions
- Review error logs and suggest likely causes
- Suggest alternative implementation options
- Confirm whether this is a platform, networking, security, application, or data issue
- Help define the next debugging steps

## Open Questions

List any unresolved questions.

- Question 1:
- Question 2:
- Question 3:

## Links and References

Add any relevant links.

- Repository:
- Merge request:
- Pipeline/job:
- Dashboard:
- Logs/traces:
- Documentation:
- Related tickets:
- Diagram:
```
