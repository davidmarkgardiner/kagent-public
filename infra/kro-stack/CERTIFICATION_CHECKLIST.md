# UK8S Cluster Stack Certification Checklist

**Version:** 1.0.0
**Date:** 2025-11-13
**Purpose:** Automated validation checklist for UK8S cluster deployments using KRO

---

## Overview

This checklist provides validation criteria for certifying a UK8S cluster deployment. Each section contains checks that should be automated in an Argo Workflow for continuous validation and certification.

---

## 1. Pre-Deployment Validation

### 1.1 Azure Prerequisites
- [ ] Azure subscription exists and is accessible
- [ ] Target resource group exists or can be created
- [ ] Required Azure RBAC permissions are granted
- [ ] Virtual network and subnet exist with correct CIDR ranges
- [ ] Control plane managed identity exists
- [ ] Kubelet managed identity exists
- [ ] AAD admin group exists and is valid

### 1.2 Configuration Validation
- [ ] Instance YAML is valid against UK8SCluster schema
- [ ] Kubernetes version is supported (currently 1.32)
- [ ] Network CIDRs do not overlap (serviceCidr, podCidr, vnet)
- [ ] SSH public key is valid format
- [ ] All required identity resource IDs are valid ARM format
- [ ] Tags contain all mandatory fields (environment, project, costCenter)

---

## 2. KRO Resource Validation

### 2.1 ResourceGraphDefinition Status
- [ ] `uk8scluster.kro.run` RGD exists
- [ ] `uk8scluster.kro.run` RGD state is `Active`
- [ ] `uk8sjobs.kro.run` RGD exists
- [ ] `uk8sjobs.kro.run` RGD state is `Active`
- [ ] `uk8sfluxgitops.kro.run` RGD exists
- [ ] `uk8sfluxgitops.kro.run` RGD state is `Active`

### 2.2 UK8SCluster Instance
- [ ] UK8SCluster instance created successfully
- [ ] Instance state is `ACTIVE`
- [ ] Condition `InstanceManaged` is `True`
- [ ] Condition `GraphResolved` is `True`
- [ ] Condition `ResourcesReady` is `True`
- [ ] Condition `Ready` is `True`
- [ ] Finalizers are present (`kro.run/finalizer`)
- [ ] Labels include `kro.run/owned: "true"`

### 2.3 Nested KRO Resources
- [ ] UK8Sjobs instance exists in correct namespace
- [ ] UK8Sjobs state is `ACTIVE` and ready is `True`
- [ ] UK8SFluxGitOps instance exists in correct namespace
- [ ] UK8SFluxGitOps state is `ACTIVE` and ready is `True`
- [ ] All nested resources use `targetNamespace` correctly

---

## 3. Azure Service Operator (ASO) Resources

### 3.1 Resource Group
```bash
kubectl get resourcegroup -n <targetNamespace>
```
- [ ] ResourceGroup exists with correct name
- [ ] ResourceGroup condition `Ready` is `True`
- [ ] ResourceGroup condition `Reason` is `Succeeded`
- [ ] No severity errors present

### 3.2 AKS Managed Cluster
```bash
kubectl get managedcluster -n <targetNamespace>
```
- [ ] ManagedCluster resource exists
- [ ] ManagedCluster condition `Ready` is `True`
- [ ] ManagedCluster provisioning state is `Succeeded`
- [ ] Kubernetes version matches specification
- [ ] Node pool configuration matches specification
- [ ] Network profile matches specification (serviceCidr, podCidr)
- [ ] Identity profile contains correct managed identities
- [ ] AAD profile enabled with correct admin groups
- [ ] Workload identity enabled
- [ ] OIDC issuer enabled
- [ ] Security profile configured (SecureBoot, vTPM, Defender)
- [ ] Service mesh enabled with correct Istio revision
- [ ] Auto-upgrade channel configured correctly
- [ ] Storage drivers enabled (disk, file, snapshot)
- [ ] Addons configured (Azure Key Vault, Azure Policy)

