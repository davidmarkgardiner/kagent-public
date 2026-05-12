---
name: yaml-to-kro
description: Convert standard Kubernetes YAML manifests into KRO (Kubernetes Resource Orchestrator) ResourceGraphDefinition files and matching instance CRs. Use when the user has existing K8s manifests (Deployments, Services, ConfigMaps, RBAC, etc.) and wants to package them as a single KRO-managed custom resource with a parameterized schema.
---

# YAML-to-KRO Converter

Convert raw Kubernetes YAML into KRO ResourceGraphDefinitions (RGDs) and instances. This skill turns a collection of standard manifests into a single custom resource that KRO reconciles, with a clean schema, CEL-based templating, and sensible defaults.

## When to Use

- Packaging multiple K8s manifests into a single deployable unit
- Creating reusable infrastructure templates from existing YAML
- Building platform abstractions (namespace-as-a-service, app stacks, monitoring stacks)
- Migrating Helm charts or kustomize overlays to KRO
- Composing ASO (Azure Service Operator) resources with standard K8s resources

## How KRO ResourceGraphDefinitions Work

A ResourceGraphDefinition has two main sections:

1. **`spec.schema`** -- Defines a new custom resource kind with typed, validated fields
2. **`spec.resources`** -- Lists the Kubernetes resources KRO will create, with CEL expressions referencing the schema

When you apply the RGD, KRO registers a new CRD (e.g., `KroWorkerAlloy`). You then create instances of that CRD, and KRO reconciles all the child resources.

```
RGD (definition)          Instance (CR)              Reconciled Resources
--------------------      -------------------        ----------------------
schema:                   kind: KroWorkerAlloy       Namespace
  kind: KroWorkerAlloy    spec:                      ServiceAccount
  spec:                     cluster:                  ClusterRole
    cluster:                  name: prod-01           ClusterRoleBinding
      name: string            ...                     ConfigMap
      ...                                             Deployment
resources:                                            Service
  - id: namespace
  - id: serviceAccount
  - id: deployment
  ...
```

## Step-by-Step Conversion Process

### Step 1: Inventory the Source YAML

List every resource in the source manifests. For each one, note:
- apiVersion/kind
- Which values are environment-specific (names, namespaces, replica counts, images, connection strings)
- Which values are always the same (labels selectors, port names, RBAC verbs)

### Step 2: Design the Schema

Extract environment-specific values into schema fields. Follow these rules:

**What to parameterize:**
- Names that change per deployment (cluster name, app name)
- Namespaces
- Image tags/versions
- Replica counts
- Resource requests/limits
- External endpoints (URLs, FQDNs, connection strings)
- Feature toggles (enabled/disabled booleans)
- Credentials secret names (never the credentials themselves)

**What to hardcode:**
- Label selectors that must match between Deployment and Service
- RBAC verb lists (get, list, watch)
- Volume mount paths
- Health check paths
- Port names (keep as literal strings)
- Security context settings (runAsNonRoot, drop ALL capabilities)

**Schema field type syntax:**

> **YAML quoting gotcha (KRO v0.8.5+):** When a schema marker value contains an embedded double-quoted string (e.g. `description="..."` or `pattern="..."`), wrap the ENTIRE right-hand side in single quotes. YAML parses bare plain scalars loosely around `"`, `{`, `}`, `(`, `)`, `+`, and multi-marker lines frequently get mangled before KRO's `simpleschema` parser ever sees them — the symptom is `failed to parse <fieldName>`. Rule of thumb: if the value has any `"..."` inside it, single-quote the whole line. Bare single-marker lines (e.g. `integer | default=2`) are fine unquoted.
>
> ```yaml
> # BAD — bare plain scalar with embedded double quotes, may fail
> agentPrefix: string | required=true pattern="^[A-Z]+$" description="Agent prefix"
>
> # GOOD — single-quoted, passes through to simpleschema verbatim
> agentPrefix: 'string | required=true pattern="^[A-Z]+$" description="Agent prefix"'
> ```

