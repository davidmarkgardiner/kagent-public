# Downloads

Public examples and sanitized receipts are bundled with this site.
The YAML templates still need rendering and target validation; downloads do not deploy anything.

- [aks/headers.example.json](aks/headers.example.json)
- [aks/incident.json](aks/incident.json)
- [aks/render.py](aks/render.py)
- [aks/smoke.py](aks/smoke.py)
- [aks/templates/01-virtualservice.yaml](aks/templates/01-virtualservice.yaml)
- [aks/templates/02-httproute.yaml](aks/templates/02-httproute.yaml)
- [aks/templates/03-payload-policy.yaml](aks/templates/03-payload-policy.yaml)
- [aks/templates/04-referencegrant.yaml](aks/templates/04-referencegrant.yaml)
- [aks/test_helpers.py](aks/test_helpers.py)
- [aks/values.example.json](aks/values.example.json)
- [downloads/skill/SKILL.md.txt](downloads/skill/SKILL.md.txt)
- [downloads/skill/agents/openai.yaml](downloads/skill/agents/openai.yaml)
- [downloads/skill/assets/starter/docs/index.md.txt](downloads/skill/assets/starter/docs/index.md.txt)
- [downloads/skill/assets/starter/mkdocs.yml](downloads/skill/assets/starter/mkdocs.yml)
- [downloads/skill/assets/starter/requirements.txt](downloads/skill/assets/starter/requirements.txt)
- [poc/a2a-request.json](poc/a2a-request.json)
- [poc/evidence/a2a-pass-through-response.json](poc/evidence/a2a-pass-through-response.json)
- [poc/evidence/agent-executions.log](poc/evidence/agent-executions.log)
- [poc/evidence/cleanup.json](poc/evidence/cleanup.json)
- [poc/evidence/gateway-access.log](poc/evidence/gateway-access.log)
- [poc/evidence/initial-model-network-denial.json](poc/evidence/initial-model-network-denial.json)
- [poc/evidence/model-gateway-access.log](poc/evidence/model-gateway-access.log)
- [poc/evidence/raw-json-response.json](poc/evidence/raw-json-response.json)
- [poc/evidence/replay-result.json](poc/evidence/replay-result.json)
- [poc/evidence/result.json](poc/evidence/result.json)
- [poc/evidence/server-dry-run.txt](poc/evidence/server-dry-run.txt)
- [poc/incident.json](poc/incident.json)
- [poc/resources.yaml](poc/resources.yaml)
- [poc/run.sh](poc/run.sh)
- [poc/verify.py](poc/verify.py)
- [reference/istio-virtualservice.yaml](reference/istio-virtualservice.yaml)
- [reference/kagent-a2a-invoke.sh](reference/kagent-a2a-invoke.sh)
- [reference/route-a2a-fleet-agent.yaml](reference/route-a2a-fleet-agent.yaml)
- [reference/service-a2a-fleet-agent.yaml](reference/service-a2a-fleet-agent.yaml)

The raw skill entrypoint uses a `.txt` suffix so MkDocs serves the source unchanged.
Remove the final `.txt` from downloaded `.md.txt` filenames when importing, and preserve `agents/` and `assets/` from
the bundled skill downloads. The canonical GitHub skill folder already has the right names.
