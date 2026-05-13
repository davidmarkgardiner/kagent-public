# Application Onboarding — Interview Reference

Maps the 9 interview questions to generated GitOps YAML artifacts.

---

## Parameter Map

| Question | Field | Notes |
|----------|-------|-------|
| App name? | `appName` | Becomes Deployment/Service name; lowercase, hyphens |
| Team? | `team` | Label value and request.yaml `metadata.team` |
| Namespace? | `namespace` | Must already exist; suggest namespace-onboarding-agent if not |
| Container image + tag? | `image` | Full registry path, e.g. `myregistry.azurecr.io/myapp:1.2.3` |
| Port? | `port` | Default: `8080` |
| Protocol? | `protocol` | `HTTP`, `gRPC`, or `TCP` — informs Istio VirtualService |
| Istio ingress? | `istioIngress` | yes/no; if yes → collect `host` and `pathPrefix` |
| AuthorizationPolicy? | `authPolicy` | yes/no; if yes → collect allowed namespaces/service accounts |
| Resource requirements? | `resources` | CPU req/limit + memory req/limit |

Bonus questions (after Round 3):
- `hpa` — yes/no; defaults min 2 / max 10 / 70% CPU target
- `triageAgent` — yes/no; generates `request.yaml` for BYO-KAgent submission

---

## Generated Artifacts

### Always generated

**`deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: <appName>
  namespace: <namespace>
  labels:
    app: <appName>
    platform.com/team: <team>
spec:
  replicas: 2
  selector:
    matchLabels:
      app: <appName>
  template:
    metadata:
      labels:
        app: <appName>
        platform.com/team: <team>
    spec:
      containers:
        - name: <appName>
          image: <image>
          ports:
            - containerPort: <port>
          resources:
            requests:
              cpu: <cpuRequest>
              memory: <memRequest>
            limits:
              cpu: <cpuLimit>
              memory: <memLimit>
```

**`service.yaml`** — ClusterIP exposing `<port>`.

---

### Optional: Istio VirtualService (`virtualservice.yaml`)

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: <appName>
  namespace: <namespace>
spec:
  hosts:
    - <host>
  gateways:
    - istio-system/platform-gateway
  http:
    - match:
        - uri:
            prefix: <pathPrefix>
      route:
        - destination:
            host: <appName>
            port:
              number: <port>
```

Use `{{INGRESS_DOMAIN}}` as the domain placeholder if no specific domain is provided.

---

### Optional: Istio AuthorizationPolicy (`authorizationpolicy.yaml`)

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-<appName>
  namespace: <namespace>
spec:
  selector:
    matchLabels:
      app: <appName>
  action: ALLOW
  rules:
    - from:
        - source:
            namespaces: [<allowedNamespace1>, <allowedNamespace2>]
```

---

### Optional: HPA (`hpa.yaml`)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: <appName>
  namespace: <namespace>
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: <appName>
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

### Optional: BYO-KAgent request.yaml

```yaml
# request.yaml
# Submit as a PR labelled 'byo-kagent' to trigger the platform review workflow.
metadata:
  agentName: <appName>-triage-agent
  team: <team>
  costCenter: "{{COST_CENTER}}"
target:
  clusters:
    - "{{CLUSTER_NAME}}"
model:
  ref: shared/default-model-config
tools:
  - catalogRef: "k8s-read-only@v1"
    scopes:
      - namespace:<namespace>
budget:
  cpu: 100m
  memory: 256Mi
```

Tool references must use verified `ToolCatalogEntry` values. New MCP tools must pass through
`mcp-onboarding-template` quarantine before they appear in the catalog.

---

## GitOps Apply Sequence

```bash
# 1. Validate locally
kubectl apply --dry-run=client -f deployment.yaml -f service.yaml

# 2. Commit to GitOps repo
git add deployment.yaml service.yaml
git commit -m "feat(<namespace>): onboard <appName>"
git push origin feat/onboard-<appName>
# Open PR — Flux reconciles after merge

# 3. If BYO-KAgent requested
# Submit request.yaml as a PR labelled 'byo-kagent'
```

---

## Source Files

| File | Location |
|------|----------|
| Agent CRD | `agents/kagent-triage/app-onboarding-agent.yaml` |
| Istio reference | `platform/teams-hitl/` (VirtualService + AuthorizationPolicy patterns) |
| BYO-KAgent workflow | `platform/argo-workflows/templates/byo-kagent/` |
| MCP onboarding | `platform/argo-workflows/templates/mcp-onboarding/` |
