#!/bin/bash
# Test IDP webhook endpoints via kubectl run (from inside cluster).
# Usage: ./test-webhook.sh [namespace-create|namespace-delete|app-deploy]
set -euo pipefail

ACTION="${1:-namespace-create}"
SVC="port-webhook-eventsource-svc.argo-events.svc.cluster.local:12000"

case "$ACTION" in
  namespace-create)
    echo "Testing namespace creation..."
    kubectl run -n argo-events test-ns-create --rm -it --restart=Never --image=curlimages/curl -- \
      curl -s -X POST "http://${SVC}/namespace-action" \
      -H "Content-Type: application/json" \
      -d '{
        "action": "create",
        "namespace": "platform-dev-testing",
        "cluster": "homelab",
        "owner": "david@bank.com",
        "team": "platform",
        "environment": "dev",
        "cpu_quota": "4",
        "memory_quota": "8Gi"
      }'
    ;;

  namespace-delete)
    echo "Testing namespace deletion..."
    kubectl run -n argo-events test-ns-delete --rm -it --restart=Never --image=curlimages/curl -- \
      curl -s -X POST "http://${SVC}/namespace-action" \
      -H "Content-Type: application/json" \
      -d '{
        "action": "delete",
        "namespace": "platform-dev-testing",
        "cluster": "homelab",
        "owner": "david@bank.com",
        "team": "platform",
        "environment": "dev"
      }'
    ;;

  app-deploy)
    echo "Testing app deployment..."
    kubectl run -n argo-events test-app-deploy --rm -it --restart=Never --image=curlimages/curl -- \
      curl -s -X POST "http://${SVC}/app-deploy" \
      -H "Content-Type: application/json" \
      -d '{
        "app_name": "podinfo",
        "namespace": "platform-dev-testing",
        "image": "stefanprodan/podinfo:latest",
        "replicas": "2",
        "port": "9898",
        "cpu_request": "100m",
        "memory_request": "128Mi",
        "enable_ingress": "true",
        "enable_hpa": "false"
      }'
    ;;

  *)
    echo "Usage: $0 [namespace-create|namespace-delete|app-deploy]"
    exit 1
    ;;
esac

echo ""
echo "Watch workflows: kubectl get workflows -n argo-events -w"
