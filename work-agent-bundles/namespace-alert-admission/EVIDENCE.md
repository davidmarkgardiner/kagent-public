# Admission-gate validation evidence — 1 October 2026

The strict implementation accepts only limits one and two, with no critical or
urgent bypass. Earlier 1/2/3 prototype results are superseded.

## Completed verification

- 22 behavioral tests passed against real disposable PostgreSQL 16: intake
  replay, concurrent report/publish, restart, owner grouping, namespace limits,
  critical-no-bypass, extra outbox intents, broker-history failure, database
  rollback, seven accelerated dates, ambiguous sends, expiry, DST, HTTP auth,
  database-outage 503, required Kafka TLS and 30-day retention without historical
  allowance refund.
- Actual Vector 0.45 HTTP sink delivered 40 synthetic envelopes to PostgreSQL;
  shadow mode created zero Kafka intents.
- Actual Kafka 3.9.1 transactional publication/committed consumption returned
  exactly two records from 40 candidates; 38 groups deferred; replay sent zero.
- [Initial home-lab transport proof](evidence/2026-10-01-home-lab-transport.md).
- [Strict home-lab restart/recovery proof](evidence/2026-10-01-strict-admission.md):
  real Alloy → Vector → gate → Kafka, seven accelerated dates, four concurrent
  publishers, lost budget state, fenced ambiguous transactions and topic replacement.
- The runner confirmed all isolated namespaces were removed.

## Remaining verification

The final retention change and complete 22-test suite passed on GitHub for
commit `37e3a88068acaf38a61800b67875c5876ad4d7a3`, together with actual Vector
intake and committed Kafka produce/consume:
https://github.com/davidmarkgardiner/kagent-public/actions/runs/36927976947

That run's separate public-safety step was blocked by missing ripgrep. The
workflow now installs the dependency and reruns the full suite and scan. Check
the latest branch CI status for its overall verdict. The local public-safety
and Gitleaks scans were clean; detect-secrets' five findings were reviewed as
SHA-256 code fingerprints in the evidence receipt, not credentials.

No workplace rollout, actual ticket cap, agent advice, complete health coverage,
PV/backup disaster recovery, security or long-duration unattended proof is claimed.
