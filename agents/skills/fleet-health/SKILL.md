---
name: fleet-health
description: Monitor agent gateways, detect failures, attempt safe remediation, and escalate when human action is needed.
---

# Fleet Health Monitor

Monitors all agent gateways, detects failures, auto-remediates where possible, and escalates to David when human action is needed.

## When to Use
- Heartbeat checks (automatic, every cycle)
- When an agent stops responding
- After cluster reboots
- When David asks about fleet status

## Quick Check
```bash
~/clawd/skills/fleet-health/scripts/fleet-check.sh
```

## What It Monitors

| Check | Auto-Fix | Needs David |
|-------|----------|-------------|
| Gateway process down | ✅ Restart via systemd | ❌ |
| Wrong model configured | ✅ Update config + restart | ❌ |
| OAuth token expired | ❌ | ✅ Re-auth via browser |
| API quota exhausted | ⚠️ Switch to fallback model | ✅ Top up credits |
| VM unreachable | ⚠️ WoL if in shutdown window | ✅ If hardware issue |
| Device signature invalid | ✅ Re-pair device | ❌ |
| Heartbeat model wrong | ✅ Fix config | ❌ |
| Service not enabled | ✅ Enable + start | ❌ |

## Expected Models (DO NOT CHANGE without David's approval)

| Agent | Primary Model | Heartbeat Model |
|-------|--------------|-----------------|
| Scotty (local) | anthropic/claude-opus-4-6 | anthropic/claude-sonnet-4-6 |
| Codex (192.168.6.105) | openai-codex/gpt-5.3-codex | openai-codex/gpt-5.3-codex |
| Gem (192.168.6.10) | google-gemini-cli/gemini-3.1-pro | google-gemini-cli/gemini-2.5-flash |
| Kimi (192.168.6.104) | kimi-code/kimi-for-coding | kimi-code/kimi-for-coding |

## Fallback Models (when primary is unavailable)

| Agent | Fallback | When to Use |
|-------|----------|-------------|
| Codex | google-gemini-cli/gemini-2.5-pro | OpenAI quota exhausted / OAuth expired |
| Gem | google-gemini-cli/gemini-2.5-pro | If 3.1 not available on version |
| Kimi | (none — wait for VM) | Only offline during shutdown hours |

## Escalation

When human action is needed, send a Telegram message to David with:
- Which agent is affected
- What the problem is
- Exact steps to fix (copy-paste ready)
- Urgency level (🔴 now / 🟡 next session / 🟢 whenever)

## Auth Token Lifecycle

**OpenAI Codex OAuth:** Refresh tokens are single-use. Each time OpenClaw refreshes, the old token is consumed. If a refresh fails (network blip, crash mid-refresh), the token is burned and needs manual re-auth.

**Expected re-auth frequency:** Every few weeks to months, depending on token expiry.

**Re-auth steps for David:**
```
ssh david@192.168.6.105
openclaw configure --section model
# Select openai-codex → browser opens → login → done
```

**Google Gemini OAuth:** More durable — uses standard Google OAuth with auto-refresh. Rarely needs re-auth.

**Kimi API:** Token-based, doesn't expire unless rotated manually.
