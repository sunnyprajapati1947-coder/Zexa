---
name: etl-workflow-designer
description: Designs a complete ETL workflow diagram and implementation plan for a given data movement scenario. Use when planning how to move and transform data between source and destination systems.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: etl, workflow, design, architecture, data-integration, planning
---

## Overview

Produces a complete, professional ETL/ELT workflow design document and implementation plan for a specific data movement scenario. Includes source profiling questions, connector selection guide, transformation catalog, scheduling strategy, error handling matrix, monitoring, and a design document template with Mermaid diagrams that can be turned into working code.

## When to Use This Skill

- Planning a new data integration or migration project.
- The user describes "move data from A to B" or "build a pipeline that...".
- You need to create a design document before coding (good for alignment with stakeholders).

## Prerequisites

- Clear source(s) and destination(s).
- Rough understanding of data volume, freshness requirements, and SLAs.
- Access to documentation or sample data from the source system.

## Steps

1. **Source profiling** (ask these questions and document answers):
   - What is the source system and access method (API, DB, files, stream)?
   - Volume (rows/day, GB)?
   - Update pattern (append-only, CDC, full refresh)?
   - Schema stability?
   - Authentication / rate limits?

2. **Destination profiling**:
   - Warehouse, lake, app DB, search index, etc.
   - Required freshness (real-time, hourly, daily)?
   - Query patterns (what will consume the data)?

3. **Connector & tool selection**:
   - Batch: Airflow + Python, dbt, Fivetran, Stitch, custom scripts.
   - Streaming: Kafka, Kinesis, Debezium CDC, Spark Structured Streaming.
   - File: AWS Glue, Azure Data Factory, custom.

4. **Transformation catalog**:
   - Filter, map/rename, join/enrich, aggregate, type cast, deduplicate, validate, mask/PII.
   - Document each transform with input → output example.

5. **Error handling matrix**:
   - Transient (retry with backoff).
   - Data quality (quarantine + alert).
   - Schema drift (alert + fallback).
   - Permanent failure (DLQ + manual review).

6. **Scheduling & orchestration**:
   - Cron, event-driven, dependency-based (Airflow DAG).
   - Watermark / incremental logic.
   - Backfill strategy.

7. **Monitoring & SLAs**:
   - Freshness, volume, latency, data quality score.
   - Alerting channels and escalation.

8. **Output**:
   - Design document (Markdown) with:
     - Context & requirements
     - Architecture diagram (Mermaid)
     - Data flow
     - Transformation list
     - Error handling table
     - Implementation phases & timeline
     - Risks & open questions
   - High-level code skeleton or Airflow DAG outline.
   - Next-step recommendations (prototype the extract first).

## Examples

A complete design document for "Ingest Shopify orders + customers into Snowflake daily, with incremental logic, PII masking, and quality checks" including Mermaid architecture diagram, transformation catalog, error matrix, and 4-week implementation plan is included.

## Edge Cases & Error Handling

- **Source downtime**: Backpressure, queueing, or graceful degradation.
- **Schema evolution**: Versioned schemas or automated drift detection.
- **Compliance** (GDPR, HIPAA): Document data lineage and masking strategy.

## Verification

1. The design document is reviewed and approved by stakeholders (data + engineering + business).
2. A small prototype of the critical path (extract → minimal transform → load) succeeds.
3. The Mermaid diagram renders and accurately reflects the planned flow.
4. Error scenarios are covered in the matrix with clear ownership.
5. Success: The team has a clear, shared plan that can be implemented with minimal rework.

## References

- [Data Engineering Lifecycle](https://www.dataengineering.design/)
- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [Mermaid Diagrams](https://mermaid.js.org/)
