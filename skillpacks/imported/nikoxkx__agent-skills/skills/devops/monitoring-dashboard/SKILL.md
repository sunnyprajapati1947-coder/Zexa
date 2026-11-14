---
name: monitoring-dashboard
description: Creates monitoring dashboards and alerting rules for production services. Use when setting up observability with Prometheus, Grafana, Datadog, or similar.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: monitoring, prometheus, grafana, observability, alerting, slos
---

## Overview

Builds production monitoring stacks centered on the four golden signals (latency, traffic, errors, saturation). Includes Prometheus scrape config, useful PromQL queries, Grafana dashboard JSON or Terraform, alert rules with runbook links, SLO/SLI definitions, and on-call best practices.

## When to Use This Skill

- Adding observability to a new or existing service.
- Replacing or improving existing dashboards that are noisy or missing key signals.
- Defining SLIs/SLOs for a team or product.

## Prerequisites

- Metrics exposed by the application (Prometheus client library, OpenTelemetry, StatsD, etc.).
- Prometheus or compatible scraper running (or Datadog, New Relic, etc.).
- Grafana or equivalent visualization.

## Steps

1. **Define SLIs** (Service Level Indicators) for the service:
   - Availability: successful requests / total.
   - Latency: p95 or p99 of request duration.
   - Error rate.
   - Saturation (CPU, memory, queue depth).

2. **Instrument the code** (if not done):
   - Request duration histogram.
   - Counter for errors by type.
   - Gauges for queue depth, active connections.

3. **Prometheus scrape & recording rules**:
   - Scrape config for the app + node-exporter + cAdvisor (if k8s).
   - Recording rules for common aggregates (e.g., `job:request_duration_seconds:rate5m`).

4. **Grafana dashboard**:
   - One row per golden signal.
   - Heatmaps for latency distribution.
   - Error budget burn rate.
   - Top endpoints by latency/error.

5. **Alerting rules**:
   - Page on critical (error budget burning fast).
   - Ticket on warning.
   - Always link to a runbook in the alert annotation.

6. **SLOs**:
   - Example: 99.9% availability over 28 days.
   - Error budget calculation and visualization.

7. **Output**:
   - `prometheus.yml` snippet.
   - Recording + alerting rules YAML.
   - Grafana dashboard JSON (importable).
   - Runbook template (markdown).
   - On-call rotation recommendations.

## Examples

A complete set of recording/alerting rules for a typical web service, a Grafana dashboard JSON focused on the four golden signals, and an SLO error budget dashboard are included.

## Edge Cases & Error Handling

- **Noisy alerts**: Use error budget burn rate instead of raw thresholds.
- **Missing metrics**: Provide a checklist of must-have metrics per service type.
- **Multi-tenant / high cardinality**: Careful with label usage.

## Verification

1. Metrics appear in Prometheus.
2. Grafana dashboard loads and shows live data.
3. A test alert fires and creates a ticket with runbook link.
4. Error budget dashboard correctly shows remaining budget.
5. Success: Team has clear visibility into service health and actionable alerts.

## References

- [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana](https://grafana.com/)
- [SLIs, SLOs, SLAs](https://sre.google/sre-book/service-level-objectives/)
