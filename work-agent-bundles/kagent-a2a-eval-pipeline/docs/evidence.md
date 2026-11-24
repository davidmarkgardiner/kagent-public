# Evidence and limits

Full record: `evidence/LIVE-PROXMOX-2026-11-23.md`. Sanitized live receipts are regression fixtures in `tests/fixtures/`.

| Result | Detail |
|---|---|
| Assay, kagent 0.7.13, through the gateway | smoke 1.0 (6 s); full pass^3 1.0, 1.0, 1.0; 4 of 4 tool calls captured on every repeat |
| Assay caught a real bug | A deterministic `contextId` made a second agent, or a rerun, get 403. Every call now gets a unique id |
| Warden, kagent 0.7.13 | 1 live PASS (`route=ticket`); the worker reworded its report after PASS, so the receiver delivers the approved text |
| Warden, kagent 1.0.0-alpha17 (A2A 1.0, subAgent) | 3 live runs: PASS, FAIL (worker omitted the `contract:` line, a correct block), PASS |
| Review | Codex found 7 ways to get a false PASS in the first version of the verifier; all fixed, each with a test |

## Not proven

- Three live Warden passes in a row; a first-try FAIL on 1.x has no retry and its route is undecided.
- The FAIL → fix → retry loop on 0.7.x was not re-run after the 1.x work.
- The GitLab receiver write and read-back.
- kagent 1.0.1 (the profile version); only alpha17 was run.
- The forbidden-tool check relies on agent history; join gateway or OTel audit data to prove it.
- `judge.py` scores are uncalibrated and advisory.
