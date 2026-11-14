---
name: prompt-engineer
description: Designs, tests, and iterates on LLM prompts for accuracy, reliability, and performance. Use when crafting system prompts, few-shot examples, chain-of-thought prompts, or output format instructions.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: llm, prompt-engineering, few-shot, chain-of-thought, structured-output, evaluation
---

## Overview

Designs, tests, and iterates high-quality LLM prompts. Covers prompt anatomy (role, context, instructions, examples, output format), few-shot example selection and ordering, chain-of-thought triggering, structured output (JSON mode, Pydantic, grammar), prompt injection defenses, systematic evaluation, and 10 reusable prompt patterns that have proven effective across many tasks.

## When to Use This Skill

- Building or improving system prompts for agents, chatbots, or tools.
- The user wants reliable, structured output from an LLM.
- Debugging inconsistent or low-quality LLM responses.
- Creating few-shot examples or chain-of-thought prompts.

## Prerequisites

- Access to one or more LLMs (via API or local).
- A clear task definition and success criteria.
- Evaluation data (even 10-20 examples is useful to start).

## Steps

1. **Define the task precisely**:
   - What is the input?
   - What is the desired output (format, content, constraints)?
   - What are the failure modes to avoid?

2. **Prompt anatomy** (use this structure):
   - Role / persona.
   - Context / background.
   - Task instructions (clear, numbered, imperative).
   - Constraints and rules.
   - Few-shot examples (2-6 high-quality ones).
   - Output format (JSON schema, bullet list, specific template).
   - Reasoning encouragement ("Think step by step").

3. **Few-shot best practices**:
   - Choose diverse, representative, high-quality examples.
   - Order matters — put the most similar or most important first.
   - Include both positive and "edge" examples when helpful.

4. **Chain-of-Thought (CoT)**:
   - "Let's think step by step."
   - Or more specific: "First identify X, then Y, then produce Z."
   - For complex reasoning, use "ReAct" style (Thought → Action → Observation).

5. **Structured output**:
   - Use model `response_format: {type: "json_object"}` (OpenAI) or equivalent.
   - Provide a Pydantic model or JSON Schema in the prompt.
   - Validate the output in code and retry with error feedback if invalid.

6. **Defense against prompt injection**:
   - Clearly separate instructions from user content (e.g., XML tags, "User input starts here:").
   - Instruct the model to ignore instructions inside user content.
   - Validate and sanitize output.

7. **Evaluation & iteration**:
   - Create a small golden set (10-30 examples) with expected outputs.
   - Score outputs (exact match, fuzzy, LLM-as-judge).
   - A/B test prompt variants.
   - Track regression when changing models or prompts.

8. **Output**:
   - The full system prompt + user template.
   - 3-6 few-shot examples.
   - Evaluation script or rubric.
   - Notes on which model(s) it works best with.
   - Version history of the prompt.

## Examples

10 reusable prompt patterns (Classification, Extraction, Summarization, Reasoning, Tool Use, Critique, etc.) with full prompts and example inputs/outputs are included, plus a complete worked example for "Extract structured customer feedback from free-text reviews" with JSON schema, CoT, and evaluation.

## Edge Cases & Error Handling

- **Model refuses or hallucinates**: Add explicit "If you cannot answer from the provided context, say 'I don't have enough information'."
- **Output not parseable**: Always validate + retry loop with the error message fed back to the model.
- **Context length**: Summarize or chunk long context; use RAG when appropriate.

## Verification

1. Run the prompt on the golden set — success rate meets the target (e.g., >90% on key fields).
2. Test with adversarial or edge-case inputs — model behaves as specified.
3. Structured output is always valid JSON that passes Pydantic validation.
4. Changing the model (within the same family) still produces good results (or you have noted model-specific tuning).
5. Success: The prompt is reliable enough to use in production or as part of an agent, with known limitations documented.

## References

- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Prompt Engineering](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [Prompt Engineering Guide (DAIR.AI)](https://www.promptingguide.ai/)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [JSON Mode & Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
