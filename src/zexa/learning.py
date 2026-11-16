"""Provenance-aware local learning notes and reviewable skill drafts.

Learning never executes imported instructions or generated code. Notes start as
drafts, and generated skill contracts remain inert until a trusted handler is
implemented separately in application code.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

from .skills import Skill


_NOTE_STATUSES = {"draft", "approved", "rejected", "archived"}
_SKILL_STATUSES = {"review_required", "approved", "rejected"}
_SKILL_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@dataclass(frozen=True)
class KnowledgeNote:
    note_id: int
    title: str
    body: str
    sources: tuple[dict[str, str], ...]
    source_type: str
    source_label: str
    content_sha256: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SkillDraft:
    draft_id: int
    note_id: int
    name: str
    description: str
    system_instruction: str
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    risk_level: str
    status: str
    created_at: str
    updated_at: str


class LearningStore:
    """SQLite store for reviewed knowledge notes and inert skill contracts."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".zexa" / "knowledge.sqlite3").expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_notes (
                    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_label TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS skill_drafts (
                    draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER NOT NULL REFERENCES knowledge_notes(note_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    system_instruction TEXT NOT NULL,
                    input_schema_json TEXT NOT NULL,
                    output_schema_json TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(note_id, name)
                )
            """)
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_status_updated "
                "ON knowledge_notes(status, updated_at)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_skill_drafts_status "
                "ON skill_drafts(status, updated_at)"
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate_sources(sources: list[dict[str, str]] | None) -> list[dict[str, str]]:
        if sources is None:
            return []
        if not isinstance(sources, list) or len(sources) > 20:
            raise ValueError("A knowledge note may contain at most 20 source references.")
        clean: list[dict[str, str]] = []
        for item in sources:
            if not isinstance(item, dict) or set(item) != {"title", "url"}:
                raise ValueError("Each source must contain exactly title and url.")
            title, url = item["title"], item["url"]
            if not isinstance(title, str) or not title.strip() or len(title) > 300:
                raise ValueError("Source title must contain 1–300 characters.")
            if not isinstance(url, str) or len(url) > 2048:
                raise ValueError("Source URL must contain at most 2048 characters.")
            parsed = urlsplit(url)
            if (
                parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
            ):
                raise ValueError("Source URLs must be valid HTTP(S) URLs without credentials.")
            clean.append({"title": title.strip(), "url": url})
        return clean

    def save_note(
        self,
        title: str,
        body: str,
        *,
        source_type: str,
        source_label: str,
        sources: list[dict[str, str]] | None = None,
        source_sha256: str | None = None,
    ) -> int:
        title = title.strip() if isinstance(title, str) else ""
        body = body.strip() if isinstance(body, str) else ""
        if not title or len(title) > 200:
            raise ValueError("Knowledge title must contain 1–200 characters.")
        if not body or len(body) > 20_000:
            raise ValueError("Knowledge summary must contain 1–20000 characters.")
        if source_type not in {"web_search", "local_file", "user_text"}:
            raise ValueError("Unsupported knowledge source type.")
        if not isinstance(source_label, str) or not source_label.strip() or len(source_label) > 300:
            raise ValueError("Source label must contain 1–300 characters.")
        clean_sources = self._validate_sources(sources)
        digest = source_sha256 or hashlib.sha256(body.encode("utf-8")).hexdigest()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Source SHA-256 must be a lowercase 64-character digest.")
        now = self._now()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                """INSERT INTO knowledge_notes
                   (title, body, sources_json, source_type, source_label,
                    content_sha256, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)""",
                (
                    title, body, json.dumps(clean_sources, ensure_ascii=False),
                    source_type, source_label.strip(), digest, now, now,
                ),
            )
            return int(cursor.lastrowid)

    @staticmethod
    def _note(row: sqlite3.Row) -> KnowledgeNote:
        sources = json.loads(row["sources_json"])
        return KnowledgeNote(
            note_id=int(row["note_id"]),
            title=row["title"],
            body=row["body"],
            sources=tuple(sources),
            source_type=row["source_type"],
            source_label=row["source_label"],
            content_sha256=row["content_sha256"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_note(self, note_id: int) -> KnowledgeNote | None:
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT * FROM knowledge_notes WHERE note_id=?", (note_id,)
            ).fetchone()
        return self._note(row) if row else None

    def list_notes(self, limit: int = 50, status: str | None = None) -> list[KnowledgeNote]:
        if not 1 <= limit <= 200:
            raise ValueError("Knowledge list limit must be between 1 and 200.")
        if status is not None and status not in _NOTE_STATUSES:
            raise ValueError("Invalid knowledge note status.")
        with closing(self._connect()) as db:
            if status is None:
                rows = db.execute(
                    "SELECT * FROM knowledge_notes ORDER BY note_id DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM knowledge_notes WHERE status=? ORDER BY note_id DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
        return [self._note(row) for row in rows]

    def search_notes(self, query: str, limit: int = 10, approved_only: bool = True) -> list[KnowledgeNote]:
        query = query.strip() if isinstance(query, str) else ""
        if not query or len(query) > 200:
            raise ValueError("Knowledge search query must contain 1–200 characters.")
        if not 1 <= limit <= 50:
            raise ValueError("Knowledge search limit must be between 1 and 50.")
        terms = [part for part in re.findall(r"[A-Za-z0-9_\u0900-\u097f-]{2,}", query)[:8]]
        if not terms:
            raise ValueError("Knowledge search query has no searchable terms.")
        clauses = " AND ".join("(title LIKE ? OR body LIKE ?)" for _ in terms)
        params: list[str | int] = []
        for term in terms:
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params.extend((f"%{escaped}%", f"%{escaped}%"))
        sql = "SELECT * FROM knowledge_notes WHERE " + clauses
        if approved_only:
            sql += " AND status='approved'"
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with closing(self._connect()) as db:
            rows = db.execute(sql, params).fetchall()
        return [self._note(row) for row in rows]

    def review_note(self, note_id: int, decision: str) -> bool:
        if decision not in {"approved", "rejected", "archived"}:
            raise ValueError("Knowledge review decision must be approved, rejected, or archived.")
        now = self._now()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                "UPDATE knowledge_notes SET status=?, updated_at=? WHERE note_id=?",
                (decision, now, note_id),
            )
            return cursor.rowcount > 0

    def delete_note(self, note_id: int) -> bool:
        with closing(self._connect()) as db, db:
            cursor = db.execute("DELETE FROM knowledge_notes WHERE note_id=?", (note_id,))
            return cursor.rowcount > 0

    def save_skill_draft(self, note_id: int, skill: Skill) -> int:
        if not isinstance(skill, Skill):
            raise TypeError("A validated Skill contract is required.")
        if skill.enabled:
            raise ValueError("Learned skill drafts must remain disabled.")
        if not _SKILL_NAME.fullmatch(skill.name):
            raise ValueError("Learned skill name must be a lowercase identifier.")
        if self.get_note(note_id) is None:
            raise KeyError("Knowledge note does not exist.")
        now = self._now()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                """INSERT INTO skill_drafts
                   (note_id, name, description, system_instruction, input_schema_json,
                    output_schema_json, risk_level, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'review_required', ?, ?)""",
                (
                    note_id, skill.name, skill.description, skill.system_instruction,
                    json.dumps(skill.input_schema, ensure_ascii=False),
                    json.dumps(skill.output_schema, ensure_ascii=False),
                    skill.risk_level, now, now,
                ),
            )
            return int(cursor.lastrowid)

    def list_skill_drafts(self, limit: int = 50) -> list[SkillDraft]:
        if not 1 <= limit <= 200:
            raise ValueError("Skill draft list limit must be between 1 and 200.")
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT * FROM skill_drafts ORDER BY draft_id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            SkillDraft(
                draft_id=int(row["draft_id"]),
                note_id=int(row["note_id"]),
                name=row["name"],
                description=row["description"],
                system_instruction=row["system_instruction"],
                input_schema=json.loads(row["input_schema_json"]),
                output_schema=json.loads(row["output_schema_json"]),
                risk_level=row["risk_level"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def review_skill_draft(self, draft_id: int, decision: str) -> bool:
        if decision not in {"approved", "rejected"}:
            raise ValueError("Skill draft decision must be approved or rejected.")
        now = self._now()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                "UPDATE skill_drafts SET status=?, updated_at=? WHERE draft_id=?",
                (decision, now, draft_id),
            )
            return cursor.rowcount > 0
