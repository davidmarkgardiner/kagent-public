# Workload Autoscaler Guide (KEDA & VPA)

## Overview

The UK8S AKS cluster now includes **workload autoscaler** capabilities with support for:
- **KEDA** (Kubernetes Event-driven Autoscaling) - Scale based on events
- **VPA** (Vertical Pod Autoscaler) - Automatically adjust CPU and memory requests

Both are configured at the cluster level through Azure Service Operator (ASO).

## Configuration in uk8scluster-public.yaml

### Schema Definition

```yaml
spec:
  schema:
    spec:
      workloadAutoScaler:
        keda:
          enabled: boolean | default=true description="Enable KEDA for event-driven autoscaling"
        verticalPodAutoscaler:
          enabled: boolean | default=true description="Enable Vertical Pod Autoscaler"
```

### ManagedCluster Resource

The configuration is applied to the AKS ManagedCluster resource:

```yaml
resources:
  - id: managedCluster
    template:
      spec:
        workloadAutoScalerProfile:
          keda:
            enabled: ${schema.spec.workloadAutoScaler.keda.enabled}
          verticalPodAutoscaler:
            enabled: ${schema.spec.workloadAutoScaler.verticalPodAutoscaler.enabled}
```

## What is KEDA?

**KEDA (Kubernetes Event-Driven Autoscaling)** allows applications to scale based on external metrics and events, not just CPU/memory.

### Key Features

- **Event-driven scaling** - Scale based on:
  - Message queue depth (Azure Service Bus, RabbitMQ, Kafka)
  - HTTP request rate
  - Custom metrics from Azure Monitor
  - Prometheus metrics
  - Cron schedules
  - And 50+ other scalers

- **Scale to zero** - Can scale workloads down to zero when idle
- **Built-in to AKS** - Managed by Azure, no separate installation needed
- **HPA compatible** - Works alongside Kubernetes Horizontal Pod Autoscaler

### Use Cases

1. **Message Processing**
   - Scale based on Azure Service Bus queue length
   - Process messages efficiently without over-provisioning

2. **Scheduled Workloads**
   - Scale up during business hours
   - Scale down at night/weekends

3. **HTTP-based Scaling**
   - Scale based on request rate
   - Integrate with Azure Application Gateway

4. **Custom Metrics**
   - Scale based on business KPIs
   - Use Azure Monitor custom metrics

### Example: Scale based on Azure Service Bus Queue

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: queue-processor-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: queue-processor
  minReplicaCount: 0  # Scale to zero when idle
  maxReplicaCount: 10
  triggers:
    - type: azure-servicebus
      metadata:
        queueName: orders
        namespace: my-servicebus-namespace
        messageCount: "5"  # Target 5 messages per pod
      authenticationRef:
        name: servicebus-auth
```

## What is VPA?

**VPA (Vertical Pod Autoscaler)** automatically adjusts CPU and memory requests/limits for containers based on actual usage.

### Key Features

- **Right-sizing** - Automatically set optimal resource requests
- **Continuous optimization** - Adjusts over time as usage patterns change
- **Recommendation mode** - Can provide recommendations without applying changes
- **Multi-container support** - Works with all containers in a pod

### How VPA Works

1. **Observes** actual resource usage
2. **Calculates** optimal requests/limits
3. **Recommends** or **applies** changes
4. **Evicts and recreates** pods with new resource settings (when in Auto mode)

### VPA Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Off** | Only provides recommendations | Testing, analysis |
| **Initial** | Sets requests on pod creation only | Stateful workloads |
| **Recreate** | Updates requests by recreating pods | Most workloads |
| **Auto** | Automatically applies recommendations | Production workloads |

### Example: VPA for a Deployment

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: default
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: Auto  # Automatically apply recommendations
  resourcePolicy:
    containerPolicies:
      - containerName: '*'
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 2
          memory: 2Gi
        controlledResources:
          - cpu
          - memory
```

## Deployment Configuration

