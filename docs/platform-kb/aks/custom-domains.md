# Bring Your Own Domain on the Shared AKS Platform

## Summary

Bring your own domain by pointing DNS at the approved platform ingress endpoint, then binding the host to an approved `Ingress` or `HTTPRoute` in the application namespace. The platform team owns the public ingress controller and certificate automation.

## Steps

1. Request the namespace ingress hostname and routing pattern from the platform team or self-service portal.
2. Create a `CNAME` record for the application host, such as `app.example.com`, that targets the platform ingress hostname.
3. Add the host to the application `Ingress` or `HTTPRoute`.
4. Keep the route scoped to the application namespace and service.
5. Use the approved platform certificate issuer or certificate automation annotation.
6. Wait for DNS propagation and certificate readiness.
7. Validate with `curl -I https://app.example.com` and confirm the expected service responds.

## Guardrails

Do not point apex records directly at transient load balancer IPs. Use the documented ingress hostname. Keep TLS enabled. Do not share one hostname across namespaces unless the platform team approves the routing model.

## Troubleshooting

If the host resolves but traffic does not reach the service, check:

- DNS target is the platform ingress hostname.
- Hostname in the route exactly matches the requested domain.
- TLS certificate is ready.
- Backend service name and port match the deployed service.
- Namespace route policy allows the route to attach.

## Related References

- AKS app routing add-on: https://learn.microsoft.com/azure/aks/app-routing
- Kubernetes Ingress: https://kubernetes.io/docs/concepts/services-networking/ingress/
- Kubernetes Gateway API: https://gateway-api.sigs.k8s.io/

