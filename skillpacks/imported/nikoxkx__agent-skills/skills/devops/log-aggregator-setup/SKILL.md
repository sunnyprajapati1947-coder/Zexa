---
name: log-aggregator-setup
description: Sets up centralized log aggregation with structured logging, log levels, and alerting. Use when implementing observability in production systems.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: logging, observability, elk, loki, grafana, structured-logging, fluentd
---

## Overview

Establishes centralized, structured logging for production systems. Covers JSON log format, log level guidelines, shipping options (Fluentd, Promtail, Vector, Filebeat), storage backends (ELK, Loki + Grafana, CloudWatch, Datadog), retention policies, and basic alerting on error rate or anomaly patterns. Includes code examples for Node.js, Python, and Go.

## When to Use This Skill

- Moving from local file logs or `console.log` to a proper observability stack.
- Debugging production issues that require historical logs.
- Meeting compliance or audit requirements.

## Prerequisites

- Applications that can emit structured logs.
- A logging backend (self-hosted or SaaS).
- Network access from apps to the log shipper/collector.

## Steps

1. **Adopt structured logging**:
   - Use a library that outputs JSON (pino for Node, structlog or logging with json formatter for Python, zap for Go).
   - Include standard fields: `timestamp`, `level`, `message`, `service`, `trace_id`, `user_id` (when available), `error`.

2. **Log level policy**:
   - ERROR: Something broke, needs attention.
   - WARN: Degraded but recovered.
   - INFO: Normal business events.
   - DEBUG: Detailed for local/dev only (never in prod by default).

3. **Choose shipping architecture**:
   - Sidecar / DaemonSet (Promtail for Loki, Fluent Bit).
   - Direct from app (for cloud providers).
   - Agent on host.

4. **Storage & query**:
   - Loki + Grafana (lightweight, labels + LogQL).
   - ELK (full text search, Kibana).
   - Cloud native (CloudWatch Logs, GCP Logging).

5. **Retention & cost**:
   - Hot/warm/cold tiers.
   - 30-90 days hot, longer in cold storage or S3.

6. **Alerting**:
   - High error rate (>1% or threshold).
   - Sudden spike in logs (possible loop).
   - Specific error strings (e.g., "OutOfMemory").

7. **Output**:
   - Structured logger config for 2-3 languages.
   - Docker / Kubernetes log shipping config (Promtail example).
   - Basic Grafana dashboard for logs + error rate.
   - Retention and alert rule examples.

## Examples

Pino logger setup for Node, structlog for Python, Promtail config for Kubernetes, and a simple Loki alert rule are included.

## Edge Cases & Error Handling

- **High cardinality labels**: Avoid putting user IDs or request IDs in labels in Loki (use in message or indexed fields carefully).
- **Sensitive data**: Never log passwords, tokens, PII. Use log redaction middleware.
- **Log volume explosion**: Sample debug logs in prod or use dynamic levels.

## Verification

1. Deploy the logger + shipper.
2. Generate traffic and errors.
3. Query logs in the backend by service, level, trace_id.
4. Confirm an alert fires on injected errors.
5. Success: All services emit consistent JSON logs, they are queryable centrally, and critical errors are alerted.

## References

- [Pino](https://github.com/pinojs/pino)
- [Loki + Promtail](https://grafana.com/docs/loki/latest/)
- [Fluent Bit](https://fluentbit.io/)
- [Structured Logging](https://www.structlog.org/en/stable/)
