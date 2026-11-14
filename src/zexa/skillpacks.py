"""Safe, metadata-only importer for third-party Agent Skills.

Imported skill instructions are untrusted reference material. This module never
executes scripts, hooks, shell commands, MCP servers, or network requests.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path

MAX_SKILL_BYTES = 64 * 1024
MAX_SKILLS_PER_SCAN = 1000
ALLOWED_LICENSES = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
    "MPL-2.0", "CC0-1.0", "CC-BY-4.0", "Unlicense",
}
_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
_EXCLUDED_TOPICS = re.compile(
    r"(?i)\b(?:firearms?|guns?|ammunition|explosives?|weapons?|knives?|"
    r"self[- ]defen[cs]e weapons?|narcotics?|recreational drugs?|"
    r"controlled substances?|casino|gambling|sports betting|betting strategy|"
    r"prediction markets?|dangerous challenges?|stunts?)\b"
)
_UNSAFE_PATTERNS = (
    re.compile(r"(?im)^\s*allowed-tools\s*:\s*.*\bBash\b"),
    re.compile(r"(?i)\b(curl|wget)\b[^\n]{0,240}\|\s*(sh|bash)\b"),
    re.compile(r"(?i)dangerouslyDisableSandbox|disableSandbox"),
    re.compile(r"(?im)^\s*(hooks?|preload|postload)\s*:"),
    re.compile(r"(?i)\b(rm\s+-rf|sudo\s+|chmod\s+777)\b"),
)


@dataclass(frozen=True)
class ImportedSkill:
    name: str
    description: str
    source_repo: str
    source_commit: str
    relative_path: str
    license_id: str
    sha256: str
    review_required: bool
    warnings: tuple[str, ...] = ()


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must begin with YAML frontmatter.")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed.")
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Ignore nested metadata (e.g. generated_at) rather than interpreting it.
        # The loader only consumes the two top-level routing fields below.
        if line[:1].isspace():
            continue
        if ":" not in line:
            raise ValueError("Unsupported top-level frontmatter line.")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", key):
            raise ValueError("Invalid frontmatter key.")
        if key in metadata:
            raise ValueError(f"Duplicate frontmatter field: {key}")
        metadata[key] = value
    return metadata, text[end + 4:].strip()


def inspect_skill_file(
    path: Path,
    root: Path,
    source_repo: str,
    source_commit: str,
    license_id: str,
) -> ImportedSkill:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_root not in resolved_path.parents:
        raise ValueError("Skill path escapes the selected import root.")
    if path.name.lower() != "skill.md":
        raise ValueError("Only SKILL.md files can be imported.")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_SKILL_BYTES:
        raise ValueError("Skill file is empty or exceeds the 64 KiB limit.")
    text = raw.decode("utf-8")
    metadata, body = _frontmatter(text)
    name = metadata.get("name", "").strip().lower()
    description = metadata.get("description", "").strip()
    if not _NAME.fullmatch(name):
        raise ValueError("Skill name must be a valid lowercase slug.")
    if not description or len(description) > 500:
        raise ValueError("Skill description must contain 1–500 characters.")
    if not body or len(body) > 48_000:
        raise ValueError("Skill body is empty or exceeds the supported size.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source_repo):
        raise ValueError("Source must be a GitHub owner/repository.")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("Source commit must be a full 40-character SHA.")
    if license_id not in ALLOWED_LICENSES:
        raise ValueError("Skill license is missing or not on the approved allowlist.")
    if _EXCLUDED_TOPICS.search(" ".join((name, description, body))):
        raise ValueError("Skill is outside Zexa safe import scope.")
    warnings = tuple(
        f"Potentially unsafe pattern: {pattern.pattern}"
        for pattern in _UNSAFE_PATTERNS if pattern.search(text)
    )
    return ImportedSkill(
        name=name,
        description=description,
        source_repo=source_repo,
        source_commit=source_commit,
        relative_path=resolved_path.relative_to(resolved_root).as_posix(),
        license_id=license_id,
        sha256=hashlib.sha256(raw).hexdigest(),
        review_required=bool(warnings),
        warnings=warnings,
    )


def scan_skill_directory(
    root: Path,
    source_repo: str,
    source_commit: str,
    license_by_path: dict[str, str],
    max_skills: int = MAX_SKILLS_PER_SCAN,
) -> list[ImportedSkill]:
    """Inspect a bounded directory; unlicensed files are reported as rejected."""
    if not 1 <= max_skills <= MAX_SKILLS_PER_SCAN:
        raise ValueError("max_skills must be between 1 and 1000.")
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Skill import root must be an existing directory.")
    files = sorted(root.rglob("SKILL.md"))
    if len(files) > max_skills:
        raise ValueError("Skill pack exceeds the configured scan limit.")
    results: list[ImportedSkill] = []
    seen: set[str] = set()
    for path in files:
        relative = path.resolve().relative_to(root).as_posix()
        license_id = license_by_path.get(relative)
        if license_id is None:
            continue
        item = inspect_skill_file(path, root, source_repo, source_commit, license_id)
        if item.name in seen:
            raise ValueError(f"Duplicate skill name in pack: {item.name}")
        seen.add(item.name)
        results.append(item)
    return results



def load_imported_manifest(path: Path | None = None) -> dict:
    """Load metadata for disabled imported skills without executing their content."""
    manifest_path = path or (
        Path(__file__).resolve().parents[2] / "skillpacks" / "imported" / "index.json"
    )
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError("No imported skill reference pack is installed.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Imported skill manifest is not valid UTF-8 JSON.") from exc

    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported imported skill manifest schema.")
    skills = data.get("skills")
    if not isinstance(skills, list) or len(skills) > MAX_SKILLS_PER_SCAN:
        raise ValueError("Imported skill manifest has an invalid skill list.")
    if data.get("imported_count") != len(skills):
        raise ValueError("Imported skill manifest count does not match its entries.")
    if data.get("enabled_count") != 0:
        raise ValueError("Imported skill packs must remain disabled by default.")

    seen: set[str] = set()
    for item in skills:
        if not isinstance(item, dict):
            raise ValueError("Imported skill manifest contains an invalid entry.")
        name = item.get("name")
        description = item.get("description")
        source_repo = item.get("source_repo")
        source_commit = item.get("source_commit")
        source_path = item.get("source_path")
        license_id = item.get("license")
        sha256 = item.get("sha256")
        if not isinstance(name, str) or not _NAME.fullmatch(name) or name in seen:
            raise ValueError("Imported skill manifest contains an invalid or duplicate name.")
        if not isinstance(description, str) or not 1 <= len(description) <= 500:
            raise ValueError("Imported skill manifest contains an invalid description.")
        if not isinstance(source_repo, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source_repo
        ):
            raise ValueError("Imported skill manifest contains an invalid source repository.")
        if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            raise ValueError("Imported skill manifest contains an invalid source commit.")
        if not isinstance(source_path, str) or not source_path or source_path.startswith("/"):
            raise ValueError("Imported skill manifest contains an invalid source path.")
        if ".." in Path(source_path).parts:
            raise ValueError("Imported skill manifest contains a path traversal.")
        if license_id not in ALLOWED_LICENSES:
            raise ValueError("Imported skill manifest contains an unapproved license.")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError("Imported skill manifest contains an invalid content hash.")
        if item.get("enabled") is not False:
            raise ValueError("Imported skill references cannot be enabled by this loader.")
        if not isinstance(item.get("review_required"), bool):
            raise ValueError("Imported skill manifest has invalid review metadata.")
        if not isinstance(item.get("warnings"), list):
            raise ValueError("Imported skill manifest has invalid warning metadata.")
        seen.add(name)

    return data
