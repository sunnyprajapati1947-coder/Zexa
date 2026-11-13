"""Permission-aware tool registry containing only local, non-side-effecting tools."""
from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[[str], str]
    consequential: bool = False


class ToolRouter:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.consequential:
            raise ValueError("Consequential tools require a separate approval-gated adapter.")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list(self) -> list[Tool]:
        return sorted(self._tools.values(), key=lambda item: item.name)

    def run(self, name: str, argument: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool is not allowlisted: {name}")
        if tool.consequential:
            raise PermissionError("This action requires explicit user approval.")
        return tool.handler(argument)


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_number(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        if abs(node.value) > 10**12:
            raise ValueError("Number is outside the supported range.")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _safe_number(node.left), _safe_number(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("Exponent is too large.")
        result = _BINARY[type(node.op)](left, right)
        if abs(result) > 10**12:
            raise ValueError("Result is outside the supported range.")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_safe_number(node.operand))
    raise ValueError("Only basic arithmetic is supported.")


def calculate(expression: str) -> str:
    if len(expression) > 120:
        raise ValueError("Expression is too long.")
    tree = ast.parse(expression, mode="eval")
    return str(_safe_number(tree.body))


def text_stats(text: str) -> str:
    return f"characters={len(text)} words={len(text.split())} lines={len(text.splitlines())}"


def default_router() -> ToolRouter:
    router = ToolRouter()
    router.register(Tool("calculator", "Evaluate basic arithmetic only.", calculate))
    router.register(Tool("text_stats", "Count characters, words, and lines.", text_stats))
    return router
