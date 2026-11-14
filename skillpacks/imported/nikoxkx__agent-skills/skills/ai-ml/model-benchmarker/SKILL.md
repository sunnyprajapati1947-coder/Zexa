---
name: model-benchmarker
description: Benchmarks LLM performance on speed, cost, accuracy, and token efficiency. Use when selecting a model for a use case or comparing model versions.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: llm-benchmark, latency, cost, accuracy, ttft, tps, evaluation
---

## Overview

Builds a comprehensive LLM benchmark harness focused on practical production metrics: latency (TTFT, time-per-output-token, end-to-end), cost (input + output tokens × price), accuracy/quality on task-specific tests, token efficiency, streaming vs non-streaming, and batch performance. Produces comparable numbers across models and a decision framework.

## When to Use This Skill

- Choosing which model(s) to use for a new feature or product.
- Comparing a new model release against your current one.
- Optimizing the cost/quality/latency tradeoff for a specific workload.
- The user says "which model should we use?" or "benchmark these models".

## Prerequisites

- Access to the models you want to compare (API keys or local inference server).
- A representative test set for the target task (quality eval) + a set of typical prompts for latency/cost.
- (Optional) A quality evaluation harness (see `evaluation-harness` skill).

## Steps

1. **Define the benchmark dimensions**:
   - Quality / accuracy on your task.
   - Latency: TTFT (time to first token), TPS (tokens per second), total time.
   - Cost: $ per 1M input + output tokens (use current published prices).
   - Token usage: input + output tokens per request.
   - Reliability: error rate, timeout rate.

2. **Prepare test sets**:
   - Quality set: 50-200 examples with ground truth or strong judge.
   - Latency set: 20-50 representative prompts of varying lengths (short, medium, long context).
   - Run multiple times and average (warm up, then measure).

3. **Measurement**:
   - For streaming APIs: capture TTFT and per-token timestamps.
   - For non-streaming: just wall time.
   - Use the provider's usage metadata for exact token counts when available.
   - Calculate cost from token counts + published prices.

4. **Run the benchmark**:
   - Same prompts, same temperature (usually 0 or 0.2 for consistency), same max_tokens.
   - Same system prompt / few-shot across models when fair.
   - Record raw results + aggregates.

5. **Analysis & visualization**:
   - Table: Model | Quality Score | Avg TTFT | Avg TPS | Avg Cost per request | Tokens in/out.
   - Pareto frontier (quality vs cost, quality vs latency).
   - Failure cases per model.

6. **Output**:
   - Benchmark script (Python) that is easy to extend with new models.
   - Results JSON + summary table (Markdown or pandas).
   - Visualization code (matplotlib or Plotly).
   - Decision framework: "If quality delta < X% and cost savings > Y%, switch to cheaper model."
   - Recommendations for your specific use case.

## Examples

A full benchmark script comparing Claude 3 Haiku / Sonnet, GPT-4o-mini / 4o, Gemini Flash / Pro on a customer support classification + draft task, with streaming latency measurement, cost calculation, quality via LLM judge, and a summary report with charts is included.

## Edge Cases & Error Handling

- **Rate limits during benchmark**: Add sleeps or run sequentially with backoff.
- **Context length differences**: Note max context and test at realistic lengths.
- **Pricing changes**: The script should take prices as input or fetch from a config.

## Verification

1. The script runs cleanly against at least two models.
2. Latency numbers are stable across repeated runs (low variance).
3. Cost calculation matches what you see in the provider dashboard for the test calls.
4. Quality scores align with your intuition (cheaper models are usually a bit worse).
5. The report clearly shows tradeoffs.
6. Success: You have objective data to make a model selection decision and can re-run the benchmark easily when new models are released.

## References

- [Artificial Analysis](https://artificialanalysis.ai/)
- [LMSYS Chatbot Arena](https://chat.lmsys.org/)
- [HELM](https://crfm.stanford.edu/helm/latest/)
- [LiteLLM](https://github.com/BerriAI/litellm) (for unified benchmarking across providers)
- [OpenTelemetry for LLM observability](https://opentelemetry.io/)
