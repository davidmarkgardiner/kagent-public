#!/usr/bin/env bash
# Mints Entra client-credentials tokens into the tokens.json shape that
# scripts/deploy.sh and scripts/verify.sh already read, so the verifier can run
# against the Entra profile instead of the disposable JWT profile.
#
#   ./entra-tokens.sh --tenant <tenant-id> --api-app-id <api-app-id> \
#     --client event_a2a=<client-app-id>:<secret-file> \
#     --client chat_a2a=<client-app-id>:<secret-file> \
#     --out tokens.json
#
# The key before '=' becomes the tokens.json key (event_a2a, chat_a2a,
# event_mcp, chat_mcp, substrate_a2a, rogue_substrate_a2a, ...).
# Secrets are read from files, never from the command line. The output holds
# bearer tokens: treat it as a secret and keep it out of git.
set -uo pipefail
tenant=""; api=""; out="tokens.json"; declare -a clients=()
while (( $# )); do
  case $1 in
    --tenant) tenant=$2; shift 2 ;;
    --api-app-id) api=$2; shift 2 ;;
    --client) clients+=("$2"); shift 2 ;;
    --out) out=$2; shift 2 ;;
    -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ -n $tenant && -n $api && ${#clients[@]} -gt 0 ]] || { echo "--tenant, --api-app-id and at least one --client are required" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 2; }

tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
echo '{}' > "$tmp"
for spec in "${clients[@]}"; do
  key=${spec%%=*}; rest=${spec#*=}
  client_id=${rest%%:*}; secret_file=${rest#*:}
  [[ -r $secret_file ]] || { echo "cannot read secret file for $key: $secret_file" >&2; exit 1; }
  body=$(curl -sS --max-time 30 -X POST "https://login.microsoftonline.com/$tenant/oauth2/v2.0/token" \
    -d "client_id=$client_id" -d "scope=api://$api/.default" -d "grant_type=client_credentials" \
    --data-urlencode "client_secret=$(cat "$secret_file")")
  token=$(jq -r '.access_token // empty' <<<"$body")
  if [[ -z $token ]]; then
    echo "$key: no token ($(jq -r '.error // "unknown"' <<<"$body"))" >&2
    continue
  fi
  # Report the claims the gateway policies key on, without printing the token.
  payload=$(cut -d. -f2 <<<"$token" | tr '_-' '/+')
  padded="$payload$(printf '%*s' $(( (4 - ${#payload} % 4) % 4 )) '' | tr ' ' '=')"
  claims=$(base64 --decode <<<"$padded" 2>/dev/null)
  printf '%-22s iss=%s aud=%s roles=%s\n' "$key" \
    "$(jq -r '.iss // "?"' <<<"$claims")" "$(jq -r '.aud // "?"' <<<"$claims")" \
    "$(jq -rc '.roles // "none"' <<<"$claims")"
  jq --arg k "$key" --arg v "$token" '.[$k]=$v' "$tmp" > "$tmp.new" && mv "$tmp.new" "$tmp"
done
install -m 600 "$tmp" "$out"
echo "wrote $out ($(jq 'keys|length' "$out") token(s), mode 600)"
