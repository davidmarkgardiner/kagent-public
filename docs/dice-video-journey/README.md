# DICE video journey

Status: story scaffold for review

Prepared: 8 October 2026

## Audience promise

Show how DICE grew from individual agent experiments into a reusable engineering platform: useful agents, approved tools, controlled model access, isolated execution and evidence-backed workflows that leave important decisions with people.

The series is aimed at a mixed internal engineering audience. Each module must make sense by itself and link naturally into the complete journey.

## Production contract

- One 1–2 minute MP4 per module, plus one combined journey video.
- David's approved voice provides narration.
- No talking head, avatar or static presenter image in this edition.
- Use diagrams, readable evidence cards and short demonstrations.
- Palette: red `#C8102E`, charcoal `#161616`, grey `#E5E7EB` and white `#FFFFFF`.
- Use DICE and generic platform language in audience-facing copy. Named components such as agentgateway, KMCP, Grafana, GitLab, PostgreSQL, Entra and Agent Substrate are allowed where they explain the implementation.
- Label evidence as `Recorded demonstration`, `Implementation prepared` or `Integration to verify`.
- Never present a lab fixture, schema check or design package as a live workplace result.

## Complete journey

| # | Module | Target | Viewer takeaway |
|---|---|---:|---|
| 01 | Why DICE exists | 1:30 | The recurring engineering problems the platform addresses. |
| 02 | Bring your own agent | 1:30 | A repeatable onboarding contract for team-owned agents. |
| 03 | Skills and tools | 1:30 | How reusable instructions choose bounded capabilities. |
| 04 | KMCP and tool connections | 1:30 | How tools are discovered, described and connected. |
| 05 | Model profiles and Model Garden | 1:30 | How approved model access is separated from each agent. |
| 06 | One front door with agentgateway | 1:30 | How model and tool requests pass through shared controls. |
| 07 | Identity with Entra | 1:30 | How caller identity and backend workload identity remain distinct. |
| 08 | Agent isolation | 1:30 | How teams receive only the routes and tools assigned to them. |
| 09 | Grafana MCP | 1:30 | How operational questions become telemetry-backed answers. |
| 10 | Evidence-first triage | 2:00 | How related signals become one useful investigation. |
| 11 | PostgreSQL without bulk context | 1:30 | How the tool bounds rows and bytes before data reaches the model. |
| 12 | GitLab MCP | 1:30 | How proposed work becomes an inspectable branch and draft merge request. |
| 13 | Software delivery loop | 2:00 | How planning, build, test, repair and review connect. |
| 14 | Agent Substrate | 1:30 | How a logical session can survive suspension and return. |
| 15 | Milestones and next steps | 1:00 | What has been demonstrated and what still needs integration evidence. |

Provisional combined length: approximately 23 minutes. Final chapter markers must come from the approved narration and rendered edits.

## Shared story pattern

Each module follows the same viewer experience:

1. State a concrete engineering problem.
2. Explain one simple mental model.
3. Show one complete demonstration.
4. Display the result and its evidence status.
5. Link the lesson to the next module.

The combined cut uses short chapter transitions. Standalone cuts add a brief opening title and a closing link back to the DICE journey.

## Navigation

Publish the material in two forms:

- a chapter library with one card per standalone MP4, a transcript and previous/next links;
- a combined journey video with chapter markers and timecode links.

Suggested paths through the library:

- Overview: 01 → 10 → 11 → 13 → 15.
- Platform foundations: 02 → 03 → 04 → 05 → 06 → 07 → 08 → 14.
- Operations and delivery: 09 → 10 → 11 → 12 → 13.

The first worked example is [Evidence-first triage](01-triage-storyboard.md).

## Review sequence

1. Review this journey and the triage example.
2. Create a plain wireframe preview of the triage chapter.
3. Approve a short narration audition in David's voice.
4. Produce and review the complete triage pilot.
5. Apply the accepted format to the remaining chapters.

This scaffold does not authorise voice generation, paid media, rendering or publication.
