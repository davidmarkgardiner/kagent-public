# Blue/Green Deployment Demo with Argo Rollouts

This demo shows how to perform a blue/green deployment using Argo Rollouts with Argo Workflows orchestration.

## 📋 Prerequisites

Ensure you have the following installed:
- kubectl
- Argo Workflows CLI (`argo`)
- Argo Rollouts CLI (`kubectl argo rollouts`)
- A running Kubernetes cluster (minikube, kind, etc.)

## 🚀 Quick Start Demo

### Step 1: Install Argo Rollouts Controller

```bash
# Install Argo Rollouts in your cluster
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Wait for rollouts controller to be ready
kubectl rollout status deployment/argo-rollouts -n argo-rollouts

# Install Argo Rollouts CLI (if not already installed)
# On macOS:
# brew install argoproj/tap/kubectl-argo-rollouts
# On Linux:
# curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
# chmod +x ./kubectl-argo-rollouts-linux-amd64
# sudo mv ./kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts
```

### Step 2: Deploy Initial Application (Blue Version)

```bash
# Navigate to the blue-green directory
cd /Users/davidgardiner/Desktop/repo/argo-workflow/k8s/argo-workflows/blue-green

# Deploy the services
kubectl apply -f services.yaml

# Deploy the initial rollout with analysis templates
kubectl apply -f analysis-templates.yaml
kubectl apply -f rollout.yaml

# Wait for initial deployment to complete
kubectl argo rollouts get rollout blue-green-demo --watch
```

**Expected output:**
```
Name:            blue-green-demo
Namespace:       default
Status:          ✓ Healthy
Strategy:        BlueGreen
Images:          nginx:1.21 (stable)
Replicas:
  Desired:       3
  Current:       3
  Updated:       3
  Ready:         3
  Available:     3
```

### Step 3: Test Current Blue Environment

```bash
# Port forward to test the active service
kubectl port-forward svc/blue-green-active 8080:80 &

# Test the current version (should show nginx:1.21 default page)
curl http://localhost:8080

# Kill the port-forward process
pkill -f "kubectl port-forward svc/blue-green-active"
```

### Step 4: Deploy Green Version (Using Workflow)

```bash
# Deploy the workflow template
kubectl apply -f deployment-workflow.yaml

# Submit a workflow to deploy nginx:1.22 (green version)
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: blue-green-deploy-
spec:
  workflowTemplateRef:
    name: blue-green-deployment-workflow
  arguments:
    parameters:
    - name: applicationName
      value: "blue-green-demo"
    - name: newImageTag
      value: "nginx:1.22"
    - name: environment
      value: "demo"
    - name: autoPromote
      value: "false"  # Manual promotion for demo purposes
    - name: rollbackOnFailure
      value: "true"
EOF
```

### Step 5: Monitor the Deployment Process

```bash
# Watch the workflow progress
WORKFLOW_NAME=$(argo list | grep blue-green-deploy | head -1 | awk '{print $1}')
echo "Monitoring workflow: $WORKFLOW_NAME"
argo watch $WORKFLOW_NAME

# In another terminal, watch the rollout status
kubectl argo rollouts get rollout blue-green-demo --watch
```

**Expected rollout progression:**
```
Name:            blue-green-demo
Namespace:       default
Status:          ॥ Paused
Message:         BlueGreenPause
Strategy:        BlueGreen
Images:          nginx:1.21 (stable)
                 nginx:1.22 (preview)
Replicas:
  Desired:       3
  Current:       4
  Updated:       1
  Ready:         4
  Available:     4
```

### Step 6: Test Both Blue and Green Environments

```bash
# Test the active (blue) service - still nginx:1.21
kubectl port-forward svc/blue-green-active 8080:80 &
curl -s http://localhost:8080 | grep -i nginx
pkill -f "kubectl port-forward svc/blue-green-active"

# Test the preview (green) service - new nginx:1.22
kubectl port-forward svc/blue-green-preview 8081:80 &
curl -s http://localhost:8081 | grep -i nginx
pkill -f "kubectl port-forward svc/blue-green-preview"
```

### Step 7: Promote Green to Active (Manual)

Since we set `autoPromote: false`, we need to manually promote:

```bash
# Promote the green version to active
kubectl argo rollouts promote blue-green-demo

# Watch the promotion process
kubectl argo rollouts get rollout blue-green-demo --watch
```

**After promotion:**
```
Name:            blue-green-demo
Namespace:       default
Status:          ✓ Healthy
Strategy:        BlueGreen
Images:          nginx:1.22 (stable)
Replicas:
  Desired:       3
  Current:       3
  Updated:       3
  Ready:         3
  Available:     3
```

### Step 8: Verify Traffic Switch

```bash
# Test that active service now serves nginx:1.22
kubectl port-forward svc/blue-green-active 8080:80 &
curl -s http://localhost:8080 | grep -i nginx
pkill -f "kubectl port-forward svc/blue-green-active"

# The old version should be scaled down after scaleDownDelaySeconds (30s)
kubectl get pods -l app=blue-green-demo
```

## 🔄 Advanced Demo: Automated Blue/Green with Analysis

