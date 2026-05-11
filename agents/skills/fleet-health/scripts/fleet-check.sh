#!/usr/bin/env bash
# Fleet Health Check — run from Scotty's heartbeat or manually
# Usage: fleet-check.sh [--fix] [--quiet] [--deep]
#
# Without --fix: report only
# With --fix: attempt auto-remediation
# With --quiet: only output problems (for heartbeat use)
# With --deep: run live auth tests (e.g. gemini echo test) in addition to log checks

set -euo pipefail

FIX=false
QUIET=false
DEEP=false
PROBLEMS=()
FIXES=()
ESCALATIONS=()

for arg in "$@"; do
  case $arg in
    --fix) FIX=true ;;
    --quiet) QUIET=true ;;
    --deep) DEEP=true ;;
  esac
done

log() { $QUIET || echo "$@"; }
problem() { PROBLEMS+=("$1"); echo "❌ $1"; }
fixed() { FIXES+=("$1"); echo "✅ FIXED: $1"; }
escalate() { ESCALATIONS+=("$1"); echo "🔴 ESCALATE: $1"; }
ok() { $QUIET || echo "✅ $1"; }

# --- Agent definitions ---
declare -A HOSTS=( [scotty]="local" [codex]="192.168.6.105" [gem]="192.168.6.10" [kimi]="192.168.6.104" )
declare -A PORTS=( [scotty]="18789" [codex]="18791" [gem]="18789" [kimi]="18790" )
declare -A MODELS=( [scotty]="anthropic/claude-opus-4-6" [codex]="openai-codex/gpt-5.3-codex" [gem]="google-gemini-cli/gemini-3.1-pro" [kimi]="kimi-code/kimi-for-coding" )
declare -A FALLBACKS=( [codex]="google-gemini-cli/gemini-2.5-pro" [gem]="google-gemini-cli/gemini-2.5-pro" )
declare -A SERVICES=( [scotty]="openclaw-gateway" [codex]="openclaw-gateway" [gem]="openclaw-gateway" [kimi]="openclaw-gateway" )

