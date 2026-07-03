# AgentHarness Hermes Next Steps

## Current State

On 2026-06-30, the {{LAB_KUBE_CONTEXT}} lab cluster was upgraded from kagent `v0.8.0-beta4` to kagent `v0.9.10`.

What is now proven:

- `kagent-crds` Helm release is `0.9.10`.
- `kagent` Helm release is `0.9.10`.
- `agentharnesses.kagent.dev` exists at `v1alpha2`.
- `kagent-controller` is running `ghcr.io/kagent-dev/kagent/controller:0.9.10`.
- `kagent-ui` is running `ghcr.io/kagent-dev/kagent/ui:0.9.10`.
- Existing `Agent`, `ModelConfig`, and `ToolServer` resources are still visible.
- Existing agents still report `READY=True` and `ACCEPTED=True`.
- A temporary `AgentHarness/hermes-proof` was accepted by Kubernetes and defaulted to `runtime: openshell`.
- The temporary `AgentHarness/hermes-proof` was deleted after the smoke test.

What is not proven yet:

- No real Hermes harness has reached `Ready`.
- No OpenShell gateway is configured.
- No Substrate API endpoint is configured.
- No Hermes Slack channel has been connected.
- No A2A or ACP composition path has been proven for AgentHarness.

## Main Finding

`AgentHarness` is now available in the lab cluster, but the controller logged:

```text
AgentHarness controller disabled: set --openshell-gateway-url and/or --substrate-ate-api-endpoint
```

So the next blocker is not the CRD or kagent version. The next blocker is choosing and wiring the harness backend:

- OpenShell path for the public `v0.9.10` AgentHarness docs.
- Substrate path for the newer `v0.10.0-beta1` / current-main direction.

## Recommended Next Step

Start with the `v0.9.10` OpenShell path because it matches the currently installed kagent version and the public Agent Harness docs:

- `https://www.kagent.dev/docs/kagent/examples/agent-harness`

Do not switch {{LAB_KUBE_CONTEXT}} to `v0.10.0-beta1` just to test Hermes. The beta API removes `spec.network`, requires `spec.substrate`, and changes the harness shape.

## Tomorrow Checklist

1. Confirm {{LAB_KUBE_CONTEXT}} is still healthy:

```bash
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent get deploy kagent-controller kagent-ui kagent-tools kagent-kmcp-controller-manager kagent-postgresql
kubectl --context {{LAB_KUBE_CONTEXT}} get crd agentharnesses.kagent.dev
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent get agents,modelconfigs,toolservers
```

2. Decide backend path:

```text
Option A: OpenShell on kagent v0.9.10
Option B: Substrate on kagent v0.10.0-beta1/main
```

Use Option A first unless there is a specific reason to move to the beta/Substrate path.

3. Install or locate the OpenShell gateway.

Capture:

```text
OPENSHELL_GATEWAY_URL={{OPENSHELL_GATEWAY_URL}}
OPENSHELL_INSECURE={{true_or_false}}
```

4. Upgrade the kagent Helm release with the OpenShell controller environment.

Example shape:

```bash
helm --kube-context {{LAB_KUBE_CONTEXT}} -n kagent upgrade kagent \
  oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --version 0.9.10 \
  --reuse-values \
  --set controller.env[0].name=OPENSHELL_GATEWAY_URL \
  --set controller.env[0].value='{{OPENSHELL_GATEWAY_URL}}' \
  --set controller.env[1].name=OPENSHELL_INSECURE \
  --set controller.env[1].value='{{true_or_false}}' \
  --atomic \
  --timeout 8m
```

5. Create a no-Slack Hermes harness first.

```yaml
apiVersion: kagent.dev/v1alpha2
kind: AgentHarness
metadata:
  name: hermes-proof
  namespace: kagent
spec:
  backend: hermes
  description: Temporary Hermes AgentHarness proof
  modelConfigRef: default-model-config
  network:
    allowedDomains:
      - api.openai.com
      - slack.com
      - api.slack.com
      - wss-primary.slack.com
      - wss-backup.slack.com
```

6. Verify status:

```bash
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent get agentharnesses
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent describe agentharness hermes-proof
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent logs deploy/kagent-controller --tail=200 | rg -i 'agentharness|hermes|openshell|gateway|error|failed'
```

7. If `hermes-proof` becomes `Ready`, add Slack Secret wiring with placeholders first, then real lab secrets outside this public repo.

Sanitized shape:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: AgentHarness
metadata:
  name: hermes-slack
  namespace: kagent
spec:
  backend: hermes
  modelConfigRef: default-model-config
  channels:
    - name: platform
      type: slack
      slack:
        botToken:
          valueFrom:
            type: Secret
            name: {{HERMES_SLACK_SECRET_NAME}}
            key: bot-token
        appToken:
          valueFrom:
            type: Secret
            name: {{HERMES_SLACK_SECRET_NAME}}
            key: app-token
        hermes:
          allowedUserIDsFrom:
            type: ConfigMap
            name: {{HERMES_ALLOWED_USERS_CONFIGMAP}}
            key: allowed-users
          homeChannel: {{SLACK_HOME_CHANNEL_ID}}
          homeChannelName: {{SLACK_HOME_CHANNEL_NAME}}
```

8. Capture final evidence:

```bash
helm --kube-context {{LAB_KUBE_CONTEXT}} -n kagent list
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent get agentharnesses -o wide
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent describe agentharness hermes-proof
kubectl --context {{LAB_KUBE_CONTEXT}} -n kagent get events --sort-by='.lastTimestamp' | tail -40
```

## Things Needed From Operator

- Confirm whether to use OpenShell first or move straight to Substrate.
- Provide or identify the OpenShell gateway endpoint for the lab.
- Confirm whether Hermes should use Slack for the first proof, or stay API/UI-only first.
- If Slack is in scope, provide the lab Secret names and allowed user/channel IDs out of band. Do not commit the actual token values.

## Rollback Note

The kagent upgrade on {{LAB_KUBE_CONTEXT}} is Helm revision 2. If we need to back out:

```bash
helm --kube-context {{LAB_KUBE_CONTEXT}} -n kagent rollback kagent 1
helm --kube-context {{LAB_KUBE_CONTEXT}} -n kagent rollback kagent-crds 1
```

Use rollback only if the upgraded controller causes a real issue. At handoff time, deployments were healthy and existing agents still reported Ready/Accepted.