### Step 9: Deploy with Auto-Promotion

```bash
# Submit a workflow with auto-promotion enabled
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: blue-green-auto-deploy-
spec:
  workflowTemplateRef:
    name: blue-green-deployment-workflow
  arguments:
    parameters:
    - name: applicationName
      value: "blue-green-demo"
    - name: newImageTag
      value: "nginx:1.23"
    - name: environment
      value: "demo"
    - name: autoPromote
      value: "true"  # Enable auto-promotion
    - name: rollbackOnFailure
      value: "true"
EOF
```

### Step 10: Watch Automated Process

```bash
# Monitor both workflow and rollout simultaneously
WORKFLOW_NAME=$(argo list | grep blue-green-auto-deploy | head -1 | awk '{print $1}')

# Terminal 1: Watch workflow
argo watch $WORKFLOW_NAME

# Terminal 2: Watch rollout
kubectl argo rollouts get rollout blue-green-demo --watch
```

## 🛠️ Rollback Demo

### Step 11: Simulate Failed Deployment

```bash
# Deploy with an invalid image to trigger rollback
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: blue-green-rollback-demo-
spec:
  workflowTemplateRef:
    name: blue-green-deployment-workflow
  arguments:
    parameters:
    - name: applicationName
      value: "blue-green-demo"
    - name: newImageTag
      value: "nginx:invalid-tag"  # This will fail
    - name: environment
      value: "demo"
    - name: autoPromote
      value: "true"
    - name: rollbackOnFailure
      value: "true"
EOF

# Watch the rollback process
WORKFLOW_NAME=$(argo list | grep blue-green-rollback-demo | head -1 | awk '{print $1}')
argo watch $WORKFLOW_NAME
kubectl argo rollouts get rollout blue-green-demo --watch
```

## 📊 Monitoring and Observability

### View Rollout History

```bash
# Check rollout history
kubectl argo rollouts history blue-green-demo

# Get detailed rollout information
kubectl argo rollouts describe rollout blue-green-demo

# Check current status
kubectl argo rollouts status blue-green-demo
```

### View Workflow History

```bash
# List all blue-green workflows
argo list | grep blue-green

# Get workflow details
argo get $WORKFLOW_NAME

# View workflow logs
argo logs $WORKFLOW_NAME
```

## 🧹 Cleanup

```bash
# Delete all workflows
argo delete --all

# Delete the rollout
kubectl delete rollout blue-green-demo

# Delete services and analysis templates
kubectl delete -f services.yaml
kubectl delete -f analysis-templates.yaml
kubectl delete -f deployment-workflow.yaml

# Optional: Remove Argo Rollouts
kubectl delete -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
kubectl delete namespace argo-rollouts
```

## 🎯 Key Concepts Demonstrated

### 1. **Blue/Green Strategy**
- **Blue (Active)**: Current production version serving traffic
- **Green (Preview)**: New version being tested
- **Instant Switch**: Traffic switches instantly from blue to green

### 2. **Analysis Templates**
- **Pre-promotion Analysis**: Validates green environment before promotion
- **Post-promotion Analysis**: Monitors active environment after promotion
- **Metrics-based Decisions**: Uses Prometheus metrics for automatic decisions

### 3. **Workflow Orchestration**
- **Parameter Validation**: Ensures deployment parameters are correct
- **Progressive Steps**: Updates → Analysis → Decision → Promotion
- **Error Handling**: Automatic rollback on failure

### 4. **Safety Features**
- **Manual Gates**: `autoPromotionEnabled: false` requires manual approval
- **Rollback Capability**: Automatic rollback on analysis failure
- **Scale Down Delay**: Keeps old version running for quick rollback

## 🔍 Troubleshooting

### Common Issues

1. **Rollout Stuck in Paused State**
   ```bash
   # Check if analysis is running
   kubectl get analysisruns

   # Manually promote if needed
   kubectl argo rollouts promote blue-green-demo
   ```

2. **Analysis Failing**
   ```bash
   # Check analysis run logs
   kubectl describe analysisrun <analysis-run-name>

   # Skip analysis (for testing)
   kubectl argo rollouts promote blue-green-demo --skip-current-step
   ```

3. **Workflow Failures**
   ```bash
   # Check workflow status
   argo get $WORKFLOW_NAME

   # View detailed logs
   argo logs $WORKFLOW_NAME
   ```

## 📈 Next Steps

- **Add Real Metrics**: Configure Prometheus for actual analysis
- **Integrate Notifications**: Add Slack/Teams notifications
- **GitOps Integration**: Trigger deployments from Git commits
- **Multi-Environment**: Extend to staging → production pipeline
- **Canary Deployments**: Explore canary strategy for gradual rollouts

## 🎉 Success Criteria

By the end of this demo, you should see:

1. ✅ Successful blue → green transition
2. ✅ Traffic serving from new version
3. ✅ Old version cleanly scaled down
4. ✅ Workflow completing successfully
5. ✅ Ability to rollback if needed

**Congratulations! You've successfully demonstrated blue/green deployment with Argo Rollouts and Workflows!** 🎊