#!/usr/bin/env bash
# check-skill-refs.sh — lint the shipped skills for reference rot.
#
# Catches the failure modes an agent otherwise discovers only by walking into
# them mid-task:
#   1. Foreign machine-local paths (~/clawd/…, /home/…, /Users/…) in skill docs
#   2. Backticked repo-relative or skill-relative paths whose target no longer
#      exists
#   3. Silent divergence between a canonical skill and its bundle/payload copy
#
# Usage: scripts/check-skill-refs.sh [--quiet]
# Exit codes: 0 clean; 1 findings; 2 tooling error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

FINDINGS=0

say() { [[ "$QUIET" -eq 0 ]] && echo "$@" || true; }
finding() { echo "$@"; FINDINGS=$((FINDINGS + 1)); }

SKILL_DOCS=()
while IFS= read -r f; do
  SKILL_DOCS+=("$f")
done < <(find agents/skills \( -name 'SKILL.md' -o -name 'yaml-to-kro.md' \) \
  -not -path '*/example-skill/*' | sort)
# example-skill is excluded: it is a deliberately incomplete scaffold template.

# ---- 1. Foreign machine-local paths ----------------------------------------
for doc in "${SKILL_DOCS[@]}"; do
  while IFS= read -r hit; do
    finding "FOREIGN_PATH $hit"
  done < <(grep -nHE '~/clawd/|/home/[a-z]+/|/Users/[a-z]+/' "$doc" || true)
done

# ---- 2. Referenced paths must exist ----------------------------------------
# Backticked paths are resolved first against the repo root, then against the
# skill's own directory (the convention for scripts/, references/, assets/,
# templates/, tests/, evals/ shipped inside the skill).
for doc in "${SKILL_DOCS[@]}"; do
  skill_dir="$(dirname "$doc")"
  while IFS= read -r raw; do
    path="${raw#\`}"
    path="${path%\`}"
    # Skip placeholders, globs, URLs, and command-looking strings
    [[ "$path" == *'{{'* || "$path" == *'*'* || "$path" == *'<'* ]] && continue
    [[ "$path" == http* || "$path" == *' '* ]] && continue
    case "$path" in
      agents/*|docs/*|infra/*|observability/*|work-agent-bundles/*|demos/*|platform/*|a2a/*|k8s/*|chaos/*)
        if [[ ! -e "$path" ]]; then
          finding "MISSING_TARGET $doc -> $path"
        fi
        ;;
      scripts/*|references/*|assets/*|templates/*|tests/*|evals/*)
        # scripts/ etc. may be skill-local or repo-root shared helpers
        if [[ ! -e "$skill_dir/$path" && ! -e "$path" ]]; then
          finding "MISSING_TARGET $doc -> $path (checked repo root and $skill_dir)"
        fi
        ;;
    esac
  done < <(grep -ohE '`[A-Za-z0-9._{}/-]+`' "$doc" | sort -u || true)
done

# ---- 3. Duplicate copies must not drift ------------------------------------
# Pairs expected to stay byte-identical (canonical -> bundle/payload copy).
IDENTICAL_PAIRS=(
  "agents/skills/grafana-chaos-incident-triage/SKILL.md work-agent-bundles/sre-grafana-mcp-observability/payload/agents/skills/grafana-chaos-incident-triage/SKILL.md"
  "agents/skills/grafana-incident-evidence-pack/SKILL.md work-agent-bundles/sre-grafana-mcp-observability/payload/agents/skills/grafana-incident-evidence-pack/SKILL.md"
  "observability/grafana/dashboard-registry.yaml work-agent-bundles/sre-grafana-mcp-observability/payload/observability/grafana/dashboard-registry.yaml"
)
# Known-divergent pair: the bundle copy of evidence-first-worker-triage is a
# substantive rewrite (different sidecars), not a mirror. Reported as INFO only.
DIVERGENT_PAIRS=(
  "agents/skills/evidence-first-worker-triage/SKILL.md work-agent-bundles/evidence-first-worker-triage/skill/evidence-first-worker-triage/SKILL.md"
)

for pair in "${IDENTICAL_PAIRS[@]}"; do
  a="${pair%% *}"
  b="${pair#* }"
  if [[ ! -f "$a" || ! -f "$b" ]]; then
    finding "MISSING_COPY $a or $b"
    continue
  fi
  if ! diff -q "$a" "$b" >/dev/null; then
    finding "DIVERGED $a <> $b (expected identical; sync them)"
  fi
done

for pair in "${DIVERGENT_PAIRS[@]}"; do
  a="${pair%% *}"
  b="${pair#* }"
  [[ -f "$a" && -f "$b" ]] || continue
  say "INFO known-divergent pair (by design): $a <> $b"
done

if [[ "$FINDINGS" -eq 0 ]]; then
  say "SKILL_REFS_OK: ${#SKILL_DOCS[@]} skill docs checked, no rot found"
  exit 0
fi
echo "SKILL_REFS_FINDINGS: $FINDINGS" >&2
exit 1
