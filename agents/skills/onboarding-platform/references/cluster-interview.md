# Cluster Onboarding Interview

Use this flow for AKS cluster requests.

## Fields

Collect:

| Field | Rule | Default |
| --- | --- | --- |
| `clusterName` | `^[a-z][a-z0-9-]{2,30}$` | none |
| `region` | `uksouth`, `ukwest`, `westeurope`, `northeurope` | `westeurope` |
| `size` | `small`, `medium`, `large` | `small` |
| `dryRun` | `true` or `false` | `true` |
| `confirmedBy` | requester name or email | `demo-user` |

## Interview

Ask:

1. What should the cluster be called?
2. Which Azure region should it use?
3. What size should it be?
4. Who should be recorded as the requester?

Normalize the cluster name only when the intended value is obvious, then ask for confirmation.

## Confirmation

For dry-run requests, require the exact phrase:

```text
yes, provision
```

For real provisioning, require the exact phrase:

```text
yes, provision real cluster
```

Only allow real provisioning if the user explicitly states they are an authorized platform operator.

## Workflow

Submit a Workflow in namespace `argo` with:

```yaml
spec:
  workflowTemplateRef:
    name: provision-aks-cluster
  arguments:
    parameters:
      - name: clusterName
      - name: region
      - name: size
      - name: dryRun
      - name: confirmedBy
```

Do not create or change the WorkflowTemplate.
