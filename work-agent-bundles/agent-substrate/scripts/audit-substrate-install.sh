#!/usr/bin/env bash
# Read-only snapshot of the Substrate 0.0.9 + kagent 0.10.x installation.
# This checks live API objects. It cannot prove a past checkpoint/restore run.
# Output includes kube context, resource and node names; share it only privately.
set -uo pipefail

CONTEXT=""
ATE_NAMESPACE="ate-system"
KAGENT_NAMESPACE="kagent"
SANDBOX_AGENT=""
FAILURES=0
UNKNOWNS=0

usage() {
  cat <<'EOF'
Usage: audit-substrate-install.sh --context KUBE_CONTEXT [options]

Read-only check for the Substrate 0.0.9 / kagent 0.10.x SandboxAgent path.
It never changes a Kubernetes resource or reads Secret values.

Options:
  --context NAME              Required. The exact kube context to inspect.
  --ate-namespace NAME        Default: ate-system.
  --kagent-namespace NAME     Default: kagent.
  --sandboxagent NAME         Also check this agent and its generated template.
  -h, --help                  Show this help.

Exit: 0 = installation checks passed; 1 = missing/unhealthy required object;
      2 = unable to determine because of access/API error or bad invocation.
Even exit 0 does not prove a request, checkpoint, restore, or air gap.
EOF
}

while (($#)); do
  case "$1" in
    --context|--ate-namespace|--kagent-namespace|--sandboxagent)
      if (($# < 2)) || [[ -z "$2" ]]; then
        echo "ERROR $1 needs a value" >&2
        exit 2
      fi
      case "$1" in
        --context) CONTEXT="$2" ;;
        --ate-namespace) ATE_NAMESPACE="$2" ;;
        --kagent-namespace) KAGENT_NAMESPACE="$2" ;;
        --sandboxagent) SANDBOX_AGENT="$2" ;;
      esac
      shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$CONTEXT" ]]; then
  echo 'ERROR --context is required; this script will not use an implicit context' >&2
  exit 2
fi
command -v kubectl >/dev/null 2>&1 || { echo 'ERROR kubectl is required' >&2; exit 2; }

k() { kubectl --context "$CONTEXT" --request-timeout=10s "$@"; }
pass() { printf 'PASS    %s\n' "$*"; }
fail() { printf 'FAIL    %s\n' "$*"; FAILURES=$((FAILURES + 1)); }
unknown() { printf 'UNKNOWN %s\n' "$*"; UNKNOWNS=$((UNKNOWNS + 1)); }

# Do not confuse a forbidden read or transport error with a missing object.
check_object() {
  local label="$1"; shift
  local output
  if output="$(k get "$@" -o name 2>&1)"; then
    if [[ -n "$output" ]]; then
      pass "$label ($output)"
    else
      fail "$label (empty response)"
    fi
  elif [[ "$output" == *NotFound* || "$output" == *'not found'* ]]; then
    fail "$label (not found)"
  else
    unknown "$label (API or permission error; run kubectl get locally for detail)"
  fi
}

printf 'TARGET_CONTEXT=%s\n' "$CONTEXT"
printf 'PROFILE=Substrate 0.0.9 + kagent 0.10.x SandboxAgent\n'

if ! kubectl config get-contexts -o name 2>/dev/null | grep -Fxq -- "$CONTEXT"; then
  echo 'RESULT=UNKNOWN: kube context is not present in this kubeconfig' >&2
  exit 2
fi
if ! k get --raw=/version >/dev/null 2>&1; then
  echo 'RESULT=UNKNOWN: target API is unreachable or access was denied' >&2
  exit 2
fi
pass 'target Kubernetes API reachable'

echo '== CRDs (ate.dev is an API group, not one CRD) =='
for crd in workerpools.ate.dev actortemplates.ate.dev sandboxconfigs.ate.dev; do
  check_object "required CRD $crd" crd "$crd"
