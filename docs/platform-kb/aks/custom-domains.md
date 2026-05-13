# Bring Your Own Domain on the Shared AKS Platform

## Summary

Bring your own domain by creating a DNS record that points to the platform ingress endpoint, then binding the host to the approved ingress resource for your namespace. The platform team owns the public ingress controller and certificate automation.

## Steps

1. Request the namespace ingress hostname and public endpoint from the platform team or the self-service portal.
2. Create a `CNAME` record for an application host such as `app.example.com` that targets the platform ingress hostname.
3. Add the host to the application's `Ingress` or `HTTPRoute`, keeping the namespace and service name scoped to your team.
4. Use cert-manager or the platform certificate issuer annotation to request TLS for the custom host.
5. Wait for DNS propagation and certificate readiness before moving traffic.
6. Validate with `curl -I https://app.example.com` and confirm the expected service responds.

## Guardrails

Do not point apex records directly at transient load balancer IPs. Use the documented ingress hostname, keep TLS enabled, and avoid sharing one hostname across namespaces unless the platform team approves the routing model.

## Related source links

- AKS app routing add-on: https://learn.microsoft.com/azure/aks/app-routing
- Kubernetes Ingress: https://kubernetes.io/docs/concepts/services-networking/ingress/

