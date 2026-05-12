# App Onboarding Interview

Use this flow for application manifest generation.

## Scope

This pillar returns Kubernetes YAML only. It must not apply manifests, submit a Workflow, or include Azure resources.

## Fields

Collect:

| Field | Rule | Default |
| --- | --- | --- |
| `appName` | lowercase DNS label | none |
| `namespace` | lowercase DNS label | none |
| `image` | container image reference | none |
| `replicas` | integer | `2` |
| `containerPort` | integer | `8080` |
| `servicePort` | integer | same as containerPort |
| `cpuRequest` | Kubernetes quantity | `100m` |
| `memoryRequest` | Kubernetes quantity | `128Mi` |
| `cpuLimit` | Kubernetes quantity | `500m` |
| `memoryLimit` | Kubernetes quantity | `512Mi` |
| `environment` | `dev`, `test`, `stage`, `prod` | `dev` |
| `exposeService` | yes or no | yes |
| `defaultDenyNetworkPolicy` | yes or no | yes |

## Output

Generate valid Kubernetes YAML in this order:

1. Namespace
2. ResourceQuota
3. NetworkPolicy
4. Deployment
5. Service when requested

## Required YAML Properties

Deployment:

- `apiVersion: apps/v1`
- Matching selector and pod labels.
- Resource requests and limits.
- Liveness and readiness HTTP probes on `/healthz`.
- Pod or container security context with `runAsNonRoot: true`.
- Container security context with `allowPrivilegeEscalation: false` and `capabilities.drop: ["ALL"]`.

Labels:

- `app.kubernetes.io/name`
- `app.kubernetes.io/part-of: onboarding-platform`
- `onboarding.platform.com/environment`

NetworkPolicy:

- If default deny is requested, include `policyTypes: ["Ingress", "Egress"]` and no ingress or egress allowances.

## Validation

End with:

```bash
kubectl apply --dry-run=client -f app-onboarding.yaml
```

Do not provide a mutating apply command.