```yaml
spec:
  schema:
    apiVersion: v1alpha1
    kind: MyAppStack
    spec:
      # String -- required
      appName: 'string | required=true description="Application name"'

      # String -- with default and validation
      namespace: 'string | default="my-app" description="Target namespace"'
      location: 'string | default="uksouth" enum="uksouth,ukwest,westeurope" description="Azure region"'
      subscriptionId: 'string | required=true pattern="^[0-9a-f]{8}-..." description="Azure subscription"'

      # Integer -- with bounds (no embedded quotes, bare is fine)
      replicas: 'integer | default=2 minimum=1 maximum=20 description="Pod replicas"'

      # Boolean
      enableMonitoring: 'boolean | default=true description="Deploy ServiceMonitor"'

      # Array of strings
      availabilityZones: '[]string | default=["1","2"] description="AZ distribution"'

      # Map
      tags: 'map[string]string | required=true description="Resource tags"'

      # Nested object -- group related fields
      resources:
        cpuRequest: 'string | default="100m"'
        cpuLimit: 'string | default="500m"'
        memoryRequest: 'string | default="128Mi"'
        memoryLimit: 'string | default="512Mi"'

      # Nested object -- external service config
      eventHub:
        fqdn: 'string | required=true description="Event Hub FQDN with port"'
        topic: 'string | default="events" description="Topic name"'
        credentialsSecretName: 'string | default="eventhub-creds" description="Pre-created secret name"'
```

### Step 3: Convert Each Resource into a KRO Resource Block

Each source manifest becomes a resource entry under `spec.resources`. The structure is:

```yaml
resources:
  - id: descriptiveResourceId
    template:
      apiVersion: v1
      kind: Service
      metadata:
        name: ${schema.spec.appName}
        namespace: ${schema.spec.namespace}
        labels:
          app: ${schema.spec.appName}
          app.kubernetes.io/instance: ${schema.metadata.name}
      spec:
        selector:
          app: ${schema.spec.appName}
        ports:
          - port: 8080        # hardcoded -- internal contract
            targetPort: http   # hardcoded -- matches container port name
```

