# Deploying UAG Agents at Work

## What You Need From the Stonebranch Team

Ask them for two things:

1. **OMS address** — hostname or IP + port (usually 7878)
   - Example: `{{OMS_HOSTNAME}}:7878` or `{{OMS_PRIVATE_IP}}:7878`
   - This is the endpoint their OMS/Controller is listening on
2. **Agent naming convention** — what prefix/pattern they want for your agents
   - Example: `AKS-WORKER1-001`, `TEAM-PLATFORM-001`, etc.
   - Each agent name must be unique across all their agents

Optional — ask if needed:

3. **TLS requirements** — default is self-signed auto-negotiated TLS 1.2. If they require specific certs, you'll need to mount them
4. **Agent cluster assignment** — which UC Agent Cluster your agents should join (they can also do this from their side after agents register)
5. **Network path** — confirm your AKS worker cluster can reach their OMS endpoint on the specified port (check firewalls, NSGs, VNet peering, Private Link)

## Deploy

For repeatable promotion across dev, test, and production, prefer the Helm chart in `chart/` over the one-off shell script. The shell script is still useful for local POC work, but Helm gives you a versioned release, environment-specific values, and a smoke-test hook.

```bash
cd stonebranch-poc

helm upgrade --install stonebranch-test ./chart \
  --namespace stonebranch-test \
  --create-namespace \
  -f ./chart/values.yaml \
  -f ./chart/values-test.yaml \
  --wait \
  --timeout 5m

helm test stonebranch-test --namespace stonebranch-test --logs --timeout 5m
```

See `HELM-PROMOTION.md` for the values model, promotion flow, and smoke-test contract.

For direct POC deployment without Helm:

```bash
cd stonebranch-poc

# Replace with values from the Stonebranch team
OMS_ADDRESS="{{OMS_HOSTNAME}}"   # ← from them
AGENT_PREFIX="AKS-PLATFORM"              # ← agreed naming
REPLICAS=2                                # ← your choice
CLUSTER_CONTEXT="aks-worker1"            # ← your AKS context

./deploy-remote-agents.sh "${CLUSTER_CONTEXT}" "${OMS_ADDRESS}" "${REPLICAS}" "${AGENT_PREFIX}"
```

## Verify

```bash
# Check agents are running
kubectl --context aks-worker1 -n stonebranch get pods

# Check agents connected to OMS (look for "Transport connected")
kubectl --context aks-worker1 -n stonebranch logs deploy/uag-agent -c uag | grep "Transport connected"

# Check init container patched config correctly
kubectl --context aks-worker1 -n stonebranch logs deploy/uag-agent -c patch-agent-config
```

Once connected, the agents will appear in the Stonebranch team's Universal Controller dashboard. They handle job assignment, scheduling, and monitoring from there.

## Network Requirements

Your AKS cluster needs **outbound TCP** to their OMS on port 7878 (or whatever port they specify). No inbound ports needed on your side.

```
Your AKS cluster                    Their infrastructure
┌─────────────────┐                 ┌──────────────────┐
│ UAG agents      │── outbound ───→ │ OMS (port 7878)  │
│ (port 7887 local│   TCP/TLS      │ Universal Controller
│  only)          │                 └──────────────────┘
└─────────────────┘

Firewall/NSG: allow egress to OMS_ADDRESS:7878
```

If they're in a different VNet, you'll need one of:
- VNet peering
- Private Link / Private Endpoint
- Istio Gateway with TLS passthrough (see `06-istio-gateway.yaml`)

## Teardown

```bash
./teardown.sh aks-worker1
```

## Checklist

- [ ] Get OMS address from Stonebranch team
- [ ] Get agent naming convention
- [ ] Confirm network path (can you reach OMS:7878?)
- [ ] Run `deploy-remote-agents.sh`
- [ ] Verify "Transport connected" in agent logs
- [ ] Confirm agents visible in their UC dashboard
- [ ] Done — they manage scheduling from their side