### Enable Both (Default)

```yaml
apiVersion: kro.run/v1alpha1
kind: UK8SClusterPublic
metadata:
  name: my-cluster
spec:
  clusterName: my-aks-cluster
  # ... other config ...

  # Both enabled by default
  workloadAutoScaler:
    keda:
      enabled: true
    verticalPodAutoscaler:
      enabled: true
```

### Enable Only KEDA

```yaml
spec:
  workloadAutoScaler:
    keda:
      enabled: true
    verticalPodAutoscaler:
      enabled: false
```

### Enable Only VPA

```yaml
spec:
  workloadAutoScaler:
    keda:
      enabled: false
    verticalPodAutoscaler:
      enabled: true
```

### Disable Both

```yaml
spec:
  workloadAutoScaler:
    keda:
      enabled: false
    verticalPodAutoscaler:
      enabled: false
```

## Verification

### Check Cluster Configuration

```bash
# Check if KEDA is enabled
kubectl get managedcluster <cluster-name> -n <namespace> \
  -o jsonpath='{.spec.workloadAutoScalerProfile.keda.enabled}'

# Check if VPA is enabled
kubectl get managedcluster <cluster-name> -n <namespace> \
  -o jsonpath='{.spec.workloadAutoScalerProfile.verticalPodAutoscaler.enabled}'
```

### Verify KEDA is Running

```bash
# Check KEDA operator pods
kubectl get pods -n kube-system -l app=keda-operator

# Check KEDA metrics server
kubectl get pods -n kube-system -l app=keda-metrics-apiserver

# View KEDA version
kubectl get deployment keda-operator -n kube-system \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Verify VPA is Running

```bash
# Check VPA components
kubectl get pods -n kube-system | grep vpa

# Should see:
# - vpa-admission-controller
# - vpa-recommender
# - vpa-updater

# Check VPA CRDs are installed
kubectl get crd | grep verticalpodautoscaler
```

### Test KEDA

```bash
# Create a test ScaledObject
kubectl apply -f - <<EOF
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: test-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: nginx
  minReplicaCount: 1
  maxReplicaCount: 5
  triggers:
    - type: cpu
      metricType: Utilization
      metadata:
        value: "50"
EOF

# Check ScaledObject status
kubectl describe scaledobject test-scaler
```

### Test VPA

```bash
# Create a test VPA
kubectl apply -f - <<EOF
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: test-vpa
  namespace: default
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nginx
  updatePolicy:
    updateMode: "Off"  # Recommendation only
EOF

# Check VPA recommendations
kubectl describe vpa test-vpa
```

## Best Practices

### KEDA Best Practices

1. **Start Conservative**
   - Set reasonable min/max replica counts
   - Test scaling behavior under load

2. **Monitor Scaling Events**
   - Watch for rapid scaling up/down
   - Adjust cooldown periods if needed

3. **Use Authentication**
   - Always use TriggerAuthentication for secrets
   - Never hardcode credentials

4. **Combine with HPA Carefully**
   - Don't use KEDA and HPA on same deployment
   - Choose one scaling method per workload

5. **Scale to Zero Considerations**
   - Ensure cold start time is acceptable
   - Consider keeping min replicas for critical services

### VPA Best Practices

1. **Start with Recommendations**
   - Use `updateMode: "Off"` initially
   - Review recommendations before auto-applying

2. **Set Boundaries**
   - Always set minAllowed and maxAllowed
   - Prevent runaway resource requests

3. **Avoid with HPA**
   - Don't use VPA with HPA on CPU/memory
   - Can use VPA for vertical + KEDA for horizontal

4. **StatefulSets Caution**
   - Use `updateMode: "Initial"` for StatefulSets
   - Avoid pod recreation for stateful workloads

5. **Resource Policies**
   - Define per-container policies
   - Control which resources VPA can modify

## Common Patterns

### Pattern 1: Event-Driven Processing with KEDA

```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-processor
spec:
  replicas: 1  # KEDA will manage this
  template:
    spec:
      containers:
        - name: processor
          image: myapp:latest
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
---
# KEDA ScaledObject
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-processor-scaler
spec:
  scaleTargetRef:
    name: order-processor
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
    - type: azure-servicebus
      metadata:
        queueName: orders
        messageCount: "10"
