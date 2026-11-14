---
name: embeddings-builder
description: Creates, stores, and queries text embeddings for semantic search, clustering, or similarity. Use when building semantic search, recommendation systems, or clustering text data.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: embeddings, vector-search, semantic-search, similarity, clustering, openai, voyage, local-models
---

## Overview

Builds production-grade text embedding pipelines: model selection (OpenAI, Cohere, Voyage, BGE, Snowflake, etc.), batch embedding, normalization, vector database upsert/query patterns, metadata filtering, approximate nearest neighbor tradeoffs, dimensionality reduction for visualization, and complete semantic search examples.

## When to Use This Skill

- Adding semantic search to a product (docs, products, messages, code).
- Building recommendation or duplicate detection systems.
- Clustering or topic modeling text data.
- The user says "semantic search", "find similar", "embeddings", or "vector search".

## Prerequisites

- Text data to embed.
- Embedding model API key or local model (sentence-transformers, etc.).
- Vector database (Chroma, Qdrant, Pinecone, Weaviate, pgvector, Milvus).

## Steps

1. **Model selection**:
   - Quality vs cost vs latency vs max tokens vs language support.
   - Hosted (OpenAI text-embedding-3-large, Voyage, Cohere) vs self-hosted (BGE, Snowflake Arctic, UAE-Large).
   - Benchmark on your domain if possible (MTEB leaderboard is a starting point).

2. **Batch embedding**:
   - Always batch (100-500 texts per call depending on model).
   - Handle rate limits and retries.
   - Normalize embeddings to unit length if the DB or similarity metric requires it (most cosine-based do).

3. **Vector DB setup**:
   - Create collection/index with dimension matching the model.
   - Choose distance metric (cosine, dot product, Euclidean).
   - Design metadata schema (filterable fields: date, source, category, user_id, etc.).

4. **Upsert pattern**:
   - Generate stable IDs (hash of content + metadata or use your own IDs).
   - Upsert in batches with metadata.
   - Handle updates/deletes (delete old vector, insert new).

5. **Query / search**:
   - Embed the query with the **same** model.
   - Top-k + metadata filters.
   - Hybrid search when supported (vector + keyword).
   - Rerank top results with a cross-encoder for better precision.

6. **Dimensionality reduction & visualization** (optional):
   - UMAP or t-SNE on a sample for exploration.
   - Plotly or matplotlib for 2D/3D scatter with labels.

7. **Output**:
   - Embedding function (with batching + retry).
   - Vector DB client code for upsert and query (examples for top 2-3 DBs).
   - Semantic search demo script.
   - Normalization and ID strategy notes.
   - Cost/latency estimates for your data volume.

## Examples

Complete code for:
- Embedding a corpus of documents with Voyage-2 or OpenAI text-embedding-3-small.
- Upserting to Qdrant and pgvector with rich metadata.
- Performing filtered semantic search.
- A small UMAP visualization of the embedding space.
All runnable and with comments.

## Edge Cases & Error Handling

- **Very long documents**: Chunk first (see RAG skill), embed chunks, then aggregate or search at chunk level.
- **Multilingual**: Choose a multilingual model or separate indexes per language.
- **Embedding drift**: Re-embed on model upgrades; keep old embeddings for comparison or re-index.

## Verification

1. Embed a small set — vectors have the expected dimension and are normalized (if required).
2. Semantic search for a query returns intuitively similar items (manual inspection).
3. Metadata filters work (e.g., only results from 2024).
4. Update a document — old vector is replaced, new search reflects the change.
5. Visualization (if done) shows reasonable clusters.
6. Success: Semantic search returns relevant results with good precision, and the pipeline scales to the target corpus size.

## References

- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Voyage AI](https://www.voyageai.com/)
- [Qdrant](https://qdrant.tech/)
- [pgvector](https://github.com/pgvector/pgvector)
- [Sentence Transformers](https://www.sbert.net/)
- [UMAP](https://umap-learn.readthedocs.io/)
