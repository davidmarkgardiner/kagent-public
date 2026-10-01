# Admission-gate validation evidence — 1 October 2026

The strict implementation accepts only limits one and two, with no critical or
urgent bypass. Earlier 1/2/3 prototype results are superseded.

## Completed verification

- 21 behavioral tests passed against real disposable PostgreSQL 16: intake
  replay, concurrent report/publish, restart, owner grouping, namespace limits,
  critical-no-bypass, extra outbox intents, broker-history failure, database
  rollback, seven accelerated dates, ambiguous sends, expiry, DST, HTTP auth,
  database-outage 503 and required Kafka TLS.
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

A subsequent small 30-day outbox/budget pruning delta adds a 22nd test. Its
runtime verification was blocked locally by sandbox restrictions; the scoped
GitHub CI workflow runs the complete final suite and real Docker wire proofs.
Do not treat a pending/skipped CI run as a pass.

No workplace rollout, actual ticket cap, agent advice, complete health coverage,
PV/backup disaster recovery, security or long-duration unattended proof is claimed.
