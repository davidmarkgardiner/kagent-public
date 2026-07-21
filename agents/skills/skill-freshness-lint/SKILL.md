---
name: skill-freshness-lint
description: Detect and fix reference rot in the shipped skills — dead paths, foreign machine-local paths, and drifted duplicate skill copies. Use when editing any SKILL.md, during weekly maintenance, or when asked to check the skills.
---

# Skill Freshness Lint

Reference rot in skills silently burns agent time: a dead path is discovered
only by walking into it mid-task. Run the linter; fix everything it reports.

## Run

```bash
scripts/check-skill-refs.sh          # verbose
scripts/check-skill-refs.sh --quiet  # findings only (CI-friendly)
```

It reports:

- `FOREIGN_PATH` — machine-local paths (home-directory layouts such as
  `~/clawd`, `/home/<user>`, `/Users/<user>`) that only worked on the
  original author's machine. Replace with the in-repo path
  (`agents/skills/<name>/scripts/…`) or a `{{PLACEHOLDER}}`.
- `MISSING_TARGET` — a backticked path whose target does not exist. Fix the
  path if the file moved; remove or replace the promise if it never existed.
- `DIVERGED` — a canonical skill and its bundle/payload copy differ when they
  are expected to be identical. Diff them, decide which side is canonical
  (bundle payloads follow `work-agent-bundles/SHARED-VARIABLES.md`
  placeholder names), and sync.

Exit 0 = clean; exit 1 = findings to fix.

## Fixing rules

- Skill-local helpers referenced from a SKILL.md must live inside the skill
  directory (they ship in the skill image — see
  `agents/skills/skills-as-images/`); repo-root `scripts/` helpers must be
  called with a "run from the repo root" note.
- Do not delete a documented capability to silence the linter — either create
  the promised file or rewrite the reference to point at what actually
  exists.
- Watch for stale API teaching while editing: anything recommending the
  kagent session/chat API (`/api/chat`, `/api/sessions`) is wrong for
  v0.8.0-beta4 — route it to `scripts/kagent-a2a-invoke.sh` instead.
