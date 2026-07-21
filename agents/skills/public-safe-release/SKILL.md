---
name: public-safe-release
description: Sanitize content for this public repo and gate it with the shared public-safety scan. Use when asked to sanitize, make public-safe, run pre-push/pre-publish checks, or move work-environment content into kagent-public.
---

# Public-Safe Release

Gate any content bound for this public repository through the shared scanner,
then apply judgment only to the hits.

## Workflow

1. Run the scan (from the repo root) on the files or directory being released:

   ```bash
   scripts/public-safe-scan.sh <path> [--strict] [--json]
   ```

   Default patterns catch RFC1918 addresses, private registry hosts,
   `PRIVATE-TOKEN`, and `password=`. `--strict` adds bearer/token/GUID
   patterns — use it for handover packages.

2. For every hit, decide: real leak or false positive?
   - **Real leak** — replace with the canonical `{{PLACEHOLDER}}` per
     `AGENTS.md` ("Do not add secrets, private hostnames, private cluster
     IPs, subscription IDs, tenant IDs, internal URLs, or real tokens") and
     `work-agent-bundles/SHARED-VARIABLES.md` placeholder names.
   - **False positive** (e.g. a scan pattern quoted in a verifier, a
     documented example placeholder) — add the file to an allowlist and
     re-run with `--allowlist FILE`.

3. Re-run until the scan is clean, then record the gate in your output:

   ```text
   OUTPUT_SANITIZED: yes
   ```

## Rules

- Never "fix" a hit by deleting the surrounding content wholesale — replace
  the private value with a placeholder and keep the documentation intact.
- Never claim `OUTPUT_SANITIZED: yes` without a clean scan run in this
  session.
- Bundle verifiers embed the same patterns; when creating a new bundle
  verifier, call `scripts/public-safe-scan.sh` instead of copying the rg
  block (drift in hand-copied scans is how four bundles shipped with no scan
  at all).
