# Guard, overseer and spend guards

Full design and status: [monitoring loop and guard](alert-loop.md). Evidence: `evidence/GUARD-AND-LOOP-2026-11-24.md`.

| Part | What it does | Tested |
|---|---|---|
| `guard/detect.py` | Deterministic detector: long runs, token burn, tools outside the allowlist, non-200 bursts, failed tasks, Warden blocks. Missing data is `degraded`, never `clean` | offline and live on the lab |
| `guard/propose.py` | Ticket plus a block-policy **proposal**. Identity only from a trusted map; never-block list; hostile text quoted; never applies | live dry-run only |
| `guard/alert_to_a2a.py` | Alertmanager payload to an agent-health request. Human-only alerts never reach an agent; no self-trigger | offline |
| `guard/circuit.py` | Attempt cap, permanent errors never retried, bounded 429 backoff, circuit breaker, token budget, kill switch, fail-closed state | offline |
| Guard and agent-health agents | Explain findings and draft issues; no write credentials; gated by Warden contracts | Guard 3 of 3; agent-health not passing live yet: its model 400 (a 4.4 MB tool result) was fixed, then it wandered for 245000 tokens and wrote no report; a tool-call budget and a better prompt now gate it, untested live |

Commands: `python guard/detect.py --events <receipts> --agent <name>`, then `python guard/propose.py --findings out.json --identity-map map.yaml --out dir`.
Run `--dry-run-server --context <explicit>` to have the API server validate a proposal; it still changes nothing.
