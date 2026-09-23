# Full Script

## Recording contract

- Target runtime: **5:20**
- Delivery: measured, conversational and technically precise
- Structure: 15 independently replaceable narration segments matching the approved storyboard
- Timing authority: approved narration audio for each segment will set its final frame duration
- Fixture language: always say or show `synthetic` when discussing incident, release or MCP data
- Evidence language: distinguish the current read-only status check from the recorded 2026-09-16 functional run
- Identity treatment: voice-led by default; any presenter disclosure is added only after a presenter choice is separately approved

## N01 · 0:00–0:15 · The side-door problem

Giving each application team its own Kubernetes namespace makes agent delivery fast. But if every team exposes its agent and MCP tool differently, self-service also creates side doors around identity, routing and network controls.

## N02 · 0:15–0:35 · Promise and mental model

The platform answer is simple: one front door, separate locked lanes, and no side doors. In this red-cluster rehearsal, we’ll send an event, a chat request and a platform security review through their approved lanes. Then we’ll watch a rogue namespace fail.

## N03 · 0:35–1:00 · Who owns what

Each team owns the useful part: its namespaced Agent, its system prompt and skills, and its MCP workload. The platform keeps control of the shared safety boundary: the Gateway, HTTP routes, authentication policies, reference grants and network policy. Teams can change agent behaviour without taking ownership of the front door.

## N04 · 1:00–1:25 · The request chain

An approved request never jumps straight to a Pod. It enters a dedicated agentgateway listener, passes the identity and claim policy, follows an HTTPRoute to the correct kagent Agent, and only that Agent can reach its namespaced MCP service. That is the complete chain we need for the demonstration.

## N05 · 1:25–1:50 · Four enforcement boundaries

The lock is layered. Identity decides who the caller is. The listener and route select the permitted lane. Reference grants constrain typed cross-namespace links. Network policy removes the direct Pod-to-Pod shortcut. And one warning matters here: a system prompt supplies context. It is not authorization.

## N06 · 1:50–2:15 · Event-driven team

The first application team runs an incident-adviser Agent with its own instructions and an incident MCP fixture. A synthetic event becomes an A2A request, enters the event listener, and reaches that Agent. The Agent may call the event team’s tool, but it has no route to the chat team’s tool.

## N07 · 2:15–2:35 · Interactive team

The second team uses the same platform contract for a different experience. A person asks the release-adviser Agent a question, and that Agent reaches only its own release MCP fixture. The interaction changed from event to chat. The front-door rule did not.

## N08 · 2:35–2:50 · Substrate and the negative control

A fifth listener fronts a platform-owned security specialist backed by Agent Substrate. The rogue namespace owns none of these lanes. It exists for one reason: to test the boundary from the wrong side.

## N09 · 2:50–3:10 · Starting state

First, the status check. All five routes are accepted with resolved references. Both team Agents report ready. The platform specialist is accepted and ready, its actor template is ready with a snapshot, and the worker pool has all three replicas present.

## N10 · 3:10–3:35 · Event proof

Now the recorded functional run. A synthetic incident enters the event lane. The incident adviser completes its A2A task and calls the event MCP. The event counter increases by one, while the chat counter stays unchanged. The approved lane produced exactly the state change we expected.

## N11 · 3:35–4:00 · Chat proof

Next, a synthetic release question enters the chat lane. The release adviser completes its task, the chat MCP counter increases by one, and the event counter stays still. A different team and a different interaction used the same platform-controlled route without crossing into the other team’s tool.

## N12 · 4:00–4:20 · Substrate lifecycle proof

The platform security request uses the fifth listener. Its specialist completes the review and returns the required trust-boundary and security-verdict sections. After the response, the actor returns to Suspended and the recorded run shows a new snapshot present.

## N13 · 4:20–4:40 · Rogue denial

Finally, the negative control. No credential returns 401. A token for the wrong lane returns 401. Correctly signed credentials carrying rogue claims return 403. And the tested direct path to the Substrate specialist times out or is refused. In this rehearsal, the side door stays closed.

## N14 · 4:40–5:00 · What this proves

So the red rehearsal proves a scoped result. Two team-owned Agent-to-MCP paths and one platform-owned Substrate specialist worked through dedicated agentgateway controls, while the tested rogue credentials and direct path failed at the intended boundaries.

## N15 · 5:00–5:20 · Boundary and takeaway

It does not yet prove live Entra, production AKS, external MCP security, or the target kagent and Substrate versions running together. Those remain promotion gates. The reusable rule is this: let teams own agent behaviour, but keep identity, routes and reachability inside the platform boundary.

## Recording notes

- Pause briefly after “one front door”, “separate locked lanes” and “no side doors”.
- Pronounce `kagent` as “kay-agent”, `MCP` as individual letters and `A2A` as “A-to-A”.
- Read HTTPRoute as “HTTP route”; do not spell it out.
- Keep `401` and `403` conversational: “four-oh-one” and “four-oh-three”.
- Segment N13 must sound factual rather than triumphant; it is scoped negative evidence.
- Leave approximately half a second of clean room tone at each segment boundary for assembly.
- Generate and approve one short sound-on audition using N02 and the first two sentences of N13 before producing the complete narration set.
