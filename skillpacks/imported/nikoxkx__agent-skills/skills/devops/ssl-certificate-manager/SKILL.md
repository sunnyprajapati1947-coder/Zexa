---
name: ssl-certificate-manager
description: Manages SSL/TLS certificates including provisioning, renewal, and multi-domain setup. Use when configuring HTTPS for any domain.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: ssl, tls, lets-encrypt, certbot, cert-manager, wildcard, renewal
---

## Overview

Manages the full lifecycle of SSL/TLS certificates: provisioning via Let's Encrypt (HTTP-01 and DNS-01 challenges), wildcard certificates, automated renewal, Kubernetes cert-manager integration, monitoring of expiry, and troubleshooting failed renewals. Includes cron jobs, hooks, and multi-domain (SAN) setups.

## When to Use This Skill

- Adding HTTPS to a domain or subdomain for the first time.
- Setting up wildcard certs (`*.example.com`).
- Automating renewal for many certificates.
- Deploying to Kubernetes.

## Prerequisites

- Domain control (DNS or web server for challenge).
- For DNS challenge: API access to DNS provider (Cloudflare, Route53, etc.).
- Nginx, Caddy, or ingress controller that can use the certificates.

## Steps

1. **Choose challenge type**:
   - HTTP-01: Easy for single domains when you control the web server.
   - DNS-01: Required for wildcards and when you don't want to expose port 80.

2. **Provision with certbot (standalone or webroot)**:
   ```bash
   certbot certonly --nginx -d example.com -d www.example.com
   # or DNS
   certbot certonly --dns-cloudflare -d '*.example.com' -d example.com
   ```

3. **Automated renewal**:
   - certbot renew runs twice a day via systemd timer or cron.
   - Use `--deploy-hook` to reload Nginx or restart services after successful renew.

4. **Kubernetes (cert-manager)**:
   - Install cert-manager.
   - Create Issuer or ClusterIssuer (Let's Encrypt production/staging).
   - Create Certificate resources or use annotations on Ingress.
   - Wildcard via DNS01 solver with Cloudflare or Route53 secret.

5. **Monitoring & alerting**:
   - Check certificate expiry (e.g., with `certbot certificates` or Prometheus blackbox / cert-exporter).
   - Alert when < 30 days remaining.

6. **Multi-domain (SAN)**:
   - List all domains in one certificate when they share the same server.

7. **Output**:
   - Exact certbot commands for the domains.
   - Systemd timer or cron for renewal + deploy hook.
   - cert-manager YAML for Kubernetes.
   - Expiry monitoring script or Prometheus rule.
   - Troubleshooting steps for common renewal failures (rate limits, DNS propagation, webroot path wrong).

## Examples

Full certbot commands for single + wildcard, a production renewal cron with deploy hook that reloads Nginx, and a complete cert-manager setup for a Kubernetes Ingress with wildcard are included.

## Edge Cases & Error Handling

- **Rate limits**: Use staging for testing (`--staging`), respect 50 certs/week per domain for production.
- **DNS propagation**: For DNS-01, wait or use a provider with fast propagation.
- **Certificate not picked up**: Check file permissions and service reload.
- **Revocation**: Have a process to revoke and re-issue if key is compromised.

## Verification

1. `https://example.com` shows a valid certificate (padlock, not self-signed).
2. `certbot certificates` shows the cert and next renewal date.
3. Renewal test: `certbot renew --dry-run` succeeds.
4. In Kubernetes: `kubectl get certificate` shows Ready=True.
5. Expiry alert would fire if the cert were close to expiring.
6. Success: All domains have valid, auto-renewing certificates with >30 days validity at all times.

## References

- [Let's Encrypt](https://letsencrypt.org/)
- [certbot](https://certbot.eff.org/)
- [cert-manager](https://cert-manager.io/)
- [Mozilla SSL Config](https://ssl-config.mozilla.org/)
