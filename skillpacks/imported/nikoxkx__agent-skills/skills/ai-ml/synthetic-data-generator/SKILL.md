---
name: synthetic-data-generator
description: Generates synthetic training or test data using LLMs or statistical methods. Use when you need labelled training data, test fixtures, or privacy-safe data substitutes.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: synthetic-data, data-generation, llm, privacy, augmentation, testing
---

## Overview

Generates high-quality synthetic data using LLMs (for text, structured records, conversations) or statistical methods (for tabular). Covers use case taxonomy, prompt strategies for controlled diversity, schema-driven generation, quality validation (deduplication, diversity, realism), seed example selection, privacy considerations, and complete generation pipelines with evaluation.

## When to Use This Skill

- You need more training data for fine-tuning or few-shot examples.
- Creating test fixtures or demo data that looks realistic.
- Privacy or compliance prevents using real customer data.
- Augmenting a small real dataset.

## Prerequisites

- A schema or example of the desired data shape (JSON schema, Pydantic model, or a few real examples).
- LLM access (strong model helps for quality and diversity).
- (For tabular) `faker`, `sdv`, or similar libraries.

## Steps

1. **Decide generation approach**:
   - LLM-based: best for text, conversations, JSON, code, nuanced labels.
   - Statistical / faker: best for structured tabular data with known distributions.
   - Hybrid: use LLM for complex fields, faker for simple ones.

2. **Schema-driven generation**:
   - Provide a JSON Schema or Pydantic model in the prompt.
   - Ask the model to generate N records that conform to it.
   - Use structured output / JSON mode.

3. **Seed & diversity**:
   - Start with a small number of real or high-quality seed examples.
   - Vary the prompt (different personas, contexts, edge cases).
   - Temperature + top_p for diversity (higher for exploration, lower for fidelity).
   - Post-process to remove near-duplicates (embedding similarity or exact match).

4. **Quality validation**:
   - Schema validation (Pydantic or jsonschema).
   - Deduplication (exact + semantic).
   - Diversity metrics (unique values per field, embedding spread).
   - Realism / fidelity (compare distributions to real data if available, or LLM judge).
   - Privacy (no PII leakage — scan with a secret/PII detector).

5. **Scale**:
   - Generate in batches (avoid very large single prompts).
   - Parallelize across multiple LLM calls.
   - Store intermediate results and resume.

6. **Output**:
   - Generation script (Python) that takes a schema + seeds → synthetic dataset.
   - Prompt templates for different data types.
   - Quality validation functions.
   - Example synthetic dataset + report.
   - Guidance on mixing synthetic + real data.

## Examples

- Generate 500 diverse customer support conversations (with labels) from 10 seed examples using structured output.
- Generate realistic but fully synthetic user profiles + transaction history (tabular + text fields) with validation.
- Privacy-safe synthetic medical notes or financial records.

## Edge Cases & Error Handling

- **Mode collapse** (all examples too similar): Increase temperature, add more varied seeds, post-filter for diversity.
- **Schema violations**: Retry with the validation error fed back to the model.
- **PII leakage**: Run a PII/secret scanner on generated data; discard or redact offending records.

## Verification

1. All generated records pass schema validation.
2. Low exact and semantic duplicate rate (<5-10%).
3. Diversity is high (many unique values across key fields).
4. (If real data available) distributions are reasonably close.
5. Manual or LLM review finds the data realistic and useful.
6. No obvious PII in a sample.
7. Success: You have a usable synthetic dataset that can stand in for (or augment) real data for the intended purpose.

## References

- [Synthetic Data for LLMs](https://huggingface.co/blog/synthetic-data-for-llm)
- [Faker](https://faker.readthedocs.io/)
- [SDV (Synthetic Data Vault)](https://sdv.dev/)
- [LLM Synthetic Data Generation Techniques](https://arxiv.org/abs/2305.17493)
- [Pydantic](https://docs.pydantic.dev/)
