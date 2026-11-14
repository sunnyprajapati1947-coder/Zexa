---
name: sql-query-optimizer
description: Analyzes and optimizes slow SQL queries for PostgreSQL, MySQL, or SQLite. Use when queries are slow, or when building efficient queries from scratch.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: sql, postgres, mysql, optimization, explain, indexes, performance
---

## Overview

Analyzes slow SQL queries using EXPLAIN / EXPLAIN ANALYZE, recommends and implements index strategies (B-tree, partial, composite, covering), detects and fixes N+1 problems, optimizes JOINs, subqueries vs CTEs vs window functions, and provides concrete before/after query rewrites with performance numbers.

## When to Use This Skill

- A query is slow in production or during development.
- Building new reports or features that query the database.
- Reviewing ORM-generated queries that are causing problems.
- Preparing for a database migration or scaling event.

## Prerequisites

- Access to the database (read-only for analysis, or a staging copy for testing).
- The slow query (or the code that generates it).
- `EXPLAIN` support (all major relational DBs).
- For production changes: migration tool (Alembic, Flyway, Prisma, etc.).

## Steps

1. **Capture the slow query**:
   - From logs, APM (pg_stat_statements, slow query log), or application tracing.
   - Get the full query text with parameters.

2. **Run EXPLAIN ANALYZE** (or EXPLAIN on SQLite):
   ```sql
   EXPLAIN ANALYZE SELECT ...;
   ```
   - Look for: Seq Scan on large tables, high cost, many rows removed by filter, Nested Loop with high row counts.

3. **Index strategy**:
   - B-tree for equality and range.
   - Composite indexes in column order of the WHERE/JOIN/ORDER BY.
   - Partial indexes for common filters (e.g., `WHERE status = 'active'`).
   - Covering indexes (INCLUDE in Postgres) to avoid table lookups.

4. **Fix N+1**:
   - Use JOINs or `IN` subquery / lateral join instead of looping in application code.
   - For ORMs: use `select_related` / `prefetch_related` (Django), `includes` / `eager_load` (ActiveRecord), or write a single query.

5. **Rewrite patterns**:
   - Subquery → JOIN or CTE.
   - Correlated subquery → window function or lateral.
   - `SELECT *` → only needed columns.
   - `ORDER BY` without LIMIT on large result sets → paginate or use cursor.

6. **Test the change**:
   - Run EXPLAIN ANALYZE before and after.
   - Run the query with realistic data volume.
   - Check that the new index does not slow down writes unacceptably (measure insert/update time).

7. **Output**:
   - Original query + EXPLAIN.
   - Diagnosis.
   - Optimized query + new EXPLAIN.
   - Index creation statement (with `CONCURRENTLY` for Postgres production).
   - Application code change (if N+1).
   - Monitoring recommendation (add to pg_stat_statements watch list).

## Examples

A classic slow "get recent orders with customer and items" N+1 query, its EXPLAIN, the diagnosis, the rewritten JOIN + covering index version, and the before/after timing (e.g., 2.3s → 12ms) are included, along with similar examples for MySQL and SQLite.

## Edge Cases & Error Handling

- **Write-heavy tables**: Partial or filtered indexes to reduce write overhead.
- **Very large tables**: Partitioning + query that can use partition pruning.
- **Parameter sniffing** (SQL Server) or plan cache issues: use `RECOMPILE` or plan guides when needed.
- **ORM limitations**: Sometimes the best fix is a raw SQL query or a database view.

## Verification

1. New EXPLAIN shows index usage (Index Scan / Index Only Scan instead of Seq Scan).
2. Query time improves by at least 5-10x on realistic data.
3. No increase in write latency after adding the index (measured on staging).
4. Application tests still pass (the optimized query returns identical results).
5. Success: The slow path is fixed, and the query plan is stable and efficient.

## References

- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [Use The Index, Luke](https://use-the-index-luke.com/)
- [MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.0/en/explain.html)
- [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
