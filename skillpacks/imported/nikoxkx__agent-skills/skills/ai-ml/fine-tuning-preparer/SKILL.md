---
name: fine-tuning-preparer
description: Prepares datasets and training configurations for fine-tuning LLMs. Use when customizing a base model on domain-specific data using LoRA, QLoRA, or supervised fine-tuning.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: fine-tuning, lora, qlora, dataset, huggingface, sft, evaluation
---

## Overview

Prepares high-quality datasets and training configurations for fine-tuning LLMs (LoRA, QLoRA, full SFT). Covers when to fine-tune vs prompt engineering vs RAG, dataset formats (instruction-response JSONL), quality filtering, train/val/test splits, hyperparameter selection, LoRA config, Hugging Face Trainer / TRL setup, evaluation, and cost/latency estimation.

## When to Use This Skill

- You have domain-specific data (support tickets, legal docs, internal knowledge, code style, product data) that a base model doesn't handle well.
- Prompt engineering + RAG has hit a quality ceiling.
- You need the model to output in a very specific style, format, or with deep domain knowledge.

## Prerequisites

- A dataset of input → desired output pairs (hundreds to tens of thousands of examples).
- GPU access (single A100/H100 for QLoRA on 7-13B models is common; more for larger).
- Hugging Face account + transformers + peft + bitsandbytes + trl (or Axolotl/Unsloth for easier workflows).

## Steps

1. **Decide if fine-tuning is the right tool**:
   - Fine-tune when you need new behavior/knowledge that is hard to prompt or retrieve.
   - Prefer RAG + good prompting for factual recall over large private corpora.
   - Combine both when appropriate.

2. **Dataset format**:
   - Instruction tuning: `{"instruction": "...", "input": "...", "output": "..."}` or chat format.
   - JSONL, one example per line.
   - For chat models: messages array in the model's chat template.

3. **Quality filtering** (critical):
   - Remove duplicates (exact + near-duplicate via embedding similarity).
   - Length filters (too short or extremely long).
   - Quality heuristics or LLM-as-judge scoring.
   - Human review of a sample (aim for >95% high quality).

4. **Split strategy**:
   - 80/10/10 or 90/5/5 (train/val/test).
   - Ensure no leakage (same conversation or document not split across sets).

5. **LoRA / QLoRA config**:
   - Rank (r): 8-64 (16-32 common starting point).
   - Alpha, dropout.
   - Target modules (q_proj, v_proj, etc. for most models).
   - 4-bit or 8-bit quantization for QLoRA.

6. **Training setup (Hugging Face)**:
   - Use TRL SFTTrainer or Axolotl for simpler config.
   - Learning rate, batch size, gradient accumulation, epochs (usually 1-3 for instruction tuning).
   - Evaluation strategy, save best, early stopping.
   - Packing / packing for efficiency.

7. **Evaluation**:
   - Held-out test set with exact or fuzzy match + LLM judge.
   - Qualitative review of outputs.
   - Compare to base model + few-shot on the same test set.

8. **Output**:
   - Cleaned, split dataset files.
   - `config.yaml` or Python training script (LoRA + QLoRA).
   - Evaluation script.
   - Cost estimate (GPU hours × price).
   - Merging and inference notes (how to merge LoRA adapters back into base).

## Examples

A complete pipeline for fine-tuning a 7B or 13B model on a customer support / internal knowledge dataset: dataset cleaning script, JSONL preparation, QLoRA config, TRL training script, and evaluation harness with LLM-as-judge is included.

## Edge Cases & Error Handling

- **Catastrophic forgetting**: Use LoRA (low rank), small learning rate, short training, or replay of general data.
- **Small datasets** (<1k examples): Heavy augmentation or start with very low rank LoRA + more epochs.
- **Evaluation contamination**: Strict separation of train/val/test.

## Verification

1. Dataset passes quality filters and split checks.
2. Training runs without OOM on the target hardware (with QLoRA).
3. Validation loss decreases and plateaus reasonably.
4. On the held-out test set, the fine-tuned model outperforms the base model + good prompting (by automatic metrics and human/LLM judgment).
5. Merged model loads and generates correctly.
6. Success: The fine-tuned model shows clear improvement on the target domain/task with acceptable generalization.

## References

- [Hugging Face PEFT](https://huggingface.co/docs/peft/index)
- [TRL - Supervised Fine-Tuning](https://huggingface.co/docs/trl/sft_trainer)
- [QLoRA Paper](https://arxiv.org/abs/2305.14314)
- [Axolotl](https://github.com/OpenAccess-AI-Collective/axolotl)
- [Unsloth](https://github.com/unslothai/unsloth)
- [Fine-tuning Guide (Hugging Face)](https://huggingface.co/docs/transformers/en/training)
