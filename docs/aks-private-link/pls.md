I think there may be two different things getting mixed together:

1. **Azure Private Link Service (PLS)**, which exposes a private service over Azure Private Link.
2. **PLS Gateway**, which some people use informally to describe a routing proxy or gateway that sits in front of multiple services. That's **not** an Azure networking construct.

If you're talking about **AKS + Istio + Azure Databricks**, then **Istio should absolutely be handling the SNI/Host-based routing**. You don't need another "PLS gateway" just for hostname routing.

The flow would typically be:

```text
Databricks
     │
Private Endpoint
     │
Azure Private Link
     │
Private Link Service
     │
Azure Internal Load Balancer
     │
Istio Ingress Gateway (Envoy)
     │
SNI / Host Routing
     │
Service
     │
Pods
```

The responsibilities break down like this:

| Component              | Responsibility                                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| Private Endpoint       | Private connectivity from Databricks                                                           |
| Private Link Service   | Publishes your AKS service privately                                                           |
| Internal Load Balancer | Receives the TCP connection                                                                    |
| Istio Gateway (Envoy)  | Terminates TLS (or passes it through), inspects SNI/Host header, routes to the correct backend |

So **SNI routing belongs in Envoy/Istio**, not in Private Link.

---

## When would you need another gateway?

Usually only if you need capabilities **before** traffic reaches Istio, such as:

* Azure WAF
* Azure Front Door (Private Link origin)
* Azure Application Gateway
* An L4 TCP proxy
* DDoS mitigation at the edge

Otherwise, Istio is perfectly capable of:

* Multiple hostnames
* Wildcard certificates
* SNI routing
* Path routing
* JWT authentication
* mTLS
* Traffic splitting

---

## The Databricks question

This is the part I'd like to understand better.

When you say:

> we're trying to connect to Databricks

Do you mean:

**Option A**

```text
Databricks
      │
calls
      │
AKS API
```

where Databricks is the **client** and your application is running in AKS?

Or

**Option B**

```text
User
      │
AKS
      │
calls
      │
Databricks REST APIs
```

where AKS is the client?

Or

**Option C**

You're specifically talking about **Databricks Model Serving / AI Gateway** calling services running in AKS?

The answer changes quite a bit depending on which direction the traffic is flowing.

I suspect you're referring to **Azure Databricks talking privately to an API hosted in AKS**, in which case **Private Link Service + Istio Gateway is exactly the architecture I'd recommend**. Databricks would resolve your API's private FQDN via Private DNS, connect through a Private Endpoint, and Envoy would perform the SNI/Host routing to the correct Kubernetes service. That aligns well with Microsoft's guidance for using Private Link to reach customer-hosted services privately. ([docs.databricks.com][1])

[1]: https://docs.databricks.com/aws/en/security/network/serverless-network-security/pl-to-internal-network?utm_source=chatgpt.com "Configure private connectivity to resources in your VPC | Databricks on AWS"
