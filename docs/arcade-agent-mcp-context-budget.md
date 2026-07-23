# Arcade Agent — MCP Context Bloat & Token Burn Assessment

**Question:** Agents spawn ephemerally, do one specific task, connect to 3–4 MCPs (EKS, Grafana, GitLab issues). Task scope is narrow and they aren't hoarding logs. Is context bloat / token burn a real concern?

**Short answer:** Mostly no for the *reasoning* — but narrow tasks do **not** guarantee narrow context. Two costs the "gut check" misses: the upfront **tool-schema tax** across 3–4 MCPs, and **tool-response bloat** from k8s/Grafana/GitLab reads. Neither is about logs. Both are controllable.

---

## Where the tokens actually go (ranked)

### 1. Tool-schema tax — upfront, every agent spawn (biggest hidden cost)

When an agent connects to an MCP server, the server injects **all** of its tool definitions into the agent's context *before the agent does any work*. Each definition = tool name + description + full JSON input schema.

Rough per-server footprint:

| MCP server | Typical tool count | Approx. schema tokens |
|---|---|---|
| Kubernetes / EKS | 20–40 | 8k–25k |
| Grafana | 10–20 | 4k–12k |
| GitLab | 20–30 | 8k–18k |
| **Total (3–4 servers)** | **50–90 tools** | **~15k–50k tokens** |

This tax is paid:
- **Per agent spawn** (ephemeral agents re-pay it every time — the flip side of statelessness).
- **Even if the agent calls only 2 tools.** You load 90 schemas to use 3.
- **Before any task logic runs.**

This is the dominant cost and the one the "narrow task" intuition doesn't see.

### 2. Tool-response bloat — the "not log-wanting" blind spot

Narrow tasks still return wide payloads. These are normal reads, not logs:

- `kubectl get <resource> -A -o yaml` / `describe` → **50k–150k tokens** in one call.
- Grafana query returning raw time-series JSON → tens of thousands of tokens.
- GitLab "list issues" with full bodies/comments → unbounded with project size.

A single unbounded read spikes the whole budget. The agent asked one specific question ("is the pod healthy?") and got the entire cluster state back.

### 3. Task instruction + reasoning — genuinely small

This is what the gut check is measuring, and it's right. A tightly-scoped prompt + a few tool calls of reasoning is a few thousand tokens. Not the problem.

---

## Why ephemeral agents help (and where they don't)

**Help:**
- Context doesn't accumulate turn-over-turn — no long-session creep.
- Blast radius is contained per spawn; a bloated agent dies and takes its context with it.

**Don't help:**
- Cost #1 (schema tax) is **re-paid on every spawn** — statelessness makes it recurring, not one-time.
- Cost #2 (response bloat) — one bad `get -o yaml` still blows a single agent's window regardless of lifetime.

---

## Mitigations (do these; then it's a non-issue)

1. **Per-agent tool allowlist / scoping.** Biggest lever. Don't load the whole MCP — expose only the 3–4 tools that agent role needs (e.g. read-only `get`/`describe`, not the full write surface). Kills most of cost #1.
2. **Bound every read.** Field selectors, `-o jsonpath`, label filters, `jq` projection, pagination/limits. Never `-A -o yaml` when you want one pod's status.
3. **Output truncation caps.** Hard ceiling on tool-response size returned to the model; truncate + note truncation.
4. **Summarize-before-return.** For unavoidably large sources, have a cheap step reduce to the signal (status, deltas, error lines) before it hits the reasoning context.
5. **Split by role, not by "connect everything."** An EKS-check agent shouldn't carry GitLab's 30 tool schemas. Match MCP set to task.

---

## Verdict

- **Reasoning/instruction burn:** low. Gut is correct.
- **Schema tax:** real, recurring, ~15k–50k tokens/spawn — but eliminated by tool scoping.
- **Response bloat:** real, spiky, single-call — but eliminated by bounded reads + output caps.

Net: **not a concern once tool sets are scoped per agent and reads are bounded.** It becomes a concern if agents connect to full MCPs and issue unbounded reads. The fix is cheap and belongs in the agent CRD / MCP config, not in the reasoning.

---

## Config checklist

- [ ] Each agent role declares only the MCP tools it calls (allowlist in the agent spec).
- [ ] Read tools default to filtered/projected output, never full dumps.
- [ ] Output-size cap enforced at the tool-server boundary.
- [ ] Large sources routed through a summarize step.
- [ ] Verify schema footprint: count tools × avg schema size per connected server.
