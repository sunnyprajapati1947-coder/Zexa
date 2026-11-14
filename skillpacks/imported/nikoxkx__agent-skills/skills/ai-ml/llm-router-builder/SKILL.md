---
name: llm-router-builder
description: Builds an LLM router that selects the right model or prompt based on task complexity, cost, or latency. Use when optimizing AI API costs or routing queries to specialized models.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: llm-router, cost-optimization, model-selection, cascading, complexity-classifier
---

## Overview

Builds an intelligent LLM router that chooses the cheapest/fastest/ most appropriate model or prompt for each incoming request. Covers routing strategies (complexity classifier, embedding similarity, regex/rules, cascading), model tier design, fallback logic, caching, and a complete, production-ready Python router implementation supporting OpenAI + Anthropic + local models.

## When to Use This Skill

- High LLM spend and you want to reduce cost without hurting quality too much.
- Different queries have very different complexity (simple FAQ vs deep reasoning).
- You have access to multiple models (cheap fast ones + expensive smart ones) and want to use the right one per task.
- Building a multi-model gateway or agent that needs to be cost-aware.

## Prerequisites

- Access to at least two LLMs with different cost/quality/latency profiles.
- A way to classify or score incoming queries (or willingness to build one).
- (Recommended) Embedding model for similarity-based routing.
- Logging of token usage and quality signals.

## Steps

1. **Define model tiers**:
   - Tier 0 (free/fast): small local model, rule-based, or cached answers.
   - Tier 1 (cheap): GPT-4o-mini, Claude 3 Haiku, Gemini Flash, etc.
   - Tier 2 (smart/expensive): GPT-4o, Claude 3.5 Sonnet, o1, etc.
   - Document cost per 1M tokens and typical latency for each.

2. **Routing strategies** (pick one or combine):
   - **Rules / regex**: Simple, zero-cost (e.g., "if query contains 'code' → coding model").
   - **Complexity classifier**: Fine-tune or prompt a small model to output "simple | medium | complex".
   - **Embedding similarity**: Embed the query and route based on similarity to known hard/easy example sets.
   - **Cascading**: Always try cheap model first; if confidence low or output fails validation, escalate to expensive model.
   - **Task type**: Route coding questions to a coding-specialized model, math to a math model, etc.

3. **Fallback & escalation**:
   - If cheap model returns low-quality (detected by length, refusal, validation failure, or a judge), retry with next tier.
   - Always have a "best effort" expensive fallback.

4. **Caching**:
   - Exact match cache for identical queries.
   - Semantic cache (embed query, retrieve similar past answers if similarity > threshold).
   - TTL and invalidation strategy.

5. **Implementation**:
   - Clean `Router` class with `route(query) -> model_name` and `complete(query, **kwargs)`.
   - Pluggable classifiers and caches.
   - Logging of every decision + cost.
   - Optional: async support.

6. **Output**:
   - Complete `llm_router.py` with multiple strategies implemented.
   - Example model tier config (JSON or dataclass).
   - Complexity classifier prompt or fine-tuning dataset sketch.
   - Caching implementation (exact + semantic).
   - Dashboard or log analysis script to see routing distribution and savings.

## Examples

A full router that:
- Uses a small classifier (or LLM judge) to label complexity.
- Routes simple queries to Haiku / 4o-mini.
- Routes complex reasoning to Sonnet / 4o.
- Falls back on validation failure.
- Uses semantic cache for repeated questions.
With usage example and cost savings simulation.

## Edge Cases & Error Handling

- **Classifier is wrong**: The cascade/fallback catches most mistakes.
- **Cache poisoning**: Only cache when the answer was high-quality (validated or judged good).
- **Cost tracking**: Always log `model`, `input_tokens`, `output_tokens`, `cost` for every call.

## Verification

1. The router code runs and makes decisions.
2. On a test set of easy/medium/hard queries, it routes the majority of easy ones to cheap models and hard ones to expensive models.
3. Quality on the test set is close to "always use expensive" while cost is significantly lower.
4. Fallback triggers correctly on low-quality cheap outputs.
5. Cache hits reduce cost/latency on repeated queries.
6. Success: You have a measurable reduction in LLM spend with acceptable quality impact, and the system is easy to tune and monitor.

## References

- [LLM Routing Papers & Techniques](https://arxiv.org/abs/2406.18665)
- [Semantic Caching](https://python.langchain.com/docs/integrations/caches/)
- [OpenAI + Anthropic SDKs](https://github.com/anthropics)
- [LiteLLM](https://github.com/BerriAI/litellm) (great for multi-provider abstraction)
