# Build Custom Stonebranch UAG Image

Fixes the `/etc/passwd` security alert by pre-baking the runtime user into the image,
so `ua_entrypoint` has nothing to write at startup.

## Prerequisites

- Docker (or Podman) on your work machine
- Access to your work container registry (ACR, Artifactory, etc.)
- `stonebranch/universal-agent:8.0.0.0-debian` pullable from Docker Hub or your mirror

---

## Step 1 — Inspect the base image

Before building, confirm what user `ua_entrypoint` tries to add:

```bash
# See existing users in the base image
docker run --rm --entrypoint cat stonebranch/universal-agent:8.0.0.0-debian /etc/passwd

# Read the entrypoint script to find what it writes
docker run --rm --entrypoint cat stonebranch/universal-agent:8.0.0.0-debian /bin/ua_entrypoint
```

If the username is different from `uaguser`, update the `useradd` line in `Dockerfile` accordingly.

---

## Step 2 — Build the image

```bash
cd stonebranch-poc/custom-image

# Replace YOUR_REGISTRY with e.g. myacr.azurecr.io/stonebranch
docker build -t YOUR_REGISTRY/universal-agent:8.0.0.0-debian-fixed .
```

---

## Step 3 — Verify the user is baked in

```bash
docker run --rm --entrypoint grep YOUR_REGISTRY/universal-agent:8.0.0.0-debian-fixed \
  /etc/passwd -- uaguser
# Should print the uaguser entry — if blank, check the Dockerfile useradd line
```

---

## Step 4 — Push to your registry

```bash
docker push YOUR_REGISTRY/universal-agent:8.0.0.0-debian-fixed
```

For Azure Container Registry:
```bash
az acr login --name YOUR_ACR_NAME
docker tag YOUR_REGISTRY/universal-agent:8.0.0.0-debian-fixed \
  YOUR_ACR_NAME.azurecr.io/stonebranch/universal-agent:8.0.0.0-debian-fixed
docker push YOUR_ACR_NAME.azurecr.io/stonebranch/universal-agent:8.0.0.0-debian-fixed
```

---

## Step 5 — Update the deployment manifest

In `stonebranch-poc/03-uag-agent.yaml`, update both image references:

```yaml
# initContainer
- name: patch-agent-config
  image: YOUR_REGISTRY/universal-agent:8.0.0.0-debian-fixed   # <-- changed

# main container
- name: uag
  image: YOUR_REGISTRY/universal-agent:8.0.0.0-debian-fixed   # <-- changed
```

Also remove the `/etc/passwd` workaround — it is no longer needed:

1. Remove the `cp /etc/passwd /etcdata/passwd` line from the initContainer args
2. Remove the `etc-passwd` volumeMount from the initContainer
3. Remove the `etc-passwd` volumeMount from the main container (`mountPath: /etc/passwd`)
4. Remove the `etc-passwd` volume from the volumes list

---

## Step 6 — Redeploy and verify no alert fires

```bash
kubectl rollout restart deployment/uag-agent -n stonebranch
kubectl rollout status deployment/uag-agent -n stonebranch

# Watch startup logs — should see no passwd errors
kubectl logs -n stonebranch -l app=uag-agent --follow
```

Confirm with your security team that the alert no longer triggers on pod startup.