```

### Pattern 2: VPA for Resource Optimization

```yaml
# Deployment with conservative requests
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
spec:
  template:
    spec:
      containers:
        - name: api
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
---
# VPA to optimize over time
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-service-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-service
  updatePolicy:
    updateMode: Auto
  resourcePolicy:
    containerPolicies:
      - containerName: api
        maxAllowed:
          cpu: "2"
          memory: 4Gi
```

### Pattern 3: KEDA + VPA Together

```yaml
# Use KEDA for horizontal scaling (replica count)
# Use VPA for vertical scaling (resource requests)
---
# KEDA handles replica count
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: worker-keda
spec:
  scaleTargetRef:
    name: worker
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus:9090
        metricName: queue_depth
        threshold: "5"
---
# VPA optimizes resource requests
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: worker-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: worker
  updatePolicy:
    updateMode: Auto
```

## Troubleshooting

### KEDA Issues

**ScaledObject not scaling:**
```bash
# Check KEDA operator logs
kubectl logs -n kube-system -l app=keda-operator --tail=100

# Check ScaledObject events
kubectl describe scaledobject <name>

# Verify trigger configuration
kubectl get scaledobject <name> -o yaml
```

**Authentication failures:**
```bash
# Check TriggerAuthentication
kubectl get triggerauthentication <name> -o yaml

# Verify secret exists and is correct
kubectl get secret <secret-name> -o yaml
```

### VPA Issues

**VPA not providing recommendations:**
```bash
# Check VPA recommender logs
kubectl logs -n kube-system -l app=vpa-recommender --tail=100

# Ensure enough data collected (needs ~24 hours)
kubectl describe vpa <name>
```

**Pods not being updated:**
```bash
# Check VPA updater logs
kubectl logs -n kube-system -l app=vpa-updater --tail=100

# Verify updateMode is set correctly
kubectl get vpa <name> -o jsonpath='{.spec.updatePolicy.updateMode}'
```

## Cost Optimization

### KEDA Cost Benefits

- **Scale to zero** - No cost when idle
- **Right-sized scaling** - Only scale when needed
- **Efficient resource use** - Match capacity to demand

### VPA Cost Benefits

- **Eliminate over-provisioning** - Right-size resource requests
- **Reduce waste** - Containers use only what they need
- **Optimize node utilization** - Better bin packing

### Monitoring Savings

```bash
# Check resource usage before/after VPA
kubectl top pods -n <namespace>

# View VPA recommendations
kubectl describe vpa <name> | grep -A 20 "Recommendation"

# Calculate potential savings
# Compare requested vs recommended resources
```

## Integration with Certification Workflow

The certification workflow validates that KEDA and VPA are properly configured:

```yaml
# Checked during certification
- Workload autoscaler profile exists
- KEDA enabled status matches desired state
- VPA enabled status matches desired state
- KEDA operator pods are running (if enabled)
- VPA components are running (if enabled)
```

See certification logs for autoscaler validation results.

## Additional Resources

### KEDA
- [KEDA Documentation](https://keda.sh/)
- [KEDA Scalers](https://keda.sh/docs/scalers/)
- [Azure KEDA Guide](https://learn.microsoft.com/azure/aks/keda-about)

### VPA
- [VPA Documentation](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [Azure VPA Guide](https://learn.microsoft.com/azure/aks/vertical-pod-autoscaler)

### Best Practices
- [AKS Autoscaling Best Practices](https://learn.microsoft.com/azure/aks/best-practices-app-scaling)
- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

---

**Updated:** 2025-11-21
**Feature:** Workload Autoscaler (KEDA & VPA)
**Status:** Production Ready
