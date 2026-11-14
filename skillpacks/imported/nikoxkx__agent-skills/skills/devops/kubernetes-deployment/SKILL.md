---
name: kubernetes-deployment
description: Creates Kubernetes manifests for deploying containerized applications with scaling, health checks, and resource limits. Use when deploying to any Kubernetes cluster (GKE, EKS, AKS, local).
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: kubernetes, k8s, deployment, helm, manifests, autoscaling
---

## Overview

Produces complete, production-grade Kubernetes manifests (Deployment, Service, Ingress, ConfigMap, Secret, HorizontalPodAutoscaler, PodDisruptionBudget) with proper resource requests/limits, liveness/readiness probes, rolling update strategy, securityContext (non-root), and a basic Helm chart structure or Kustomize overlay for environment-specific configuration.

## When to Use This Skill

- Deploying a containerized app to Kubernetes for the first time or improving an existing deployment.
- User mentions "Kubernetes", "k8s", "deploy to cluster", "EKS", "GKE", "AKS", or "Helm".

## Prerequisites

- A container image (built and pushed to a registry).
- Access to a Kubernetes cluster (kubectl configured).
- Domain and TLS certificate management (cert-manager recommended).

## Steps

1. **Core objects**:
   - Deployment with replicas, strategy (RollingUpdate), resources, probes, securityContext.
   - Service (ClusterIP or LoadBalancer).
   - Ingress (with TLS).

2. **Configuration**:
   - ConfigMap for non-sensitive config.
   - Secret for sensitive data (or external-secrets operator).

3. **Autoscaling & resilience**:
   - HorizontalPodAutoscaler (CPU + memory or custom metrics).
   - PodDisruptionBudget.
   - Pod anti-affinity for high availability.

4. **Probes**:
   - livenessProbe (restart if unhealthy).
   - readinessProbe (remove from service if not ready).
   - startupProbe for slow-starting apps.

5. **Security**:
   - Run as non-root user.
   - Read-only root filesystem where possible.
   - Drop all capabilities.
   - NetworkPolicy (deny all by default, allow only needed).

6. **Output**:
   - All YAML manifests in a `k8s/` or `manifests/` folder.
   - Basic `values.yaml` for Helm if appropriate.
   - `kubectl apply` order and commands.
   - Verification steps (`kubectl get`, port-forward, logs).

## Examples

Full set of manifests for a typical web app (Deployment + Service + Ingress + HPA + ConfigMap + Secret example) with comments and a simple Helm chart skeleton are included.

## Edge Cases & Error Handling

- **Image pull secrets**: For private registries.
- **Zero-downtime deploys**: Use maxSurge/maxUnavailable and proper probes.
- **Stateful apps**: Recommend StatefulSet + persistent volumes instead of Deployment.

## Verification

1. `kubectl apply -f k8s/` succeeds.
2. `kubectl get pods` — all Running and Ready.
3. `kubectl get hpa` — scaling works when load is applied.
4. App is reachable via Ingress.
5. Rolling update completes without downtime.
6. Success: App runs reliably, scales, self-heals, and follows security best practices.

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes Best Practices (book)](https://www.oreilly.com/library/view/kubernetes-best-practices/9781492056461/)
- [cert-manager](https://cert-manager.io/)
- [Helm](https://helm.sh/)
