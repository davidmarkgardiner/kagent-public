# Business Case: Increase Monthly GitHub Copilot Token Allocation from 10,000 to 20,000

**Requested change:** 10,000 → 20,000 tokens per month (team allocation)
**Audience:** Engineering management
**Status:** Draft for approval

---

## 1. Summary

Our engineering team routinely exhausts its monthly Copilot token allocation before month end. Because day-to-day development now depends on AI agents, running out stops us from iterating and delivering, not just from working faster. We are asking for the allocation to be doubled to 20,000 tokens per month.

We have already minimised cost: roughly 90% of our usage is on the lowest-cost model (Luna), and we use Sol and Terra only for complex or difficult tasks. We are still running out.

## 2. Context

- The team does feature development and implementation, plus a high volume of proof-of-concept work in the AI space.
- New AI applications and tools keep arriving. We must learn how each works and how it integrates with our current systems. That is exploratory, trial-and-error work that burns tokens by nature.
- Agents are now a core part of how we build. They are a dependency for delivery, not a convenience.

## 3. Problem

| Factor | Impact |
|---|---|
| Exploratory / proof-of-concept work | Many iterations, many discarded; tokens spent before value is known |
| Integration of new AI applications | Learning and wiring up unfamiliar systems is token-heavy |
| Agent dependency | Allocation exhausted = team cannot build, iterate or deliver |
| Month-end exhaustion | Work stalls or slips until the allocation resets |

## 4. What we are already doing right

- **Cheapest model by default.** Luna is used about 90% of the time.
- **Premium models by exception.** Sol and Terra only for complex or difficult tasks.
- **Intended-use compliance.** Usage is for development and building. It is not for debugging or general engineering tasks outside the intended scope.
- **We are trying to stay within the rules** and still cannot make the allocation last the month.

## 5. Why this is a capacity problem, not a discipline problem

Usage is already optimised on model choice and scope. The remaining driver is volume of legitimate work: PoCs, new-application evaluation and feature delivery.

Allocation also does not roll over or transfer. In one month a team member lost about two weeks to an outage of their dev environment and could not use or borrow their tokens. Even in months with reduced working time (leave, outages), the allocation has not stretched far enough. In a full-capacity month, it falls well short. Usage history is available for review and supports this.

## 6. The request

Double the monthly allocation from **10,000 to 20,000 tokens**.

### Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Double to 20,000 (recommended)** | Removes month-end stalls; keeps cheap-model default; simple | Higher spend |
| B. Stay at 10,000 | No extra cost | Continued stalls; slower delivery; PoCs deferred |
| C. Raise a smaller amount (e.g. 15,000) | Lower cost | Likely still runs short; may need a second request |

## 7. Benefits

- **Continuity:** the team can work and deliver all month.
- **Faster experimentation:** we can validate or discard ideas quickly instead of rationing attempts.
- **Better integration outcomes:** room to learn new AI applications properly before adopting them.
- **Predictability:** delivery dates no longer depend on when tokens run out.

## 8. Cost and controls

- **Cost:** [insert incremental monthly cost for +10,000 tokens]
- **Cost of not acting:** [insert estimate, e.g. engineer-days lost per month × day rate]
- **Controls we will keep:**
  - Luna remains the default; Sol/Terra for complex tasks only.
  - Monthly usage review with the model split reported.
  - Revisit at [3 months] and reduce if usage does not justify the increase.

## 9. Success measures

- Zero working days lost to exhausted allocation.
- Luna share stays at or above 90%.
- Monthly usage reported and reviewed.

## 10. Decision requested

Approve an increase to 20,000 tokens per month, effective [date], with a review after [3 months].

---

*Before sending: fill in the bracketed placeholders (cost, dates) and attach a usage-history export showing monthly consumption and the Luna/Sol/Terra split.*
