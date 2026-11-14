---
name: load-balancer-config
description: Configures load balancers for high availability, health checking, and traffic distribution. Use when distributing traffic across multiple backend instances.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: load-balancer, ha, health-checks, sticky-sessions, blue-green, canary, aws-alb, haproxy, nginx
---

## Overview

Configures load balancers (AWS ALB/NLB, Nginx, HAProxy) for high availability with proper health checks, traffic distribution algorithms (round-robin, least connections, ip-hash), sticky sessions when needed, SSL termination, connection draining, and advanced traffic splitting (blue-green, canary, A/B).

## When to Use This Skill

- Running multiple instances of an app behind a load balancer.
- Implementing zero-downtime deploys or canary releases.
- Adding high availability or geographic distribution.

## Prerequisites

- Multiple backend instances (or containers/pods) of the same app.
- Health check endpoint on the app (`/health` or `/ready`).
- DNS or cloud load balancer service.

## Steps

1. **Choose LB type**:
   - Layer 7 (ALB, Nginx, HAProxy) for HTTP features (path routing, headers, canary).
   - Layer 4 (NLB, HAProxy TCP) for raw TCP/UDP or when you need extreme performance.

2. **Health checks**:
   - Path, interval, timeout, healthy/unhealthy thresholds.
   - Separate liveness vs readiness if using Kubernetes.
   - Use a dedicated lightweight endpoint that checks critical dependencies (DB, cache) or a simpler one.

3. **Algorithms**:
   - Round robin (default, even distribution).
   - Least connections (good for long-lived connections).
   - IP hash / source IP (for sticky sessions when state is local).

4. **Sticky sessions** (when unavoidable):
   - Cookie-based (preferred) or source IP.
   - Document why sticky is needed and plan to remove it.

5. **SSL termination**:
   - Terminate at LB (recommended) — backends can stay on HTTP.
   - Or pass-through (rare).

6. **Connection draining / deregistration**:
   - Deregistration delay (AWS) or slow start / drain timeout.
   - Essential for zero-downtime deploys.

7. **Traffic splitting**:
   - Blue-green: two target groups, switch listener rule or DNS.
   - Canary: weighted target groups (ALB, Nginx, HAProxy, or service mesh).
   - Header or cookie based routing for A/B.

8. **Output**:
   - Config for the chosen LB (ALB listener + target group Terraform, Nginx upstream + server block, HAProxy frontend/backend).
   - Health check endpoint recommendation for the app.
   - Blue-green and canary deployment scripts or Terraform.
   - Monitoring (LB 5xx, latency, healthy host count).

## Examples

AWS ALB Terraform for a blue-green setup, an Nginx config with least-conn and sticky cookie, an HAProxy example with canary weighting, and health check implementation guidance are included.

## Edge Cases & Error Handling

- **All backends unhealthy**: LB should return 503 or a maintenance page. Configure a fallback.
- **Session affinity breaking deploys**: Use cookie-based affinity with proper drain.
- **gRPC / WebSocket**: Ensure the LB supports the protocol (ALB supports gRPC, Nginx needs special config).

## Verification

1. Deploy multiple backends.
2. Send traffic — it is distributed (check logs or metrics on each backend).
3. Kill one backend — health check removes it, traffic continues on the others.
4. Perform a blue-green or canary deploy — no or minimal user impact.
5. Success: Traffic is balanced, unhealthy instances are automatically removed, and advanced deployment strategies work without downtime.

## References

- [AWS ALB Documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [Nginx Upstream](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)
- [HAProxy](https://www.haproxy.org/)
- [Blue-Green Deployments](https://martinfowler.com/bliki/BlueGreenDeployment.html)
