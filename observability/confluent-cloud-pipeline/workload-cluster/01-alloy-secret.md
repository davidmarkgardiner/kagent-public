# Alloy Confluent Secret

Create this on the `{{WORKLOAD_KUBE_CONTEXT}}` workload cluster from the local bootstrap file:

```bash
source confluent.io/.bootstrap.env

kubectl --context {{WORKLOAD_KUBE_CONTEXT}} -n monitoring create secret generic alloy-confluent \
  --from-literal=bootstrap="$CONFLUENT_BOOTSTRAP" \
  --from-literal=topic="$CONFLUENT_K8S_TOPIC" \
  --from-literal=key="$CONFLUENT_SA_KEY" \
  --from-literal=secret="$CONFLUENT_SA_SECRET" \
  --dry-run=client -o yaml | kubectl --context {{WORKLOAD_KUBE_CONTEXT}} apply -f -
```

Do not commit the rendered Secret.
