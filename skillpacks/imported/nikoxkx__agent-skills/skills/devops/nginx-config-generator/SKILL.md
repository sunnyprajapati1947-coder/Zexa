---
name: nginx-config-generator
description: Generates Nginx configurations for reverse proxying, load balancing, SSL termination, and static file serving. Use when configuring Nginx for a web server or API gateway.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: nginx, reverse-proxy, ssl, load-balancing, security-headers, gzip
---

## Overview

Produces hardened, production-ready Nginx server blocks for common use cases: reverse proxy to backend apps, load balancing across multiple upstreams, SSL termination with Let's Encrypt, static file serving with caching, gzip, rate limiting, and a full set of security headers (HSTS, CSP, X-Frame-Options, etc.).

## When to Use This Skill

- Setting up or replacing a reverse proxy / load balancer.
- Configuring Nginx in front of Node.js, Python, Go, or other app servers.
- Adding HTTPS or improving security headers.

## Prerequisites

- Nginx installed (or in Docker).
- Domain name and ability to point DNS.
- For Let's Encrypt: certbot or cert-manager.

## Steps

1. **Basic server block structure**:
   - `listen 80` + redirect to HTTPS.
   - `listen 443 ssl http2`.
   - `server_name`.
   - Root or proxy_pass.

2. **Upstream definition** for load balancing or multiple backends.

3. **SSL/TLS**:
   - Modern cipher suite.
   - OCSP stapling.
   - Let's Encrypt paths (`/etc/letsencrypt`).

4. **Proxy settings**:
   - `proxy_pass http://backend;`
   - `proxy_set_header` for X-Forwarded-*, Host, etc.
   - Timeouts and buffering.

5. **Performance**:
   - gzip on.
   - Static file caching headers (immutable for hashed assets).
   - `sendfile`, `tcp_nopush`.

6. **Security headers** (include a reusable snippet):
   - Strict-Transport-Security.
   - Content-Security-Policy (start restrictive).
   - X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.

7. **Rate limiting**:
   - `limit_req_zone`.
   - Different zones for login vs general.

8. **Output**:
   - Complete `/etc/nginx/sites-available/example.com.conf`.
   - Symlink instructions.
   - `nginx -t` and reload commands.
   - certbot command for SSL.
   - Testing with `curl -I`.

## Examples

A full reverse proxy config for a Next.js app on port 3000 with SSL, security headers, gzip, rate limiting, and static asset caching is included, plus a load-balanced upstream example.

## Edge Cases & Error Handling

- **Websockets**: Add `proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade;` etc.
- **Large uploads**: Increase `client_max_body_size`.
- **Maintenance mode**: Provide a config snippet that returns 503 with a nice page.

## Verification

1. `nginx -t` — config is valid.
2. `curl -I https://example.com` — correct headers, 200 or 301.
3. `curl -I https://example.com/_next/static/...` — long cache headers.
4. Test rate limiting by sending many requests.
5. SSL Labs test (A+ rating target).
6. Success: Traffic is proxied correctly, HTTPS works, headers are secure, performance features are active.

## References

- [Nginx Docs](https://nginx.org/en/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Nginx Security Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)
- [certbot](https://certbot.eff.org/)
