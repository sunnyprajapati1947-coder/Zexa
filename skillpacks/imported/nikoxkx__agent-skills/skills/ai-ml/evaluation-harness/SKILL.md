---
name: evaluation-harness
description: Builds an evaluation harness to measure LLM accuracy, reliability, and performance on a task. Use when benchmarking models, comparing prompts, or tracking quality regressions.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: evaluation, llm, benchmark, ragas, llm-as-judge, regression-testing
---

## Overview

Builds a robust, repeatable evaluation harness for LLMs. Covers golden dataset construction, golden answer types (exact, fuzzy, LLM-as-judge), metric selection (accuracy, BLEU/ROUGE/BERTScore, custom, faithfulness/relevance), eval runner script, LLM-as-judge prompt templates, regression tracking (diff between runs), and integration into CI or a dashboard.

## When to Use This Skill

- Comparing multiple models or prompt versions on the same task.
- Establishing a quality baseline before shipping a feature that uses LLMs.
- Detecting quality regressions after model or prompt changes.
- The user wants "to measure how good this is" or "track quality over time".

## Prerequisites

- A task with clear success criteria.
- A set of test cases (even 20-50 is valuable to start; aim for 100+ for statistical significance).
- Access to the models being evaluated.
- (Optional but recommended) A small amount of human-labeled "golden" answers.

## Steps

1. **Construct the eval dataset**:
   - Representative of real usage (include edge cases and common failures).
   - Columns: `id`, `input`, `expected_output` (or rubric), `metadata` (difficulty, category).
   - Version the dataset (git + a simple JSONL or CSV).

2. **Choose evaluation method per task**:
   - Exact match / contains (for extraction, classification).
   - Fuzzy (Levenshtein, normalized edit distance).
   - BLEU / ROUGE / BERTScore (for generation, summarization).
   - LLM-as-judge (most flexible for open-ended tasks).
   - Human evaluation for high-stakes (sample).

3. **LLM-as-judge** (when used):
   - Write a strong judge prompt with clear rubric and few-shot examples.
   - Ask for a score (1-5 or 0-1) + reasoning.
   - Run the same judge on all candidates for fair comparison.
   - Validate the judge against human labels on a small set.

4. **Build the eval runner**:
   - Load dataset.
   - For each example: call model → parse output → compute metric(s).
   - Aggregate scores (mean, per-category breakdown, failure cases).
   - Save detailed results (JSON) + summary.

5. **Regression tracking**:
   - Store results with git commit / prompt version / model version.
   - Simple diff script: "compare run A vs run B — which examples got worse?"
   - Fail CI if score drops more than X% on key metrics.

6. **Output**:
   - Golden dataset template (with 10-20 examples).
   - `evaluate.py` script that is model- and prompt-agnostic.
   - LLM judge prompt template.
   - Results viewer (simple pandas + print or Streamlit).
   - CI integration example (GitHub Action step that runs eval and comments on PR).

## Examples

A complete harness for "customer support ticket classification + draft response" task: golden dataset (JSONL), runner script, LLM-as-judge prompt for response quality, automatic metrics, and a regression diff report is included.

## Edge Cases & Error Handling

- **Judge bias**: Use the same judge model/version for all comparisons. Calibrate against humans.
- **Output parsing failures**: Treat as score 0 and log the raw output.
- **Cost of eval**: Sample or use cheaper judge models for high-volume evals; run full eval nightly.

## Verification

1. The harness runs end-to-end on the golden set without crashing.
2. Scores are reproducible when re-running the same model + prompt.
3. LLM judge scores correlate reasonably with human judgment on a validation subset (report the correlation).
4. A known-better prompt/model scores higher than a known-worse one.
5. Regression detection works (intentionally degrade a prompt and see the harness flag it).
6. Success: You have a trustworthy, automated way to know whether a change improved, hurt, or had no effect on quality.

## References

- [RAGAS](https://docs.ragas.io/)
- [ARES](https://github.com/stanford-futuredata/ARES)
- [LLM-as-a-Judge](https://arxiv.org/abs/2306.05685)
- [HELM](https://crfm.stanford.edu/helm/latest/)
- [Big-bench](https://github.com/google/BIG-bench)