done
check_object 'required CRD sandboxagents.kagent.dev' crd sandboxagents.kagent.dev

if api_resources="$(k api-resources --api-group=ate.dev -o name 2>/dev/null)"; then
  if [[ -n "$api_resources" ]]; then
    printf 'ATE_API_RESOURCES:\n%s\n' "$api_resources"
  else
    fail 'ate.dev API discovery returned no resources'
  fi
else
  unknown 'cannot discover ate.dev API resources'
fi

echo '== Control and worker resources =='
check_object "namespace $ATE_NAMESPACE" namespace "$ATE_NAMESPACE"
check_object "namespace $KAGENT_NAMESPACE" namespace "$KAGENT_NAMESPACE"

if pods="$(k -n "$ATE_NAMESPACE" get pods \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.spec.nodeName}{"\n"}{end}' 2>/dev/null)"; then
  if [[ -n "$pods" ]]; then
    printf 'ATE_PODS (name, phase, node):\n%s\n' "$pods"
    if [[ "$pods" == *$'\tRunning\t'* ]]; then
      pass "at least one running pod in $ATE_NAMESPACE"
    else
      fail "no Running pods in $ATE_NAMESPACE"
    fi
  else
    fail "no pods in $ATE_NAMESPACE"
  fi
else
  unknown "cannot list pods in $ATE_NAMESPACE"
fi

if deployments="$(k -n "$ATE_NAMESPACE" get deployments -o name 2>/dev/null)"; then
  printf 'ATE_DEPLOYMENTS:\n%s\n' "${deployments:-<none>}"
  for component in ate-api-server-deployment ate-controller atenet-router; do
    deployment="$(printf '%s\n' "$deployments" | grep -E "(^|[-/])${component}$" | head -1)"
    if [[ -n "$deployment" ]]; then
      if k -n "$ATE_NAMESPACE" rollout status "$deployment" --timeout=2s >/dev/null 2>&1; then
        pass "$component Deployment rolled out"
      else
        fail "$component Deployment exists but is not rolled out"
      fi
    else
      fail "$component Deployment missing from $ATE_NAMESPACE"
    fi
  done
else
  unknown "cannot list Deployments in $ATE_NAMESPACE"
fi

if daemonsets="$(k -n "$ATE_NAMESPACE" get daemonsets -o name 2>/dev/null)"; then
  if [[ "$daemonsets" == *atelet* ]]; then
    atelet="$(printf '%s\n' "$daemonsets" | grep -E '(^|[-/])atelet$' | head -1)"
    if [[ -n "$atelet" ]] && k -n "$ATE_NAMESPACE" rollout status "$atelet" --timeout=2s >/dev/null 2>&1; then
      pass "atelet DaemonSet rolled out ($atelet)"
    else
      fail "atelet DaemonSet is present but not rolled out"
    fi
  else
    fail "atelet DaemonSet missing from $ATE_NAMESPACE"
  fi
else
  unknown "cannot list DaemonSets in $ATE_NAMESPACE"
fi

if pools="$(k get workerpools.ate.dev -A \
  -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"|"}{.spec.replicas}{"|"}{.status.replicas}{"\n"}{end}' 2>/dev/null)"; then
  if [[ -n "$pools" ]]; then
    printf 'WORKERPOOLS (namespace/name|desired|status replicas):\n%s\n' "$pools"
    while IFS='|' read -r pool desired ready; do
      [[ -z "$pool" ]] && continue
      if [[ "$desired" =~ ^[1-9][0-9]*$ && "$ready" == "$desired" ]]; then
        pass "WorkerPool $pool has $ready/$desired replicas"
      else
        fail "WorkerPool $pool is not ready (desired=${desired:-unset}, status=${ready:-unset})"
      fi
    done <<< "$pools"
  else
    fail 'no WorkerPool exists'
  fi
else
  unknown 'cannot list WorkerPools'
fi

