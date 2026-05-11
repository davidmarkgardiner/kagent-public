# Quick Start Guide

Get your UK8S AKS cluster running in 5 minutes!

## Prerequisites

- [x] Management cluster with KRO installed
- [x] Azure Service Operator (ASO) v2 installed and configured
- [x] Azure subscription with appropriate permissions
- [x] Pre-existing VNet and subnet
- [x] Azure AD admin group created

## Step 1: Deploy ResourceGraphDefinitions

```bash
# Apply all KRO definitions
kubectl apply -f definitions/

# Verify RGDs are registered
kubectl get resourcegraphdefinitions
```

Expected output:
```
NAME                      AGE
uk8scluster.kro.run      5s
uk8scronjobs.kro.run     5s
uk8sfluxgitops.kro.run   5s
uk8sjobs.kro.run         5s
```

## Step 2: Configure RBAC

```bash
# Apply KRO controller permissions
kubectl apply -f rbac/kro-controller-rbac.yaml

# Verify ServiceAccount created
kubectl get sa -n kro-system kro-controller-uk8s
```

## Step 3: Prepare Your Cluster Configuration

```bash
# Copy the dev example
cp instances/dev/example-cluster.yaml my-cluster.yaml

# Edit with your values
vim my-cluster.yaml
```

**Required Values to Update**:
```yaml
metadata:
  name: my-cluster-name              # Change this

spec:
  clusterName: "my-cluster-name"     # Must match metadata.name
  subscriptionId: "YOUR-SUB-ID"      # Your Azure subscription
  resourceGroup: "rg-my-cluster"     # Your resource group name
  sshPublicKey: "ssh-rsa AAA..."     # Your SSH public key

  network:
    vnetSubscriptionId: "YOUR-VNET-SUB-ID"
    vnetResourceGroup: "rg-network"
    vnetName: "vnet-shared"
    subnetName: "snet-aks"

  identity:
    controlPlaneIdentityResourceId: "/subscriptions/.../uami-controlplane"
    kubeletIdentityClientId: "UUID"
    kubeletIdentityObjectId: "UUID"
    kubeletIdentityResourceId: "/subscriptions/.../uami-kubelet"
    fluxClientId: "UUID"

  aad:
    adminGroupObjectIds:
      - "YOUR-AAD-GROUP-ID"

  security:
    defenderWorkspaceResourceId: "/subscriptions/.../workspaces/law-security"

  flux:
    core:
      url: "https://dev.azure.com/org/project/_git/uk8s-core"
    config:
      url: "https://dev.azure.com/org/project/_git/uk8s-config"
```

## Step 4: Deploy Your Cluster

```bash
# Apply the cluster configuration
kubectl apply -f my-cluster.yaml

# Watch the deployment
kubectl get uk8scluster -n uk8s-nextgen -w
```

## Step 5: Monitor Progress

### Check UK8SCluster status
```bash
kubectl describe uk8scluster my-cluster-name -n uk8s-nextgen
```

### Check Azure resources being created
```bash
# Resource groups
kubectl get resourcegroups -n uk8s-nextgen

# Managed clusters
kubectl get managedclusters -n uk8s-nextgen

# Identities
kubectl get userassignedidentities -n uk8s-nextgen

# Federated credentials
kubectl get federatedidentitycredentials -n uk8s-nextgen
```

### Check child resources
```bash
# Flux GitOps configuration
kubectl get uk8sfluxgitops -n uk8s-nextgen

# Post-deployment jobs
kubectl get uk8sjobs -n uk8s-nextgen

# Check if Grafana integration job ran
kubectl get jobs -n flux-system
```

## Step 6: Verify Deployment

### Check cluster is ready
```bash
# Should show ProvisioningState: Succeeded
kubectl get managedcluster my-cluster-name -n uk8s-nextgen -o yaml
```

### Check Flux configuration
```bash
# Extensions
kubectl get extension -n uk8s-nextgen

# Flux configurations
kubectl get fluxconfiguration -n uk8s-nextgen
```

### Get cluster credentials
```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group rg-my-cluster \
  --name my-cluster-name

# Verify access
kubectl get nodes
```

## Troubleshooting

### Deployment stuck?

**Check KRO controller logs**:
```bash
kubectl logs -n kro-system -l app=kro-controller
```

**Check ASO operator logs**:
```bash
kubectl logs -n azureserviceoperator-system -l app.kubernetes.io/name=azure-service-operator
```

### Resource creation failed?

**Check specific resource status**:
```bash
# For ManagedCluster
kubectl describe managedcluster my-cluster-name -n uk8s-nextgen

# Look for Status.Conditions
kubectl get managedcluster my-cluster-name -n uk8s-nextgen -o jsonpath='{.status.conditions}'
```

### Flux not deploying?

**Check if OIDC ConfigMap exists**:
```bash
kubectl get configmap oidc-my-cluster-name -n uk8s-nextgen
```

**Check Flux Extension**:
```bash
kubectl describe extension flux-my-cluster-name -n uk8s-nextgen
```

## Common Patterns

### Development Cluster (Small)
```yaml
nodePool:
  vmSize: "Standard_D4s_v3"
  count: 1
  enableAutoScaling: false

sku:
  tier: "Free"

serviceMesh:
  externalIngressEnabled: false
```

### Production Cluster (HA)
```yaml
nodePool:
  vmSize: "Standard_D8s_v3"
  count: 3
  enableAutoScaling: true
  minCount: 3
  maxCount: 10
  availabilityZones: ["1", "2", "3"]

sku:
  tier: "Standard"

serviceMesh:
  externalIngressEnabled: true
```

## Next Steps

1. **Configure monitoring**: Set up Grafana dashboards
2. **Deploy applications**: Use Flux to deploy your apps
3. **Configure networking**: Set up External DNS and Cert Manager
4. **Set up GitOps**: Push configurations to your Git repositories
5. **Scale**: Add more node pools or enable autoscaling

## Getting Help

- **Documentation**: See [README.md](../README.md)
- **Improvements**: See [docs/IMPROVEMENTS.md](IMPROVEMENTS.md)
- **KRO Issues**: Check KRO controller logs
- **Azure Issues**: Check ASO operator logs

## Clean Up

To delete a cluster:

```bash
# Delete the UK8SCluster instance
kubectl delete uk8scluster my-cluster-name -n uk8s-nextgen

# KRO will cascade delete:
# - ManagedCluster
# - ResourceGroup
# - Identities
# - Federated Credentials
# - Flux configurations
# - Jobs
```

**Note**: The actual Azure resources will be deleted by ASO.
