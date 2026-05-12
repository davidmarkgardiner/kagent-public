# Playbook: Deploy VolBack (Backup Solution)

**Priority:** CRITICAL  
**Estimated Time:** 45 minutes  
**Prerequisites:** S3-compatible storage or NAS

---

## Overview

VolBack provides automated backup for Kubernetes PVCs with Longhorn integration.

---

## Step 1: Prepare S3 Credentials

```bash
# Create secret for S3 access
kubectl create namespace backup

kubectl create secret generic s3-credentials \
  --from-literal=access-key="YOUR_ACCESS_KEY" \
  --from-literal=secret-key="YOUR_SECRET_KEY" \
  -n backup
```

---

## Step 2: Create Service Account

```yaml
# volback-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: volback
  namespace: backup
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: volback
rules:
  - apiGroups: [""]
    resources: ["persistentvolumeclaims", "persistentvolumes", "pods", "pods/exec"]
    verbs: ["get", "list", "watch", "create", "delete"]
  - apiGroups: ["longhorn.io"]
    resources: ["volumes", "snapshots"]
    verbs: ["get", "list", "watch", "create", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: volback
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: volback
subjects:
  - kind: ServiceAccount
    name: volback
    namespace: backup
```

---

## Step 3: Deploy VolBack

```yaml
# volback-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: volback
  namespace: backup
spec:
  replicas: 1
  selector:
    matchLabels:
      app: volback
  template:
    metadata:
      labels:
        app: volback
    spec:
      serviceAccountName: volback
      containers:
        - name: volback
          image: offen/docker-volume-backup:latest
          env:
            - name: BACKUP_CRON_EXPRESSION
              value: "0 2 * * *"  # Daily at 2am
            - name: BACKUP_RETENTION_DAYS
              value: "30"
            - name: AWS_S3_BUCKET_NAME
              value: "homelab-backups"
            - name: AWS_S3_ENDPOINT
              value: "s3.amazonaws.com"  # Or your MinIO endpoint
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: access-key
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: secret-key
            - name: BACKUP_FILENAME
              value: "backup-{{ .Now }}"
            - name: BACKUP_ARCHIVE
              value: "/backup"
            - name: BACKUP_STOP_CONTAINER_LABEL
              value: "volback.stop"
            - name: BACKUP_FROM_SNAPSHOT
              value: "true"
          volumeMounts:
            - name: backup-cache
              mountPath: /cache
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
      volumes:
        - name: backup-cache
          emptyDir: {}
```

---

## Step 4: Add Backup Labels to Critical PVCs

```bash
# Label important PVCs for backup
kubectl label pvc -n gitea gitea-data volback.stop=true
kubectl label pvc -n ghost ghost-content volback.stop=true
kubectl label pvc -n ghostfolio ghostfolio-data volback.stop=true
kubectl label pvc -n vikunja vikunja-data volback.stop=true
kubectl label pvc -n vaultwarden vaultwarden-data volback.stop=true
```

---

## Step 5: Create Backup Status Dashboard

```yaml
# backup-dashboard-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backup-dashboard
  namespace: backup
data:
  dashboard.html: |
    <!DOCTYPE html>
    <html>
    <head>
      <title>Backup Status</title>
      <style>
        body { font-family: system-ui; padding: 2rem; background: #1a1a2e; color: #fff; }
        .status-ok { color: #4ade80; }
        .status-fail { color: #f87171; }
        .status-pending { color: #fbbf24; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #333; }
        th { color: #94a3b8; }
      </style>
    </head>
    <body>
      <h1>🛡️ Backup Status</h1>
      <div id="status">Loading...</div>
      <script>
        // Fetch backup status from API
        fetch('/api/backups')
          .then(r => r.json())
          .then(data => {
            // Render table
          });
      </script>
    </body>
    </html>
```

---

## Step 6: Add Alerting

```yaml
# backup-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: backup-alerts
  namespace: monitoring
spec:
  groups:
    - name: backup
      rules:
        - alert: BackupFailed
          expr: time() - volback_last_success > 90000  # 25 hours
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Backup has not completed in 25 hours"
            
        - alert: BackupOld
          expr: time() - volback_last_success > 172800  # 48 hours
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Backup is more than 48 hours old"
```

---

## Verification

```bash
# Check deployment
kubectl get pods -n backup

# View logs
kubectl logs -n backup deployment/volback -f

# Test manual backup
kubectl exec -n backup deployment/volback -- /bin/backup

# Check S3 for backups
aws s3 ls s3://homelab-backups/
```

---

## Restore Procedure

```bash
# List available backups
aws s3 ls s3://homelab-backups/ | sort

# Download backup
aws s3 cp s3://homelab-backups/backup-20240208.tar.gz /tmp/

# Restore to PVC
tar -xzf /tmp/backup-20240208.tar.gz -C /mnt/restore

# Or use VolBack restore
kubectl exec -n backup deployment/volback -- /bin/restore
```

---

## Update services.json

```json
{
  "name": "Backup Dashboard",
  "url": "backup.lab.{{INGRESS_DOMAIN}}",
  "nodePort": 30086,
  "namespace": "backup",
  "category": "infrastructure"
}
```

---

**Next:** Deploy [Outline Wiki](./03-deploy-outline.md)
