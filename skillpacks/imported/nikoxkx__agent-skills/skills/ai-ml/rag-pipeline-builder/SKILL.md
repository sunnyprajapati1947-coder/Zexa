---
name: rag-pipeline-builder
description: Builds a Retrieval-Augmented Generation pipeline with document ingestion, chunking, embedding, vector search, and generation. Use when building a Q&A system over custom documents.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: rag, retrieval, vector, embeddings, langchain, llama-index, chunking
---

## Overview

Builds a complete, production-oriented Retrieval-Augmented Generation (RAG) pipeline. Covers document ingestion, intelligent chunking strategies (fixed, recursive, semantic), embedding model selection, vector database choice and setup, retrieval (top-k, hybrid, reranking), context assembly, generation with hallucination mitigation, and evaluation of the full pipeline.

## When to Use This Skill

- Building a chatbot or Q&A system over company docs, knowledge base, code, or private data.
- The user says "RAG", "chat with my PDFs", "question answering over documents", or provides a corpus.
- Existing simple RAG is producing poor or hallucinated answers.

## Prerequisites

- A collection of documents (PDF, Markdown, HTML, Notion export, etc.).
- Embedding model access (OpenAI, Cohere, Voyage, or local via sentence-transformers).
- Vector database (Chroma for dev, Pinecone/Qdrant/Weaviate/pgvector for prod).
- LLM for generation.

## Steps

1. **Ingestion & preprocessing**:
   - Load documents (LangChain loaders, LlamaIndex readers, or custom).
   - Clean (remove boilerplate, normalize whitespace, extract metadata: source, page, date).

2. **Chunking** (critical for quality):
   - Fixed size (512-1024 tokens) with overlap.
   - Recursive (by paragraph → sentence → token) — best starting point.
   - Semantic chunking (embed sentences, cluster) for higher quality at higher cost.
   - Document-aware (respect headings, tables, code blocks).

3. **Embedding**:
   - Choose model (tradeoff: quality vs cost vs latency vs context length).
   - Batch embed and normalize if required by the vector DB.
   - Store rich metadata with each chunk.

4. **Vector store**:
   - Create collection/index with appropriate distance metric (cosine usually).
   - Upsert with metadata filtering support.

5. **Retrieval**:
   - Top-k (start with 5-10).
   - Hybrid (vector + keyword / BM25) when available.
   - Metadata filters (date range, source, user permissions).
   - Reranking (Cohere Rerank, cross-encoder, or LLM reranker) for better precision.

6. **Context assembly & generation**:
   - Assemble prompt: system instructions + retrieved chunks (with citations) + user question.
   - Instruct the model to only use provided context and to cite sources.
   - Use "If you don't know, say so" guardrails.

7. **Evaluation**:
   - Golden Q&A set (question, ground-truth answer, source docs).
   - Metrics: faithfulness (LLM judge), answer relevance, context relevance, citation accuracy.
   - RAGAS, ARES, or custom eval harness.

8. **Output**:
   - Full pipeline code (Python, using LangChain or LlamaIndex or custom).
   - Chunking + embedding + retrieval + generation functions.
   - Example ingestion script.
   - Evaluation script + sample golden set.
   - Deployment notes (indexing job, query service, caching).

## Examples

A complete end-to-end RAG pipeline over a set of company policy PDFs using recursive chunking, OpenAI embeddings, Chroma (dev) / Qdrant (prod), hybrid retrieval, Cohere rerank, and Claude 3 / GPT-4 generation with source citation and hallucination guardrails is included, along with a RAGAS-style evaluation.

## Edge Cases & Error Handling

- **No relevant context**: Model should say "I don't have information on that in the provided documents."
- **Conflicting sources**: Instruct the model to present both sides or note the conflict.
- **Large corpus / many updates**: Incremental indexing, versioning of chunks, metadata for "as of" date.
- **Permissions**: Filter chunks by user ACL at retrieval time.

## Verification

1. Ingest the documents — chunks appear in the vector DB with correct metadata.
2. Run a set of test questions — retrieved chunks are relevant (manual review).
3. Generated answers are grounded in the retrieved context (no obvious hallucinations) and cite sources.
4. Evaluation scores on the golden set meet targets (e.g., faithfulness > 0.85).
5. Re-indexing with updated documents works without duplicating old chunks.
6. Success: The RAG system answers questions accurately from the corpus with good citation and low hallucination rate.

## References

- [LangChain RAG](https://python.langchain.com/docs/use_cases/question_answering/)
- [LlamaIndex](https://docs.llamaindex.ai/)
- [RAGAS](https://github.com/explodinggradients/ragas)
- [Chunking strategies for RAG](https://www.pinecone.io/learn/chunking-strategies/)
- [Hybrid Search](https://www.pinecone.io/learn/hybrid-search-intro/)