### 3.3 Managed Identities
```bash
kubectl get userassignedidentity -n <targetNamespace>
```
- [ ] cert-manager identity created and ready
- [ ] external-dns identity created and ready
- [ ] external-secrets identity created and ready
- [ ] All identities have condition `Ready: True`
- [ ] All identities have correct naming convention

### 3.4 Federated Identity Credentials
```bash
kubectl get federatedidentitycredential -n <targetNamespace>
```
- [ ] cert-manager FIC created and ready
- [ ] external-dns FIC created and ready
- [ ] external-dns-bcm FIC created and ready (if applicable)
- [ ] external-secrets FIC created and ready
- [ ] flux-image FIC created and ready
- [ ] flux-source FIC created and ready
- [ ] All FICs reference valid resource groups
- [ ] All FICs have correct OIDC issuer URL
- [ ] All FICs have correct subject (namespace/serviceAccount)
- [ ] All FICs have condition `Ready: True`

---

## 4. Flux GitOps Validation

### 4.1 Flux Extension (Azure AKS Extension)
```bash
az k8s-extension show \
  --cluster-name <clusterName> \
  --resource-group <resourceGroup> \
  --cluster-type managedClusters \
  --name flux
```
- [ ] Flux extension installed on AKS cluster
- [ ] Extension provisioning state is `Succeeded`
- [ ] Extension auto-upgrade enabled
- [ ] Flux version is compatible

### 4.2 Flux Core Components
```bash
kubectl get deployment -n flux-system
```
- [ ] `flux-system` namespace exists
- [ ] `source-controller` deployment ready (1/1)
- [ ] `kustomize-controller` deployment ready (1/1)
- [ ] `helm-controller` deployment ready (1/1)
- [ ] `notification-controller` deployment ready (1/1)
- [ ] `image-reflector-controller` deployment ready (if image automation enabled)
- [ ] `image-automation-controller` deployment ready (if image automation enabled)

### 4.3 GitRepository Sources
```bash
kubectl get gitrepository -n flux-system
```
- [ ] Core GitRepository exists for uk8s-core
- [ ] Core GitRepository condition `Ready` is `True`
- [ ] Core GitRepository artifact exists
- [ ] Config GitRepository exists for uk8s-config (if configured)
- [ ] Config GitRepository condition `Ready` is `True`
- [ ] All GitRepositories can successfully clone from Azure DevOps
- [ ] Authentication using workload identity is working

### 4.4 Flux Kustomizations
```bash
kubectl get kustomization -n flux-system
```
- [ ] Core Kustomization applied successfully
- [ ] Core Kustomization condition `Ready` is `True`
- [ ] Config Kustomization applied successfully (if configured)
- [ ] Config Kustomization condition `Ready` is `True`
- [ ] All kustomizations reconcile without errors
- [ ] Reconciliation interval is appropriate

---

## 5. Post-Deployment Jobs

### 5.1 Job Resources
```bash
kubectl get job -n <targetNamespace>
```
- [ ] Grafana integration job exists (if monitoring configured)
- [ ] Grafana integration job completed successfully
- [ ] Job pods completed without errors
- [ ] Job backoff limit not exceeded
- [ ] ServiceAccount for jobs exists with workload identity annotation

### 5.2 Job Validation
- [ ] Azure Monitor metrics enabled on cluster (if configured)
- [ ] Grafana integration configured (if configured)
- [ ] Jobs execute in correct namespace (targetNamespace)
- [ ] Jobs have access to required Azure resources via workload identity
- [ ] Job logs show successful completion

---

## 6. Cluster Connectivity & Access

### 6.1 API Server Access
```bash
az aks get-credentials \
  --name <clusterName> \
  --resource-group <resourceGroup>
kubectl cluster-info
```
- [ ] Can authenticate to AKS cluster
- [ ] API server responds to requests
- [ ] RBAC authorization working correctly
- [ ] AAD integration functional for user access

### 6.2 Node Health
```bash
kubectl get nodes
```
- [ ] All nodes in `Ready` state
- [ ] Node count matches specification
- [ ] Nodes have correct labels (system pool)
- [ ] Nodes running correct OS SKU (AzureLinux)
- [ ] Node VM size matches specification
- [ ] Nodes have correct availability zones