# Shutdown window: Proxmox VMs (192.168.6.x) are off 22:00-09:00 UTC weekdays, all weekend
in_shutdown_window() {
  local host="${HOSTS[$1]}"
  [[ "$host" == "local" ]] && return 1
  [[ ! "$host" =~ ^192\.168\.6\. ]] && return 1
  local hour=$((10#$(date -u +%H)))
  local dow=$(date -u +%u)  # 1=Mon, 7=Sun
  # Weekend
  (( dow >= 6 )) && return 0
  # Overnight
  (( hour >= 22 || hour < 9 )) && return 0
  return 1
}

run_remote() {
  local agent="$1"; shift
  local host="${HOSTS[$agent]}"
  if [[ "$host" == "local" ]]; then
    eval "$@"
  else
    ssh -o ConnectTimeout=5 -o BatchMode=yes "david@$host" "$@" 2>/dev/null
  fi
}

log "🔧 Fleet Health Check — $(date -u '+%Y-%m-%d %H:%M UTC')"
log "========================================"

for agent in scotty codex gem kimi; do
  log ""
  log "--- $agent (${HOSTS[$agent]}:${PORTS[$agent]}) ---"
  
  host="${HOSTS[$agent]}"
  port="${PORTS[$agent]}"
  expected_model="${MODELS[$agent]}"
  service="${SERVICES[$agent]}"

  # 1. Check if host is reachable
  if [[ "$host" != "local" ]]; then
    if ! ssh -o ConnectTimeout=3 -o BatchMode=yes "david@$host" 'echo ok' &>/dev/null; then
      if in_shutdown_window "$agent"; then
        ok "$agent: offline (expected — shutdown window)"
      else
        problem "$agent: host unreachable at $host"
        escalate "$agent: VM at $host not responding. Check Proxmox."
      fi
      continue
    fi
  fi

  # 2. Check gateway service is running
  svc_status=$(run_remote "$agent" "systemctl --user is-active $service.service 2>/dev/null" || echo "inactive")
  if [[ "$svc_status" != "active" ]]; then
    if in_shutdown_window "$agent"; then
      ok "$agent: service stopped (expected — shutdown window)"
      continue
    fi
    problem "$agent: $service.service is $svc_status"
    if $FIX; then
      run_remote "$agent" "systemctl --user start $service.service 2>/dev/null" && \
        fixed "$agent: started $service.service" || \
        escalate "$agent: failed to start $service.service"
    fi
    continue
  fi
  
  # 3. Check current model
  if [[ "$host" == "local" ]]; then
    current_model=$(grep -o '"primary": "[^"]*"' ~/.openclaw/openclaw.json | head -1 | cut -d'"' -f4)
  else
    current_model=$(run_remote "$agent" 'cat ~/.openclaw/openclaw.json 2>/dev/null || cat ~/.clawdbot/clawdbot.json 2>/dev/null' | grep -o '"primary": "[^"]*"' | head -1 | cut -d'"' -f4)
  fi
  
  if [[ "$current_model" != "$expected_model" ]]; then
    problem "$agent: wrong model '$current_model' (expected '$expected_model')"
    if $FIX; then
      # Check if we should fix or use fallback
      escalate "$agent: model mismatch — may need re-auth. Current: $current_model, Expected: $expected_model"
    fi
  else
    ok "$agent: model $current_model"
  fi

  # 4. Auth validation — lightweight log scan always; live test with --deep
  case "$agent" in
    gem)
      # Check ~/.gemini/settings.json exists and has auth
      gemini_settings=$(run_remote "$agent" 'cat ~/.gemini/settings.json 2>/dev/null' || true)
      if [[ -z "$gemini_settings" ]]; then
        problem "$agent: ~/.gemini/settings.json missing — Gemini CLI not authenticated"
        escalate "$agent: run 'gemini auth' on ${HOSTS[$agent]} to re-authenticate"
      else
        # Look for an auth token or credentials block
        if echo "$gemini_settings" | grep -qi '"token"\|"credentials"\|"oauth"\|"access_token"'; then
          ok "$agent: ~/.gemini/settings.json present with auth config"
        else
          problem "$agent: ~/.gemini/settings.json exists but no auth fields found"
          escalate "$agent: Gemini settings may be incomplete — check auth on ${HOSTS[$agent]}"
        fi
      fi

      # Log-based auth scan (always)
      gem_auth_errors=$(run_remote "$agent" "journalctl --user -u ${SERVICES[$agent]}.service --since '5 min ago' --no-pager 2>/dev/null" \
        | grep -ciE "error|401|403|404|auth|quota|Cloud Code Assist" || true)
      if (( gem_auth_errors > 0 )); then
        gem_sample=$(run_remote "$agent" "journalctl --user -u ${SERVICES[$agent]}.service --since '5 min ago' --no-pager 2>/dev/null" \
          | grep -iE "error|401|403|404|auth|quota|Cloud Code Assist" | tail -2)
        problem "$agent: auth-related log entries in last 5 min ($gem_auth_errors hits)"
        escalate "$agent: possible auth issue — sample: $gem_sample"
      else
        ok "$agent: no auth errors in recent logs"
      fi

      # Live test — only with --deep
      if $DEEP; then
        log "  🔍 Deep: running Gemini live auth test..."
        gem_live=$(run_remote "$agent" 'echo "hi" | timeout 10 gemini -p "say ok" 2>&1' || true)
        if echo "$gem_live" | grep -qiE "authentication|sign in|login|auth|error|failed|denied"; then
          problem "$agent: Gemini CLI live test failed"
          escalate "$agent: Gemini CLI auth broken — output: $(echo "$gem_live" | head -2)"
        else
          ok "$agent: Gemini CLI live test passed"
        fi
      fi
      ;;

    codex)
      # Log-based auth scan
      codex_auth_errors=$(run_remote "$agent" "journalctl --user -u ${SERVICES[$agent]}.service --since '5 min ago' --no-pager 2>/dev/null" \
        | grep -ciE "insufficient_quota|invalid_api_key|authentication|error|401|403|404|auth|quota" || true)
      if (( codex_auth_errors > 0 )); then
        codex_sample=$(run_remote "$agent" "journalctl --user -u ${SERVICES[$agent]}.service --since '5 min ago' --no-pager 2>/dev/null" \
          | grep -iE "insufficient_quota|invalid_api_key|authentication|error|401|403|404|auth|quota" | tail -2)
        problem "$agent: auth-related log entries in last 5 min ($codex_auth_errors hits)"
        escalate "$agent: possible OpenAI auth/quota issue — sample: $codex_sample"
      else
        ok "$agent: no auth errors in recent logs"
      fi
      ;;

    kimi)
      # Log-based auth scan
      kimi_auth_errors=$(run_remote "$agent" "journalctl --user -u ${SERVICES[$agent]}.service --since '5 min ago' --no-pager 2>/dev/null" \
        | grep -ciE "error|401|403|404|auth|quota|unauthorized|invalid.*key" || true)
      if (( kimi_auth_errors > 0 )); then
        kimi_sample=$(run_remote "$agent" "journalctl --user -u ${SERVICES[$agent]}.service --since '5 min ago' --no-pager 2>/dev/null" \
          | grep -iE "error|401|403|404|auth|quota|unauthorized|invalid.*key" | tail -2)
        problem "$agent: auth-related log entries in last 5 min ($kimi_auth_errors hits)"
        escalate "$agent: possible Kimi/Moonshot auth issue — sample: $kimi_sample"
      else
        ok "$agent: no auth errors in recent logs"
      fi
      ;;

    scotty)
      # Local — scan Anthropic-related auth errors
      scotty_auth_errors=$(journalctl --user -u "${SERVICES[$agent]}.service" --since '5 min ago' --no-pager 2>/dev/null \
        | grep -ciE "error|401|403|invalid.*key|authentication|quota" || true)
      if (( scotty_auth_errors > 0 )); then
        scotty_sample=$(journalctl --user -u "${SERVICES[$agent]}.service" --since '5 min ago' --no-pager 2>/dev/null \
          | grep -iE "error|401|403|invalid.*key|authentication|quota" | tail -2)
        problem "$agent: auth-related log entries in last 5 min ($scotty_auth_errors hits)"
        escalate "$agent: possible Anthropic auth issue — sample: $scotty_sample"
      else
        ok "$agent: no auth errors in recent logs"
      fi
      ;;
  esac

  # 5. Check gateway responds to WebSocket health
  if [[ "$host" == "local" ]]; then
    ws_target="127.0.0.1"
  else
    ws_target="$host"
  fi
  
  # Quick TCP check on gateway port
  if timeout 3 bash -c "echo >/dev/tcp/$ws_target/$port" 2>/dev/null; then
    ok "$agent: gateway port $port open"
  else
    problem "$agent: gateway port $port not responding"
    if $FIX; then
      run_remote "$agent" "systemctl --user restart $service.service 2>/dev/null" && \
        fixed "$agent: restarted $service.service" || \
        escalate "$agent: restart failed"
    fi
  fi

  # 6. Check for recent errors in logs (last 5 min)
  recent_errors=$(run_remote "$agent" "journalctl --user -u $service.service --since '5 min ago' --no-pager 2>/dev/null" | grep -ci "rate.limit\|insufficient.quota\|signature.invalid\|auth.*reject\|ECONNREFUSED" || true)
  if (( recent_errors > 0 )); then
    # Determine error type
    error_sample=$(run_remote "$agent" "journalctl --user -u $service.service --since '5 min ago' --no-pager 2>/dev/null" | grep -i "rate.limit\|insufficient.quota\|signature.invalid\|auth.*reject" | tail -1)
    
    if [[ "$error_sample" =~ insufficient_quota|rate.limit ]]; then
      problem "$agent: API quota/rate limit issue"
      fallback="${FALLBACKS[$agent]:-}"
      if [[ -n "$fallback" ]] && [[ "$current_model" != "$fallback" ]] && $FIX; then
        escalate "$agent: needs re-auth or billing top-up. Switching to fallback $fallback"
      else
        escalate "$agent: needs re-auth or billing top-up"
      fi
    elif [[ "$error_sample" =~ signature.invalid ]]; then
      problem "$agent: device signature invalid"
      escalate "$agent: needs device re-pairing on gateway"
    fi
  else
    ok "$agent: no recent errors"
  fi
done

# --- Summary ---
log ""
log "========================================"
echo "Fleet Check Complete: ${#PROBLEMS[@]} problems, ${#FIXES[@]} auto-fixed, ${#ESCALATIONS[@]} need David"

if (( ${#ESCALATIONS[@]} > 0 )); then
  echo ""
  echo "📋 ACTION NEEDED:"
  for e in "${ESCALATIONS[@]}"; do
    echo "  → $e"
  done
fi

# Exit code: 0 = all healthy, 1 = problems found
(( ${#PROBLEMS[@]} == 0 )) && exit 0 || exit 1
