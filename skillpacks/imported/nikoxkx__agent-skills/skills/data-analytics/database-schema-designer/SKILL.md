---
name: database-schema-designer
description: Designs normalized relational database schemas with proper constraints, indexes, and relationships. Use when modeling data for a new application or refactoring an existing schema.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: database, schema, normalization, sql, postgres, indexes, erd
---

## Overview

Designs well-normalized relational database schemas (target 3NF with pragmatic denormalization where justified). Covers naming conventions, primary key strategies (UUID vs serial/bigserial), foreign keys with cascade options, index design, soft delete pattern, audit columns, and generation of ER diagrams from SQL.

## When to Use This Skill

- Designing the data model for a new application or feature.
- Refactoring a messy or performance-problematic schema.
- The user provides business requirements or an existing schema to improve.

## Prerequisites

- Understanding of the domain and entities/relationships.
- Chosen database (PostgreSQL strongly recommended for new projects; MySQL/SQLite also supported).
- Tool for ERD generation (dbdiagram.io, draw.io, or `schemaspy` / `pgadmin`).

## Steps

1. **Identify entities and relationships**:
   - List all nouns that need to be stored.
   - Define relationships (one-to-many, many-to-many, one-to-one).

2. **Normalization**:
   - 1NF: atomic values, no repeating groups.
   - 2NF: no partial dependency on composite PK.
   - 3NF: no transitive dependencies.
   - Note when to denormalize (read-heavy reporting tables, materialized views).

3. **Naming & conventions**:
   - Tables: plural snake_case (`users`, `order_items`).
   - Columns: snake_case, consistent (`created_at`, `updated_at`).
   - Primary keys: `id` (bigserial or uuid).
   - Foreign keys: `user_id`, `order_id`.

4. **Keys & constraints**:
   - Primary key.
   - Foreign keys with `ON DELETE` / `ON UPDATE` (RESTRICT, CASCADE, SET NULL — choose deliberately).
   - Unique constraints.
   - Check constraints for business rules (e.g., `price > 0`).
   - Not null where appropriate.

5. **Indexes**:
   - B-tree on foreign keys (almost always).
   - Composite on common filter + sort combinations.
   - Partial indexes for common subsets.
   - GIN for JSONB, full-text, arrays when needed.

6. **Patterns**:
   - Soft delete (`deleted_at` + `is_deleted` generated column or partial unique indexes).
   - Audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`).
   - JSONB for flexible attributes (with GIN index).

7. **Output**:
   - Complete `CREATE TABLE` statements (Postgres syntax, adaptable).
   - Index creation statements.
   - ERD (Mermaid or dbdiagram.io syntax).
   - Migration notes (how to apply without downtime).

## Examples

A complete e-commerce schema (users, products, orders, order_items, reviews, inventory) with proper normalization, indexes, soft deletes, audit columns, and a Mermaid ERD is included, plus a denormalized reporting table example with justification.

## Edge Cases & Error Handling

- **Polymorphic associations**: Use a join table or separate tables per type instead of a single foreign key + type column when possible.
- **High cardinality**: Careful with indexes on very high-cardinality columns.
- **Sharding / partitioning**: Note when a table will need to be partitioned by date or tenant.

## Verification

1. All `CREATE TABLE` statements run cleanly on a fresh database.
2. Foreign key constraints prevent invalid data.
3. Common queries have efficient plans (EXPLAIN shows index usage).
4. ERD matches the SQL.
5. Soft delete and audit columns are present where expected.
6. Success: Schema is normalized, constraints protect data integrity, and common access patterns are fast.

## References

- [PostgreSQL Data Types](https://www.postgresql.org/docs/current/datatype.html)
- [Database Normalization](https://en.wikipedia.org/wiki/Database_normalization)
- [Use The Index, Luke - Indexing](https://use-the-index-luke.com/sql/where-clause)
- [dbdiagram.io](https://dbdiagram.io/)
- [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
