# Synthetic inventory service check

This is a lab example, not a production runbook. For the synthetic
`neo4j-memory-lab/demo-inventory` Service, compare Deployment readiness with
the Service's ready EndpointSlice targets. If the Deployment is ready but no
endpoint is ready, investigate Service selectors and Pod readiness with
read-only Kubernetes tools. Do not infer a network outage from topology alone.