**Key rules:**
- Every resource MUST have an `id` (camelCase, descriptive)
- Use `${schema.spec.fieldName}` to reference schema values
- Use `${schema.metadata.name}` for the instance name
- Use `${schema.metadata.namespace}` for the instance namespace
- Nested fields: `${schema.spec.resources.cpuRequest}`
- **Reserved `id` keywords — DO NOT name a resource `id: namespace`.** KRO rejects it with `naming convention violation: id namespace is a reserved keyword in KRO` (error message literally contains the phrase "namespace is reserved", which is easily misread as "the label prefix `kro.run/` is reserved" or "the Kubernetes namespace `kro` is reserved" — it's neither). Reserved ids are words KRO uses internally as CEL bindings. Safe alternatives: `agentNamespace`, `appNamespace`, `targetNs`. Err on the side of descriptive compound names rather than bare nouns — `deployment`, `service`, `pod` have all been reported as problematic in various KRO releases.
- **Never use `kro.run/` as a label prefix inside `spec.resources[].template.metadata.labels`.** KRO v0.8.5+ rejects this with `invalid label for resource "<id>". labels with prefix "kro.run/" are reserved for internal use` (see `pkg/graph/validation.go:validateNoKROOwnedLabels`). KRO sets its own `kro.run/*` labels during reconciliation. For traceability, use `app.kubernetes.io/instance`, `app.kubernetes.io/part-of`, etc. The restriction applies ONLY to resource templates — the RGD's own top-level `metadata.labels` / `metadata.annotations` may still use `kro.run/` (e.g. `kro.run/type`), and annotations are never checked.
- **CEL does not auto-coerce between `int` and `string`.** If a schema field is `integer` and you interpolate it into a string slot (e.g. inside a shell-script block scalar, or an env var value), KRO's validation fails with `type mismatch ... expression "schema.spec.X" returns type "int" but expected "string"`. Wrapping with `${string(schema.spec.X)}` works in theory but KRO's expression extractor sometimes strips the cast; the reliable fix is to declare the schema field as `string` (with a quoted default) and, where Kubernetes demands an actual integer (e.g. NetworkPolicy egress `port`, containerPort), cast back with `${int(schema.spec.X)}`. Inverse: never declare a port field as `string` then pass a numeric string to NetworkPolicy — NetworkPolicy's `port` is `IntOrString` but only accepts an integer OR an IANA port name like `http`; `"7878"` is rejected with `must contain at least one letter (a-z)`.

### Step 4: CEL Expression Syntax

KRO uses CEL (Common Expression Language) for value substitution. The syntax in resource templates is:

```yaml
# Simple field reference
name: ${schema.spec.appName}

# String concatenation (done implicitly in KRO)
name: ${schema.spec.appName}-service
name: uami-${schema.spec.clusterName}-externalsecrets

# Nested field reference
value: ${schema.spec.eventHub.fqdn}

# Array/map passthrough
tags: ${schema.spec.tags}
availabilityZones: ${schema.spec.nodePool.availabilityZones}

# Boolean passthrough
enabled: ${schema.spec.enableMonitoring}

# Integer passthrough
replicas: ${schema.spec.replicas}

# Cross-resource references (reference another resource's output)
# Use the resource `id` to access its status fields
issuerUrl: ${cluster.status.oidcIssuerProfile.issuerURL}

# Metadata references
name: cert-${schema.spec.clusterName}
namespace: ${schema.spec.targetNamespace}
```

**Important:** KRO's `${}` expressions are NOT Go templates. They are CEL expressions evaluated by the KRO controller. Do not use `{{ }}` Helm/Go template syntax.

### Step 5: Add Labels and Annotations

Every resource should carry these labels for traceability. **Do NOT use `kro.run/` as a label prefix on resource templates** — it is reserved by KRO v0.8.5+ and will cause the RGD to be rejected. Use the `app.kubernetes.io/*` recommended labels instead:

```yaml
metadata:
  labels:
    app.kubernetes.io/part-of: my-stack-name        # identifies the stack
    app.kubernetes.io/instance: ${schema.metadata.name}    # traces back to instance CR
    app.kubernetes.io/managed-by: kro
```

For stacks in this repo, also add (use a vendor-neutral prefix, not `kro.run/`):

```yaml
metadata:
  labels:
    cluster: ${schema.spec.clusterName}                 # if cluster-scoped
    app.kubernetes.io/component: descriptive-component  # what this resource does
    environment: ${schema.spec.environment}              # if env is parameterized
```

KRO itself will add `kro.run/owned`, `kro.run/instance-name`, etc. to reconciled resources automatically — don't try to set those yourself.

### Step 6: Set RGD Metadata

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: uk8smyapp.kro.run                    # Convention: uk8s<name>.kro.run
  labels:
    kro.run/type: infrastructure              # or: application, post-deployment, event-collector
    kro.run/category: ai-proxy                # descriptive category
  annotations:
    kro.run/description: "One-line description of what this RGD creates"
    kro.run/version: "1.0.0"
```

### Step 7: Create an Instance

The instance is a CR of the kind defined in the schema:

```yaml
apiVersion: kro.run/v1alpha1      # Always kro.run/v1alpha1 for instances
kind: MyAppStack                   # Matches schema.kind
metadata:
  name: my-app-production
  namespace: default               # Namespace where KRO watches
spec:
  appName: my-app
  namespace: my-app-prod
  replicas: 3
  resources:
    cpuRequest: "200m"
    memoryLimit: "1Gi"
  eventHub:
    fqdn: "evh-prod.servicebus.windows.net:9093"
  tags:
    environment: production
    team: platform
```

Only specify fields that differ from defaults. KRO fills in defaults from the schema.

**Instance file gotchas:**
- `apiVersion` MUST include the group: `kro.run/v1alpha1`, NOT just `v1alpha1`. Omitting the group gives `no matches for kind "<Kind>" in version "v1alpha1"`.
- Value types in the instance spec must exactly match the schema types. If the schema declares `omsPort: 'string | default="7878"'`, the instance must write `omsPort: "7878"` (quoted), not `omsPort: 7878` — kubectl will reject with `spec.omsPort: Invalid value: "integer": spec.omsPort in body must be of type string: "integer"`.
- The instance CR itself needs an already-existing `metadata.namespace` to live in. If the RGD creates the target namespace as a child resource, either (a) apply the instance to a different pre-existing namespace like `default`, or (b) pre-create the target namespace manually before first apply.

## Complete Conversion Example

### Source: Raw Kubernetes YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: my-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app
      containers:
        - name: app
          image: myregistry/my-app:v1.2.3
          ports:
            - containerPort: 8080
              name: http
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
spec:
  selector:
    app: my-app
  ports:
    - port: 8080
      targetPort: http
```

### Converted: ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: uk8smyapp.kro.run
  labels:
    kro.run/type: application
    kro.run/category: web-app
  annotations:
    kro.run/description: "Deploys my-app with Namespace, SA, Deployment, and Service"
    kro.run/version: "1.0.0"
spec:
  schema:
    apiVersion: v1alpha1
    kind: UK8sMyApp
    spec:
      appName: 'string | required=true description="Application name"'
      namespace: 'string | default="my-app" description="Target namespace"'
      image: 'string | required=true description="Container image with tag"'
      replicas: integer | default=2 minimum=1 maximum=20
      resources:
        cpuRequest: 'string | default="100m"'
        cpuLimit: 'string | default="500m"'
        memoryRequest: 'string | default="128Mi"'
        memoryLimit: 'string | default="512Mi"'

  resources:
    - id: appNamespace
      template:
        apiVersion: v1
        kind: Namespace
        metadata:
          name: ${schema.spec.namespace}
          labels:
            app.kubernetes.io/part-of: my-app
            app.kubernetes.io/instance: ${schema.metadata.name}

    - id: serviceAccount
      template:
        apiVersion: v1
        kind: ServiceAccount
        metadata:
          name: ${schema.spec.appName}
          namespace: ${schema.spec.namespace}
          labels:
            app: ${schema.spec.appName}
            app.kubernetes.io/instance: ${schema.metadata.name}

    - id: deployment
      template:
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: ${schema.spec.appName}
          namespace: ${schema.spec.namespace}
          labels:
            app: ${schema.spec.appName}
            app.kubernetes.io/instance: ${schema.metadata.name}
        spec:
          replicas: ${schema.spec.replicas}
          selector:
            matchLabels:
              app: ${schema.spec.appName}
          template:
            metadata:
              labels:
                app: ${schema.spec.appName}
            spec:
              serviceAccountName: ${schema.spec.appName}
              containers:
                - name: app
                  image: ${schema.spec.image}
                  ports:
                    - containerPort: 8080
                      name: http
                  resources:
                    requests:
                      cpu: ${schema.spec.resources.cpuRequest}
                      memory: ${schema.spec.resources.memoryRequest}
                    limits:
                      cpu: ${schema.spec.resources.cpuLimit}
                      memory: ${schema.spec.resources.memoryLimit}

    - id: service
      template:
        apiVersion: v1
        kind: Service
        metadata:
          name: ${schema.spec.appName}
          namespace: ${schema.spec.namespace}
          labels:
            app: ${schema.spec.appName}
            app.kubernetes.io/instance: ${schema.metadata.name}
        spec:
          selector:
            app: ${schema.spec.appName}
          ports:
            - port: 8080
              targetPort: http
```

### Converted: Instance

```yaml
apiVersion: kro.run/v1alpha1
kind: UK8sMyApp
metadata:
  name: my-app-prod
  namespace: default
spec:
  appName: my-app
  namespace: my-app
  image: myregistry/my-app:v1.2.3
  replicas: 3
  resources:
    cpuLimit: "1000m"
    memoryLimit: "1Gi"
```

## Naming Conventions (This Repo)

| Item | Convention | Example |
|------|-----------|---------|
| RGD metadata.name | `uk8s<name>.kro.run` | `uk8slitellm.kro.run` |
| RGD file name | `uk8s-<name>.yaml` | `uk8s-litellm.yaml` |
| Schema kind | `UK8s<Name>` or `Kro<Name>` | `UK8sagentgateway`, `KroAIStack` |
| Resource id | camelCase, descriptive | `serviceAccount`, `externalSecretsIdentity` |
| Generated resource names | `${schema.spec.clusterName}-<suffix>` | `uami-${schema.spec.clusterName}-externalsecrets` |
| Instance file name | `instance.yaml` or `<env>-instance.yaml` | `instance.yaml` |
| RGD top-level labels | `kro.run/type`, `kro.run/category` (RGD metadata only) | `kro.run/type: infrastructure` |
| Resource template labels | `app.kubernetes.io/instance: ${schema.metadata.name}` | never use `kro.run/` prefix here — reserved by KRO v0.8.5+ |

## Nested / Composable RGDs

For complex stacks, break into smaller RGDs and compose them. The parent RGD creates instances of child RGDs as resources:

```yaml
# Parent RGD references child RGDs as resources
resources:
  - id: jobs
    template:
      apiVersion: kro.run/v1alpha1
      kind: UK8Sjobs                          # Child RGD's schema kind
      metadata:
        name: jobs-${schema.spec.clusterName}
        namespace: ${schema.spec.targetNamespace}
      spec:
        clusterName: ${schema.spec.clusterName}
        resourceGroup: ${schema.spec.resourceGroup}
        # Pass only what the child needs

  - id: fluxGitOps
    template:
      apiVersion: kro.run/v1alpha1
      kind: UK8SFluxGitOps                    # Another child RGD
      metadata:
        name: flux-${schema.spec.clusterName}
        namespace: ${schema.spec.targetNamespace}
      spec:
        clusterName: ${schema.spec.clusterName}
```

This pattern keeps each RGD focused and reusable. The `uk8scluster-public` RGD in this repo composes `UK8Sjobs`, `UK8SFluxGitOps`, and `UK8SCertification` as child resources.

## Conditional Resources

Use `includeWhen` to make resources optional based on schema flags:

```yaml
resources:
  - id: monitoring
    includeWhen:
      - ${schema.spec.enableMonitoring}
    template:
      apiVersion: monitoring.coreos.com/v1
      kind: ServiceMonitor
      # ...
```

## Common Pitfalls

1. **Forgetting `id` on resources** -- Every resource block needs a unique `id`
2. **Using `{{ }}` instead of `${}`** -- KRO uses `${}` CEL expressions, not Go templates
3. **Hardcoding names that should be parameterized** -- If two instances could collide, parameterize the name
4. **Not single-quoting schema lines with embedded `"..."`** -- Any marker value with embedded double quotes (`description="..."`, `pattern="..."`, `default="..."`) means the ENTIRE right-hand side must be single-quoted: `'string | required=true description="..."'`. Same rule applies to array/map types: `'[]string | ...'` and `'map[string]string | ...'`. Skipping the outer single quotes is the #1 cause of `failed to parse <fieldName>` errors from KRO's simpleschema.
5. **Missing label selectors consistency** -- If Deployment selector uses `app: ${schema.spec.appName}`, Service selector must too
6. **Putting secrets in the schema** -- Never put credential values in the schema. Reference pre-created Secret names instead
7. **Forgetting owner references for ASO** -- ASO resources need `spec.owner.name` pointing to the parent ResourceGroup
8. **Using `kro.run/` label prefix on resource templates** -- KRO v0.8.5+ rejects any resource template whose `metadata.labels` has a key starting with `kro.run/`. Error: `invalid label for resource "<id>". labels with prefix "kro.run/" are reserved for internal use`. Use `app.kubernetes.io/instance` instead. This does NOT affect the RGD's own top-level labels or any annotations.
9. **Using `id: namespace` (or other reserved words) as a resource id** -- KRO reserves certain words as CEL bindings. `namespace` is confirmed reserved; error is `naming convention violation: id namespace is a reserved keyword in KRO`. Use `agentNamespace`, `appNamespace`, `targetNs`, etc.
10. **Mixing int and string schema types across fields that must interop** -- CEL won't auto-coerce. If a field must appear in both a shell-script block scalar (needs string) and a NetworkPolicy port (needs int), declare it as `string` in the schema and cast with `${int(schema.spec.X)}` where Kubernetes demands an integer. Don't try to go the other way — numeric strings like `"7878"` are rejected by NetworkPolicy's port validator.

## Checklist Before Submitting

- [ ] Every environment-specific value is parameterized
- [ ] Required fields are marked `required=true`
- [ ] All optional fields have sensible defaults
- [ ] Every schema field has a `description`
- [ ] Resource `id` values are camelCase and descriptive
- [ ] Resource template labels use `app.kubernetes.io/instance: ${schema.metadata.name}` (NOT `kro.run/instance` — reserved prefix)
- [ ] No resource template under `spec.resources[]` has any `metadata.labels` key starting with `kro.run/`
- [ ] RGD metadata.name follows `uk8s<name>.kro.run` convention
- [ ] Instance YAML only specifies non-default values
- [ ] No secrets or credentials appear in schema or resource templates
- [ ] YAML validates with `kubectl apply --dry-run=client`

## Reference Files in This Repo

- **Definitions:** `infra-stack/kro-stack/definitions/` -- All production RGDs
- **Simple example:** `uk8s-litellm.yaml` -- agentgateway (Namespace + SA + FedCred + ConfigMap + Deployment + Service + PDB + HPA)
- **Complex example:** `uk8scluster-public.yaml` -- Full AKS cluster with nested RGDs and ASO resources
- **Event collector:** `uk8s-kro-worker-alloy.yaml` -- Alloy deployment with HCL config templating
- **AI stack:** `uk8s-kro-ai-stack.yaml` -- Argo Events + Sensor + WorkflowTemplate composition
- **Instances:** `kro/instance.yaml`, `application-stack/apps/kagent/instance.yaml`
- **KRO patterns reference:** `.claude/skills/k8s-specialist/kro-stack-builder/references/kro_patterns.md`