if configs="$(k get sandboxconfigs.ate.dev -o name 2>/dev/null)"; then
  if [[ -n "$configs" ]]; then
    printf 'SANDBOXCONFIGS:\n%s\n' "$configs"
    if [[ "$configs" == *sandboxconfig.ate.dev/gvisor-default* || "$configs" == *sandboxconfig/gvisor-default* ]]; then
      pass 'gvisor-default SandboxConfig exists'
    else
      fail 'gvisor-default SandboxConfig is missing'
    fi
  else
    fail 'no SandboxConfig exists'
  fi
else
  unknown 'cannot list SandboxConfigs'
fi

if kagent_deployments="$(k -n "$KAGENT_NAMESPACE" get deployments -o name 2>/dev/null)"; then
  controller="$(printf '%s\n' "$kagent_deployments" | grep -E '(^|[-/])kagent-controller$' | head -1)"
  if [[ -n "$controller" ]] && k -n "$KAGENT_NAMESPACE" rollout status "$controller" --timeout=2s >/dev/null 2>&1; then
    pass "kagent controller Deployment rolled out ($controller)"
  else
    fail 'kagent controller Deployment missing or not rolled out'
  fi
else
  unknown "cannot list Deployments in $KAGENT_NAMESPACE"
fi

echo '== Canary evidence currently visible =='
if [[ -n "$SANDBOX_AGENT" ]]; then
  check_object "SandboxAgent $KAGENT_NAMESPACE/$SANDBOX_AGENT" \
    -n "$KAGENT_NAMESPACE" sandboxagent "$SANDBOX_AGENT"
  if conditions="$(k -n "$KAGENT_NAMESPACE" get sandboxagent "$SANDBOX_AGENT" \
    -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{" "}{end}' 2>/dev/null)"; then
    printf 'AGENT_CONDITIONS=%s\n' "$conditions"
    if [[ "$conditions" == *Accepted=True* && "$conditions" == *Ready=True* ]]; then
      pass 'SandboxAgent Accepted=True and Ready=True'
    else
      fail 'SandboxAgent is not both Accepted=True and Ready=True'
    fi
  else
    unknown 'cannot read SandboxAgent conditions'
  fi
  if templates="$(k -n "$KAGENT_NAMESPACE" get actortemplates.ate.dev \
    -l "kagent.dev/sandbox-agent=$SANDBOX_AGENT" \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.phase}{"|"}{.status.goldenSnapshot}{"\n"}{end}' 2>/dev/null)"; then
    if [[ -n "$templates" ]]; then
      printf 'GENERATED_TEMPLATES (name|phase|goldenSnapshot):\n%s\n' "$templates"
      while IFS='|' read -r template phase golden; do
        [[ -z "$template" ]] && continue
        if [[ "$phase" == Ready && -n "$golden" ]]; then
          pass "generated ActorTemplate $template has Ready golden snapshot"
        else
          fail "generated ActorTemplate $template is not Ready with a golden snapshot"
        fi
      done <<< "$templates"
    else
      fail 'no generated ActorTemplate for named SandboxAgent'
    fi
  else
    unknown 'cannot list generated ActorTemplates'
  fi
else
  echo 'NOT_CHECKED: pass --sandboxagent NAME to inspect a current canary'
fi

echo '== Verdict =='
if ((FAILURES > 0)); then
  printf 'SUBSTRATE_INSTALL_AUDIT=FAIL missing_or_unhealthy=%d unknown=%d\n' "$FAILURES" "$UNKNOWNS"
  exit 1
fi
if ((UNKNOWNS > 0)); then
  printf 'SUBSTRATE_INSTALL_AUDIT=UNKNOWN unknown=%d\n' "$UNKNOWNS"
  exit 2
fi
echo 'SUBSTRATE_INSTALL_AUDIT=INSTALL_CHECK_PASS'
echo 'LIFECYCLE_PROOF=NOT_CHECKED (requires timestamped actor, snapshot, restore and request receipts)'
