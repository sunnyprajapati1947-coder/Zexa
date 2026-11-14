---
name: api-wrapper-builder
description: Creates a clean Python/TypeScript wrapper around an external AI API (OpenAI, Anthropic, Google AI, etc.). Use when abstracting an AI provider for easier use, testing, or provider switching.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: api-wrapper, openai, anthropic, litellm, retry, streaming, error-handling
---

## Overview

Creates a clean, production-grade client wrapper around one or more AI provider APIs. Covers client class design, retry + exponential backoff with jitter, streaming support, token counting, response parsing/normalization, error classification (rate limit, auth, server, timeout), provider-swappable interface, logging/cost tracking, and a complete, testable implementation (Python example with OpenAI + Anthropic, plus TypeScript notes).

## When to Use This Skill

- You are using (or plan to use) one or more LLM APIs and want a consistent interface.
- You need robust error handling, retries, and observability around API calls.
- You want to make it easy to switch providers or add new ones later (multi-LLM strategy).
- Building internal SDKs or agent frameworks that call LLMs.

## Prerequisites

- API keys for the provider(s) you will wrap.
- Understanding of the provider's SDK and response shapes.
- (Recommended) `tenacity` or `backoff` for retries in Python; equivalent in TS.

## Steps

1. **Design the interface** (provider-agnostic where possible):
   - `complete(prompt, model, temperature, max_tokens, **kwargs) -> Response`
   - `stream(...) -> Iterator[Chunk]`
   - `count_tokens(text, model) -> int`
   - Common response shape: `text`, `usage` (input/output tokens), `model`, `finish_reason`, `raw` (original response).

2. **Error classification & handling**:
   - RateLimitError → retry with backoff, respect `retry-after` when present.
   - AuthenticationError → fail fast, do not retry.
   - ServerError / Timeout → retry with jitter.
   - ContextLengthExceeded → surface clearly to caller (or auto-truncate with warning).

3. **Retry strategy**:
   - Exponential backoff + full jitter.
   - Max attempts (e.g., 5).
   - Distinguish transient vs permanent errors.

4. **Streaming**:
   - Yield chunks as they arrive.
   - Accumulate full text for the final response object when needed.
   - Handle partial JSON or tool calls correctly.

5. **Observability**:
   - Log every request (sanitized) with latency, tokens, cost estimate, error.
   - Emit metrics (Prometheus, Datadog, etc.).
   - Optional: send traces to LangSmith / Helicone / Phoenix.

6. **Multi-provider**:
   - Use LiteLLM as a base (strongly recommended for most cases) or build a thin adapter layer.
   - Config-driven model routing.

7. **Output**:
   - Complete `LLMClient` class (Python) with the methods above.
   - Concrete implementations for OpenAI and Anthropic (or LiteLLM wrapper).
   - Retry decorator / context manager.
   - Token counter (tiktoken for OpenAI, anthropic tokenizer, or approximate).
   - Example usage + tests (pytest or vitest).
   - Cost calculator.

## Examples

A full `LLMClient` that supports both OpenAI and Anthropic (via LiteLLM or direct), with robust retries, streaming, token counting, cost logging, and a clean `Response` dataclass is included, plus a minimal TypeScript equivalent.

## Edge Cases & Error Handling

- **Very long prompts**: Pre-check token count and raise a clear `ContextLengthError` before calling the API.
- **Partial failures in streaming**: Ensure the caller can still get whatever was generated.
- **Provider-specific quirks**: Document them and normalize in the wrapper.

## Verification

1. The wrapper can complete a simple prompt with both providers.
2. Streaming works and the final accumulated text matches the non-streaming result.
3. Token counting is accurate (or close) for the supported models.
4. Rate limit simulation triggers retries and eventually succeeds or fails gracefully.
5. Auth error fails immediately without retries.
6. All calls are logged with token usage and approximate cost.
7. Success: Calling code is much simpler and more robust than using the raw SDKs directly, and switching providers is a config change.

## References

- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [LiteLLM](https://github.com/BerriAI/litellm) (highly recommended base)
- [Tenacity](https://tenacity.readthedocs.io/) (retry library)
- [tiktoken](https://github.com/openai/tiktoken)
