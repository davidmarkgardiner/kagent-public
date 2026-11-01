# Viva Engage: technical video posting guide and draft posts

Prepared: 8 October 2026. These are suggested posts, not a record of publication to Viva Engage.

## Recommended approach

Post the videos separately as short technical learning demonstrations, not product announcements. Lead with a recognisable problem, attach the MP4 and finish with one specific question.

Start with **kagent + agentgateway**, because the governance problem is immediately relatable. Share **Agent Substrate** a few days later and link back to the first Engage conversation. Use Option A for each video as the default.

## Posting checklist

- Choose the most relevant engineering, AI or platform community rather than the company-wide feed initially. Follow local community rules.
- Upload the MP4 directly so viewers do not need YouTube. Engage supports attachments from a computer or SharePoint, subject to organisational settings. If direct upload is unavailable, use an approved internal video location and check viewer permissions.
- Check playback from the work environment after posting. Do not assume successful upload proves colleagues can play it.
- State the approximate five-minute runtime and include a short written summary for people watching without sound. Include captions where the approved video platform supports them.
- Use three or four relevant hashtags. Search Engage first and reuse established internal spellings; these suggestions are not verified internal tags.
- Add existing topics separately where available: conversation menu → **Edit topics**. Topics categorise the conversation; hashtags make messages easier to find. Avoid creating near-duplicate topics.
- Mention only genuine contributors or people whose specific feedback you want. Avoid mass tagging and broad notifications.
- Describe the videos as personal lab demonstrations using synthetic data, not company deployments or endorsed architecture.
- Follow internal sharing and AI-media disclosure requirements. Where applicable, add: “Produced with AI-assisted narration/presentation; technical claims are scoped to the demonstrated lab evidence.”
- Review the video itself as well as the post for confidential information. Do not attach private receipts, logs, credentials or internal architecture.

## Video 1: kagent + agentgateway

**Title:** One Front Door, No Side Doors | kagent + agentgateway on Kubernetes

**Runtime:** 5:20

**MP4:** `kagent-agentgateway-tenant-isolation-final-v2.mp4`

**Public reference:** https://www.youtube.com/watch?v=eAJpU-oWUdg

Suggested existing topics to look for: AI agents, Platform engineering, Kubernetes, AI security. Use the internal MP4 for the post; the public reference is optional and may be blocked at work.

### Option A: platform governance angle — recommended

**How do we enable team-owned AI agents without creating security side doors?**

I've put together a five-minute lab demonstration exploring a simple platform pattern: **one front door, separate controlled lanes, no direct shortcuts**.

Using kagent and agentgateway on Kubernetes, it shows two team-owned agents reaching their own MCP tools, followed by tests of unauthorised credentials and a direct-access attempt.

The useful distinction: teams own agent behaviour; the platform owns identity, routing and network boundaries.

This uses synthetic data in a personal lab—not a production deployment or proof of production readiness.

**Where would this ownership split help—or create friction—in the platforms you work with?**

#AIAgents #PlatformEngineering #Kubernetes #AISecurity

### Option B: discussion-led angle

**A system prompt is not an access-control policy.**

As teams experiment with AI agents and MCP tools, how do we prevent instructions from being mistaken for authorisation?

This five-minute personal lab demo explores layered controls around identity, routing and network access—including what happens when a caller tries the wrong lane.

Synthetic data throughout; the results are scoped to the demonstrated tests.

**Which boundary would you want tested first before considering this pattern for wider use?**

#AIAgents #AISecurity #MCP #Kubernetes

## Video 2: Agent Substrate

**Runtime:** approximately 5:20

**Suggested workplace MP4:** `kagent-agent-substrate-corporate-lite-email-720p.mp4` (presentation and narration, without talking head).

**Public reference:** https://www.youtube.com/watch?v=3BTzlDPiVfk

Suggested existing topics to look for: AI agents, Kubernetes, Platform engineering, Agent Substrate. Reuse a broader established topic if no Agent Substrate topic exists.

### Option A: architecture explainer — recommended

**Can an AI agent pause without losing its session?**

An agent conversation and the compute running it don't have to have the same lifetime.

In this five-minute explainer, I walk through how Agent Substrate sits underneath kagent, then demonstrate storing a marker, suspending the logical session and returning to retrieve it.

The key idea: **retain session identity and state while allowing worker capacity to be reused**.

The video uses a sanitised reconstruction of a synthetic lab run. It demonstrates session continuity—not measured cost savings or production-scale performance.

**Where do you see this pattern being useful: long-running workflows, intermittent specialist agents, or something else?**

#AIAgents #Kubernetes #PlatformEngineering #AgentSubstrate

### Option B: workload-efficiency angle

**What should happen to an agent's compute while it waits?**

Agent workloads can be bursty: a request, some tool calls, then an idle gap.

This short explainer explores separating the logical session from its worker allocation, using kagent and Agent Substrate. The demonstration follows a session through storing state, suspension and return.

It's a personal lab example using synthetic data—not a benchmark or a claim of zero idle platform cost.

**What would you need to verify before trusting a resumed agent session—state integrity, identity, isolation or recovery behaviour?**

#AIAgents #CloudNative #PlatformEngineering #AgentSubstrate

## Evidence boundaries to preserve

- The agentgateway video demonstrates scoped lab results: approved agent-to-tool paths worked, while the tested rogue credentials and direct path failed. It does not establish live Entra integration, production AKS readiness or comprehensive security certification.
- The Substrate video demonstrates continuity for the tested logical session and synthetic marker. Do not translate that into measured worker-capacity gains, cost savings, production-scale performance or comprehensive tenant isolation.
- Public YouTube availability is not evidence of approval for internal publication. Apply the organisation's sharing rules before posting.

## Microsoft posting references

Platform guidance checked on 8 October 2026. Tenant settings and licensing may affect the available controls.

- [Start a conversation in Viva Engage](https://support.microsoft.com/en-gb/viva/engage/start-a-conversation-in-viva-engage): https://support.microsoft.com/en-gb/viva/engage/start-a-conversation-in-viva-engage
- [Use topics and hashtags in Viva Engage](https://support.microsoft.com/en-au/viva/engage/use-topics-in-viva-engage): https://support.microsoft.com/en-au/viva/engage/use-topics-in-viva-engage
- [Attach files and images in Viva Engage](https://support.microsoft.com/en-au/viva/engage/attach-files-and-images-in-viva-engage): https://support.microsoft.com/en-au/viva/engage/attach-files-and-images-in-viva-engage
