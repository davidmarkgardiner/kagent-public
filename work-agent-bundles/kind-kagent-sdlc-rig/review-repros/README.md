# Offline review reproductions

These credential-free fake-GitLab scripts were supplied with the independent
review of commit `02ff4daad92905585f6ebf933934242e047d1731`. They preserve
the original observations for A2, A3, A6, A7, and B1 in `REVIEW-TASKS.md`.
They print behaviour; they are **not** passing regression tests or live GitLab
evidence. A10 should turn the relevant cases into assertions in
`test_board_poller.py` and verify they fail before, then pass after, each fix.

To reproduce the original failures, pass a separate checkout of commit
`02ff4daa` to the scripts. They use minimal fakes for that revision and are
not expected to run against the updated poller API. From this directory:

```bash
python3 review-repros/repro_findings.py <path-to-02ff4daa-bundle>
python3 review-repros/repro_ci_loop.py <path-to-02ff4daa-bundle>
```

The first script demonstrates an old branch bypassing build, a new SHA reaching
accept without a matching test marker, a forged PASS note being accepted, and
one malformed issue stopping the next issue. The second demonstrates 30 CI
failure/rework polls without reaching `agent:blocked`. These expected outputs
describe the reviewed revision. Run `python3 -m unittest discover -s .
-p 'test_*.py'` for the current fixed branch.
