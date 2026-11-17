"""Reviewable code-patch proposals with bounded paths and static validation.

This module does not write files or execute candidate code. Applying a reviewed
candidate remains a separate, explicitly approved RepairTransaction operation.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
from pathlib import PurePosixPath


_MAX_BYTES = 256 * 1024


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _allowed_path(path: str) -> bool:
    if not isinstance(path, str) or not path or "\x00" in path or "\\" in path:
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        return False
    if path == "README.md":
        return True
    if len(pure.parts) == 3 and pure.parts[0] == "src" and pure.parts[1] == "zexa":
        return pure.suffix == ".py"
    if len(pure.parts) == 2 and pure.parts[0] == "tests":
        return pure.name.startswith("test_") and pure.suffix == ".py"
    return False


def build_patch_proposal(path: str, original: str, candidate: str) -> dict:
    """Build a unified-diff proposal without filesystem writes or code execution."""
    if not _allowed_path(path):
        raise ValueError("Patch path must be README.md, src/zexa/*.py, or tests/test_*.py.")
    if not isinstance(original, str) or not isinstance(candidate, str):
        raise ValueError("Patch contents must be UTF-8 text strings.")
    if len(original.encode("utf-8")) > _MAX_BYTES or len(candidate.encode("utf-8")) > _MAX_BYTES:
        raise ValueError("Patch content exceeds the 256 KiB limit.")
    if original == candidate:
        raise ValueError("Candidate is identical to the current file.")
    if path.endswith(".py"):
        try:
            ast.parse(candidate, filename=path)
        except SyntaxError as exc:
            raise ValueError(f"Candidate Python syntax is invalid: {exc.msg} at line {exc.lineno}.") from exc
    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        candidate.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3,
    ))
    return {
        "status": "proposal_only",
        "path": path,
        "original_sha256": _digest(original),
        "candidate_sha256": _digest(candidate),
        "diff": diff,
        "static_validation": "python_ast_parse_passed" if path.endswith(".py") else "text_size_and_path_passed",
        "approval_required_to_apply": True,
        "tests_executed": False,
        "candidate_executed": False,
        "files_modified": False,
    }
