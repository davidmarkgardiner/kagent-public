# Business Case: Extend Embedded Engineer Contracts — kagent / Agentic Harness

## Situation

Two embedded engineers currently deliver and run the kagent agentic remediation
platform (agents plus the Vector/Kafka/Argo/AKS harness). The wider team has no
other engineers with the skills, experience, or exposure to take this on, and
there is no permanent internal owner for the area.

This is effectively a **bus factor of one**. The platform automates remediation
actions against production — including write-capable changes — so the continuity
risk is not just delivery slippage, it is operational safety.

## Business Impact If They Leave

**1. Loss of institutional knowledge.** One engineer holds 3–4 years of
accumulated context: why design decisions were made, where the sharp edges are,
and how the AKS hardening constraints, Kafka ACLs, and agent governance fit
together. Realistically this takes **two engineers to backfill one departure**,
and even then only after a long ramp.

**2. No internal fallback.** No one else in the team can take over, review, or
safely operate the platform. If both leave, the system runs unowned — changes
stop, incidents go unhandled by anyone who understands the automation, and the
auto-remediation cannot be audited or trusted.

**3. Long, expensive ramp-up.** Backfilling means hiring or training across eight
distinct skill areas (AKS platform, Kafka/Confluent, Argo Events/Workflows,
Vector/observability, kagent/MCP agent design, automation security/governance,
SRE/incident ops, GitOps delivery — per the skills work order). With no internal
base to build on, expect **6–12 months** before a replacement is independently
productive, with reduced platform velocity throughout.

**4. Safety and security exposure during the gap.** The platform triggers
automated, write-capable remediation. With no skilled owner, known risks
(untrusted-input automation gating, config parity, credential/ACL boundaries —
already flagged in review) go unmaintained. The most likely failure mode is a
self-inflicted production incident that no one internal can diagnose.

**5. Stalled roadmap and sunk investment.** Work already invested in the harness
loses momentum or is abandoned. The value case (incident/MTTA/MTTR reduction)
never gets proven because the capability to instrument and measure it is gone.

## Why Extend the Contract

- **Continuity of a safety-critical system** with no internal alternative — the
  cheapest risk control available now.
- **Protects 3–4 years of accumulated knowledge** that cannot be re-acquired on
  any reasonable timeline.
- **Buys time for deliberate knowledge transfer** rather than abrupt loss — the
  extension should be paired with a documentation/runbook handover so the
  platform becomes maintainable regardless of who holds the contract.
- **Far cheaper than the alternative:** two backfill hires plus a 6–12 month ramp
  plus the cost of an unowned production-automation gap vastly exceeds an
  extension.

## Recommendation

Extend both contracts, and use the extension period to fund a structured
**knowledge-transfer and documentation** workstream (runbooks, config-parity,
ownership map) so the platform is no longer a single-person dependency. This
converts the spend from "keeping the lights on" into permanently de-risking the
platform.
