---
name: agent-chain-designer
description: Designs multi-step AI agent chains with tool use, planning, and error recovery. Use when building agentic systems that require planning, tool calls, or multi-turn reasoning.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: agents, langchain, llama-index, react, tool-use, planning, multi-step
---

## Overview

Designs and implements reliable multi-step AI agent chains. Covers chain types (sequential, parallel, branching, looping), tool definition (JSON schema + execution), planning patterns (ReAct, Plan-and-Execute, Reflexion), error recovery (retry, fallback, human-in-the-loop), state management, observability (tracing), and complete implementation templates using LangChain, LlamaIndex, or custom code.

## When to Use This Skill

- Building agents that need to use tools, plan, or perform multi-step reasoning.
- The user describes a complex task that requires "research then act", "use these tools in sequence", or "handle errors gracefully".
- Existing single-prompt or simple RAG approaches are insufficient.

## Prerequisites

- Clear task that benefits from tool use or multi-step reasoning.
- Tools/APIs the agent will call (with authentication).
- LLM that supports tool calling / function calling well (Claude 3, GPT-4, Gemini 1.5, etc.).
- (Recommended) LangChain, LlamaIndex, or a custom agent framework.

## Steps

1. **Decompose the task**:
   - What are the atomic steps?
   - Which steps require tools vs pure reasoning?
   - What are the failure modes and how should the agent recover?

2. **Define tools** (critical):
   - Name, description (the model reads this), parameters (JSON Schema).
   - Implementation (the actual function the agent calls).
   - Return value format (the model sees this).
   - Error handling inside the tool (never let the tool crash the agent).

3. **Choose agent architecture**:
   - ReAct (Thought → Action → Observation loop) — very popular and effective.
   - Plan-and-Execute (high-level plan first, then execute steps).
   - Reflexion / self-critique (agent critiques its own output and retries).
   - Hierarchical (manager agent + specialist agents).

4. **State & memory**:
   - Short-term (conversation history, scratchpad).
   - Long-term (vector store of past experiences or facts).
   - How to summarize or prune history when context grows.

5. **Error recovery & control flow**:
   - Retry with different prompt or tool.
   - Fallback to simpler method or human.
   - Max iterations / timeout to prevent infinite loops.
   - Structured output for control (e.g., "next_action": "tool" | "final_answer" | "ask_human").

6. **Observability**:
   - Log every thought, action, observation, and final answer.
   - Use LangSmith, Phoenix, Helicone, or custom tracing.
   - Capture token usage and latency per step.

7. **Output**:
   - Tool definitions (JSON Schema + Python functions).
   - Agent prompt(s) (system + ReAct format).
   - Full agent loop code (or LangChain/LlamaIndex agent).
   - Error handling and recovery logic.
   - Example run trace (good and bad paths).
   - Evaluation approach for the agent.

## Examples

A complete ReAct-style agent for "research a company and draft a personalized outreach email" with tools for web search, company info lookup, email draft, and human approval step, including full prompts, tool schemas, the agent loop, and tracing is included.

## Edge Cases & Error Handling

- **Tool returns garbage**: Agent should detect low-quality observation and either retry the tool with better params or fall back.
- **Infinite loops**: Hard max_steps + timeout.
- **Cost explosion**: Track cumulative tokens/cost; stop early if budget exceeded.
- **Hallucinated tool calls**: The framework should only allow calling tools you defined.

## Verification

1. The agent successfully completes the happy-path task using tools.
2. On a failing tool or bad intermediate result, it recovers (retries, falls back, or asks for help).
3. Traces are complete and readable (you can debug why it did what it did).
4. It does not loop forever or spend excessive tokens.
5. On a held-out set of tasks, success rate is measured and acceptable.
6. Success: The agent reliably accomplishes the multi-step goal with appropriate tool use and graceful handling of problems.

## References

- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [LlamaIndex Workflows / Agents](https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/)
- [Reflexion Paper](https://arxiv.org/abs/2303.11366)
- [Toolformer Paper](https://arxiv.org/abs/2302.04761)
- [LangSmith](https://docs.smith.langchain.com/)
