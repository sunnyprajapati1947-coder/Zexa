---
name: data-pipeline-builder
description: Designs and implements ETL/ELT data pipelines with error handling, retries, and monitoring. Use when moving data between systems or building a data warehouse ingestion process.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: etl, elt, pipeline, airflow, dbt, data-warehouse, idempotency
---

## Overview

Designs and implements reliable ETL or ELT data pipelines. Covers the decision between ETL vs ELT, pipeline stages (extract, validate, transform, load, notify), idempotency patterns, dead-letter queues, orchestration with Apache Airflow or dbt, error handling and retries, and monitoring/ alerting for data freshness and quality.

## When to Use This Skill

- Ingesting data from APIs, databases, files, or streams into a warehouse or another system.
- Building or refactoring data movement processes.
- The user mentions "data pipeline", "ETL", "ELT", "ingest", "Airflow DAG", or "dbt model".

## Prerequisites

- Source and destination systems identified.
- Orchestrator (Airflow, Dagster, Prefect, or dbt + cron) or simple cron + scripts.
- Access to credentials for sources and destinations.
- Understanding of data volume and freshness requirements.

## Steps

1. **ETL vs ELT decision**:
   - ETL: transform before load (smaller data, complex transforms, regulatory reasons).
   - ELT: load raw, transform in warehouse (modern, scalable, dbt-friendly).

2. **Pipeline stages** (template):
   - Extract: pull from source (API pagination, DB query, file download).
   - Validate: schema, nulls, duplicates, business rules (great expectations or custom).
   - Transform: clean, join, aggregate, enrich.
   - Load: idempotent upsert or append.
   - Notify / quality checks: freshness, row counts, anomaly detection.

3. **Idempotency**:
   - Use natural keys + upsert (MERGE, INSERT ... ON CONFLICT).
   - Watermark / high-water mark for incremental loads.
   - Deduplication keys.

4. **Error handling & retries**:
   - Dead-letter queue or "quarantine" table for bad rows.
   - Retry with exponential backoff + jitter (for transient API/DB errors).
   - Alert on persistent failures.

5. **Orchestration**:
   - Airflow DAG structure (tasks, dependencies, sensors, SLAs).
   - dbt: models, tests, snapshots, macros for incremental logic.

6. **Monitoring**:
   - Data freshness (last successful run time).
   - Volume anomalies.
   - Schema drift detection.

7. **Output**:
   - Pipeline architecture diagram (Mermaid or text).
   - Sample code for extract/validate/load (Python or SQL).
   - Airflow DAG example or dbt project structure.
   - Dead-letter and retry patterns.
   - Alerting rules.

## Examples

A complete incremental ELT pipeline from a REST API (e.g., Stripe or Shopify) into BigQuery or Postgres using Python + dbt, with idempotent load, data quality tests, and an Airflow DAG wrapper is included.

## Edge Cases & Error Handling

- **Late-arriving data**: Use watermark + reprocessing window.
- **Schema changes in source**: Schema evolution strategy (add columns as nullable, alert on breaking changes).
- **Large backfills**: Separate backfill jobs with different resource allocation.

## Verification

1. Run the pipeline end-to-end on a small dataset.
2. Simulate a transient failure — retries succeed.
3. Simulate bad data — it goes to dead-letter, pipeline continues, alert fires.
4. Check that re-running the pipeline with the same source data produces identical results (idempotent).
5. Data freshness dashboard shows the expected last run time.
6. Success: Data arrives reliably, errors are isolated, and the pipeline can be re-run safely.

## References

- [Apache Airflow](https://airflow.apache.org/)
- [dbt](https://www.getdbt.com/)
- [Great Expectations](https://greatexpectations.io/)
- [The Data Engineering Cookbook](https://github.com/andkret/Cookbook)