### 6.3 System Pods
```bash
kubectl get pods -n kube-system
```
- [ ] CoreDNS pods running (2/2)
- [ ] kube-proxy pods running on all nodes
- [ ] metrics-server pod running
- [ ] azure-cni pods running on all nodes
- [ ] azure-ip-masq-agent pods running
- [ ] cloud-node-manager pods running

---

## 7. Security & Compliance

### 7.1 Security Features
- [ ] Local accounts disabled (if configured)
- [ ] Run command disabled
- [ ] Microsoft Defender for Containers enabled
- [ ] Secure boot enabled on nodes
- [ ] vTPM enabled on nodes
- [ ] Azure Policy addon installed and running

### 7.2 Workload Identity
```bash
kubectl get serviceaccount -A -o json | jq '.items[] | select(.metadata.annotations["azure.workload.identity/client-id"])'
```
- [ ] Workload identity enabled on cluster
- [ ] OIDC issuer URL configured and accessible
- [ ] ServiceAccounts have workload identity annotations
- [ ] Pods can successfully authenticate to Azure using workload identity
- [ ] Federated credentials properly linked

### 7.3 Network Security
- [ ] Network policies can be applied (if configured)
- [ ] Service mesh injection working (if Istio enabled)
- [ ] Internal ingress accessible (if configured)
- [ ] External ingress accessible (if configured)

---

## 8. Istio Service Mesh Validation

### 8.1 Istio Components (if enabled)
```bash
kubectl get pods -n aks-istio-system
```
- [ ] Istio control plane namespace exists
- [ ] istiod deployment ready
- [ ] Istio ingress gateways deployed (internal/external as configured)
- [ ] Istio revision matches specification (e.g., asm-1-27)
- [ ] Istio validating webhook configured

### 8.2 Service Mesh Configuration
```bash
kubectl get gateway,virtualservice,destinationrule -A
```
- [ ] Istio CRDs installed
- [ ] Gateway resources can be created
- [ ] VirtualService resources can be created
- [ ] Sidecar injection working for labeled namespaces

---

## 9. Storage & Volumes

### 9.1 Storage Drivers
```bash
kubectl get csidrivers
```
- [ ] Azure Disk CSI driver installed
- [ ] Azure File CSI driver installed
- [ ] Snapshot controller installed and running
- [ ] Storage classes created (default, managed-premium, etc.)

### 9.2 Storage Functionality
- [ ] Can create PersistentVolumeClaim with Azure Disk
- [ ] Can create PersistentVolumeClaim with Azure Files
- [ ] Volume snapshots can be created
- [ ] Volumes can be mounted to pods

---

## 10. Addons Validation

### 10.1 Azure Key Vault Secrets Provider
```bash
kubectl get pods -n kube-system -l app=secrets-store-csi-driver
```
- [ ] Secrets Store CSI driver pods running
- [ ] Azure Key Vault provider pods running
- [ ] Secret rotation enabled (if configured)
- [ ] Can create SecretProviderClass
- [ ] Can mount secrets from Key Vault

### 10.2 Azure Policy
```bash
kubectl get pods -n kube-system -l app=azure-policy
```
- [ ] Azure Policy pods running
- [ ] Policy assignments syncing to cluster
- [ ] Constraint templates created
- [ ] Audit/deny policies enforcing

### 10.3 Workload Auto Scaler
- [ ] KEDA installed (if enabled)
- [ ] KEDA operator pod running
- [ ] VPA installed (if enabled)
- [ ] VPA admission controller running
- [ ] VPA recommender running

---

## 11. Monitoring & Observability

### 11.1 Azure Monitor Integration
- [ ] Azure Monitor Container Insights enabled
- [ ] Metrics flowing to Azure Monitor workspace
- [ ] Logs flowing to Log Analytics workspace
- [ ] Prometheus metrics collection enabled
- [ ] Custom metrics annotations configured

### 11.2 Grafana Integration (if configured)
- [ ] Grafana linked to Azure Monitor workspace
- [ ] Dashboards accessible and populated with data
- [ ] Alerts configured (if required)

---

