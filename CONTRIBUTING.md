# Contributing & Public Safety

## Sanitisation Rules

Before committing any file, verify it contains none of the following:

| Category | Replace with |
|---|---|
| API keys, bot tokens, passwords | REMOVE entirely |
| Internal hostnames / FQDNs | `{{INGRESS_DOMAIN}}` |
| Azure subscription IDs (GUIDs) | `{{AZURE_SUBSCRIPTION_ID}}` |
| Internal cluster names | `{{CLUSTER_NAME}}` |
| Resource group names | `{{RESOURCE_GROUP}}` |
| VNet / subnet names | `{{VNET_NAME}}` / `{{SUBNET_NAME}}` |
| Managed identity client IDs | `{{MI_CLIENT_ID}}` |
| Internal email addresses | REMOVE |
| Messaging channel / chat IDs | REMOVE |

## Sanitisation Checklist (run before every PR)

```bash
# 1. Detect secrets
detect-secrets scan --all-files

# 2. Git-aware leak scan
gitleaks detect --no-git -v

# 3. Deep scan
trufflehog filesystem --only-verified=false .

# 4. Internal value sweep — every hit must resolve to a placeholder or be in .secrets.baseline
rg -i '(your-internal-domain|kind-homelab|proxmox-k8s|-100[0-9]{10}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})' \
   --glob '!.git/**'
```

## Placeholder Convention

```yaml
# Good
host: "{{INGRESS_DOMAIN}}"
subscriptionId: "{{AZURE_SUBSCRIPTION_ID}}"

# Bad — real values
host: "kagent.example-internal.com"
subscriptionId: "a1b2c3d4-1234-..."
```

Document all placeholders in the workstream's `README.md` under a **Configuration** section.

## What NOT to commit

- Binary files: `.pdf`, `.pptx`, `.xlsx`, `.zip`
- Local tool state: `.omc/`, `.claude/`, `.codex/`, `.cursor/`, `.vscode/`
- Secret config: `.env*`, `.teller.yml`, `.secrets.baseline`
- Upstream monorepos (reference by URL, not by copy)

## Branch and PR workflow

1. `git checkout -b feat/your-workstream`
2. Run sanitisation checklist
3. Open PR with scan output in description
4. Maintainer reviews and merges
