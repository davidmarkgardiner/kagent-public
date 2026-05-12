# Playbook: Deploy Vaultwarden

**Priority:** HIGH  
**Estimated Time:** 30 minutes  
**Prerequisites:** Authentik SSO already configured

---

## Overview

Vaultwarden is a lightweight, self-hosted Bitwarden-compatible password manager.

---

## Step 1: Create Namespace

```bash
kubectl create namespace vaultwarden
```

---

## Step 2: Create PVC

```yaml
# vaultwarden-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vaultwarden-data
  namespace: vaultwarden
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 5Gi
```

```bash
kubectl apply -f vaultwarden-pvc.yaml
```

---

## Step 3: Create Deployment

```yaml
# vaultwarden-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vaultwarden
  namespace: vaultwarden
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vaultwarden
  template:
    metadata:
      labels:
        app: vaultwarden
    spec:
      containers:
        - name: vaultwarden
          image: vaultwarden/server:latest
          ports:
            - containerPort: 80
          env:
            - name: WEBSOCKET_ENABLED
              value: "true"
            - name: SIGNUPS_ALLOWED
              value: "false"  # Set to true initially, then disable
            - name: ADMIN_TOKEN
              valueFrom:
                secretKeyRef:
                  name: vaultwarden-admin
                  key: token
          volumeMounts:
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: vaultwarden-data
```

---

## Step 4: Create Secret

```bash
# Generate admin token
ADMIN_TOKEN=$(openssl rand -base64 48)

# Create secret
kubectl create secret generic vaultwarden-admin \
  --from-literal=token="$ADMIN_TOKEN" \
  -n vaultwarden

# Save token to GCloud for backup
echo "$ADMIN_TOKEN" | gcloud secrets versions add vaultwarden-admin-token --data-file=-
```

---

## Step 5: Create Service

```yaml
# vaultwarden-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: vaultwarden
  namespace: vaultwarden
spec:
  type: NodePort
  selector:
    app: vaultwarden
  ports:
    - name: http
      port: 80
      targetPort: 80
      nodePort: 30095
    - name: websocket
      port: 3012
      targetPort: 3012
      nodePort: 30085
```

```bash
kubectl apply -f vaultwarden-service.yaml
```

---

## Step 6: Add to NPM

```bash
# Get NPM token
NPM_TOKEN=$(curl -s -X POST "https://npm.lab.{{INGRESS_DOMAIN}}/api/tokens" \
  -H "Content-Type: application/json" \
  -d '{"identity":"USER","secret":"PASSWORD"}' | jq -r '.token')

# Create proxy host
curl -X POST "https://npm.lab.{{INGRESS_DOMAIN}}/api/nginx/proxy-hosts" \
  -H "Authorization: Bearer $NPM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_names": ["vault.lab.{{INGRESS_DOMAIN}}"],
    "forward_scheme": "http",
    "forward_host": "192.168.6.6",
    "forward_port": 30095,
    "certificate_id": 1,
    "ssl_forced": true,
    "http2_support": true
  }'
```

---

## Step 7: Configure Authentik SSO (Optional)

Add to Authentik:

```yaml
# SAML configuration
name: Vaultwarden
slug: vaultwarden
provider_type: saml
acs_url: https://vault.lab.{{INGRESS_DOMAIN}}/identity/connect/saml/acs
audience: https://vault.lab.{{INGRESS_DOMAIN}}
```

---

## Step 8: First Setup

1. Visit https://vault.lab.{{INGRESS_DOMAIN}}
2. Create first account (admin)
3. Disable signups: Set `SIGNUPS_ALLOWED=false`
4. Configure backup schedule (see VolBack playbook)

---

## Verification

```bash
# Check pod status
kubectl get pods -n vaultwarden

# Check service
kubectl get svc -n vaultwarden

# Test URL
curl -I https://vault.lab.{{INGRESS_DOMAIN}}
```

---

## Update services.json

```json
{
  "name": "Vaultwarden",
  "url": "vault.lab.{{INGRESS_DOMAIN}}",
  "nodePort": 30095,
  "namespace": "vaultwarden",
  "category": "security"
}
```

---

## Maintenance

### Backup
```bash
# Backup database
kubectl exec -n vaultwarden deployment/vaultwarden -- sqlite3 /data/db.sqlite3 ".backup /tmp/backup.sql"
kubectl cp -n vaultwarden deployment/vaultwarden:/tmp/backup.sql ./vaultwarden-backup.sql
```

### Update
```bash
kubectl set image -n vaultwarden deployment/vaultwarden vaultwarden=vaultwarden/server:latest
```

---

**Next:** Deploy [VolBack for backups](./02-deploy-volback.md)