## 12. GitOps Reconciliation

### 12.1 Application Deployment
- [ ] Applications deployed via Flux are running
- [ ] HelmReleases reconciled successfully
- [ ] Kustomizations applied without errors
- [ ] Image automation working (if configured)

### 12.2 Configuration Drift Detection
- [ ] Flux detects and reconciles drift
- [ ] Manual changes to managed resources are reverted
- [ ] Git remains source of truth

---

## 13. Cleanup & Lifecycle

### 13.1 Resource Cleanup
- [ ] TTL for completed jobs configured
- [ ] Old pods and jobs cleaned up automatically
- [ ] Log retention policies configured

### 13.2 Upgrade Readiness
- [ ] Auto-upgrade channel configured
- [ ] Node OS auto-upgrade configured
- [ ] Maintenance windows configured (if required)

---

## Certification Workflow Implementation Notes

### Workflow Structure
```yaml
# Suggested Argo Workflow structure
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: uk8s-cluster-certification
spec:
  entrypoint: certify-cluster
  arguments:
    parameters:
      - name: clusterName
      - name: resourceGroup
      - name: targetNamespace
      - name: subscriptionId

  templates:
    - name: certify-cluster
      dag:
        tasks:
          - name: validate-kro-resources
            template: check-kro-status
          - name: validate-aso-resources
            template: check-aso-resources
            depends: validate-kro-resources
          - name: validate-flux
            template: check-flux-status
            depends: validate-aso-resources
          - name: validate-cluster-health
            template: check-cluster-health
            depends: validate-aso-resources
          - name: validate-security
            template: check-security-features
            depends: validate-cluster-health
          - name: validate-networking
            template: check-networking
            depends: validate-cluster-health
          - name: validate-addons
            template: check-addons
            depends: validate-cluster-health
          - name: generate-report
            template: create-certification-report
            depends: validate-flux.Succeeded && validate-security.Succeeded && validate-networking.Succeeded && validate-addons.Succeeded
```

### Validation Scripts Location
- Store validation scripts in: `kro-stack/certification/scripts/`
- Each section should have its own validation script
- Scripts should return JSON results for workflow processing
- Use exit codes: 0 = pass, 1 = fail, 2 = warning

### Output Requirements
- Generate JSON report with pass/fail status for each check
- Include timestamps and cluster metadata
- Store reports in ConfigMap or external storage
- Send notifications on certification failures

### Automation Tools
- **kubectl**: For Kubernetes resource validation
- **az cli**: For Azure resource validation (with workload identity)
- **jq**: For JSON parsing and reporting
- **helm**: For Helm release validation
- **flux cli**: For Flux-specific checks

### Retry & Timeout Configuration
- Allow 30 minutes for full cluster provisioning
- Retry failed checks up to 3 times with exponential backoff
- Set reasonable timeouts for each validation section:
  - KRO validation: 5 minutes
  - ASO validation: 15 minutes
  - Flux validation: 10 minutes
  - Cluster health: 5 minutes
  - Security: 5 minutes

---

## Success Criteria

A UK8S cluster deployment is **CERTIFIED** when:
- ✅ All mandatory checks pass (90%+)
- ✅ Zero critical security issues
- ✅ Cluster is accessible and responsive
- ✅ GitOps reconciliation working
- ✅ No pods in CrashLoopBackOff or Error state
- ✅ All ASO resources report Ready: True
- ✅ Flux extension and controllers operational

---

## Failure Handling

If certification fails:
1. **Capture full cluster state** (logs, events, resource dumps)
2. **Store diagnostic bundle** for troubleshooting
3. **Send alert** to platform team
4. **Mark cluster** with label `certified: false`
5. **Generate detailed failure report** with remediation steps
6. **Optionally trigger automated rollback** for critical failures

---

## Next Steps for Workflow Engineer

1. Review this checklist and prioritize checks
2. Create validation scripts for each section
3. Build Argo WorkflowTemplate based on structure above
4. Test workflow against existing UK8S cluster
5. Integrate with CI/CD pipeline
6. Set up monitoring and alerting for certification failures
7. Document workflow usage and troubleshooting guide
