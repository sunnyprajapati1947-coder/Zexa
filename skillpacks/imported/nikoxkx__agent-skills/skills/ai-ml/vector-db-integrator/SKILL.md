---
name: vector-db-integrator
description: Integrates a vector database (Pinecone, Qdrant, Chroma, Weaviate, pgvector) into an application for semantic search or similarity queries. Use when adding vector search to any project.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: vector-db, pinecone, qdrant, chroma, weaviate, pgvector, semantic-search
---

## Overview

Provides complete integration code and guidance for the major vector databases. Covers selection criteria (hosted vs self-hosted, scale, cost, features), index/collection creation, metadata filtering, upsert and query patterns, namespace design, hybrid search, backup, and production-ready client code for Pinecone, Qdrant, Chroma, Weaviate, and pgvector.

## When to Use This Skill

- Adding semantic search, recommendations, or RAG to an application.
- Choosing or switching vector databases.
- The user mentions a specific vector DB or needs help with the integration layer.

## Prerequisites

- Embedding model chosen and accessible.
- Text (or other) data to vectorize.
- Chosen vector DB (or decision still open — the skill helps compare).

## Steps

1. **DB selection guide**:
   - Chroma: great for local/dev and small-medium production.
   - pgvector: if you already have Postgres and want everything in one DB.
   - Qdrant / Weaviate: strong self-hosted or managed options, good filtering and hybrid.
   - Pinecone: fully managed, serverless, excellent for large scale and low ops burden.

2. **Schema / collection design**:
   - Dimension (must match embedding model).
   - Distance metric.
   - Metadata schema (what will you filter on?).
   - Namespaces or collections for multi-tenancy or data partitioning.

3. **Client setup & connection**:
   - API keys / connection strings.
   - Async vs sync clients where available.

4. **Upsert pattern** (idempotent):
   - Stable IDs.
   - Batch upserts (hundreds to thousands at a time).
   - Include metadata and (optionally) the original text for reranking or display.

5. **Query pattern**:
   - Embed the query.
   - Query with top_k, filter, include_metadata.
   - Hybrid search (vector + sparse/keyword) when supported.
   - Post-retrieval reranking (optional but powerful).

6. **Production concerns**:
   - Backup / snapshots.
   - Monitoring (index size, query latency, error rate).
   - Multi-tenancy (namespaces, partitions, or separate collections).
   - Cost control (for hosted services).

7. **Output**:
   - Comparison table of the top 5 DBs.
   - Complete, copy-pasteable client code for the top 3 (upsert + filtered query + hybrid if available).
   - Collection/index creation script.
   - Example of metadata filtering.
   - Deployment / connection string notes.

## Examples

Full integration modules for:
- Pinecone (serverless index, metadata filtering, hybrid).
- Qdrant (self-hosted or cloud, payload filtering, hybrid).
- pgvector (in existing Postgres, HNSW index, metadata via JSONB).
With a shared embedding + query interface so swapping DBs is easy.

## Edge Cases & Error Handling

- **Dimension mismatch**: Fail fast with clear error.
- **Rate limits / quotas** (Pinecone, etc.): Implement backoff and batch sizing.
- **Multi-tenancy leakage**: Always filter by tenant ID on every query.
- **Stale data**: Version vectors or use timestamps in metadata + filter.

## Verification

1. Create the index/collection.
2. Upsert a small test set — vectors are queryable.
3. Semantic queries return expected similar items.
4. Metadata filters work correctly (e.g., only 2024 documents).
5. Hybrid search (if used) improves relevance over pure vector.
6. The client code handles errors and retries gracefully.
7. Success: Vector search is reliably integrated and performs well at the expected scale.

## References

- [Pinecone](https://www.pinecone.io/)
- [Qdrant](https://qdrant.tech/)
- [Chroma](https://www.trychroma.com/)
- [Weaviate](https://weaviate.io/)
- [pgvector](https://github.com/pgvector/pgvector)
- [Vector DB Comparison](https://supabase.com/docs/guides/ai/vectordbs)
