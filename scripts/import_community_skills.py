#!/usr/bin/env python3
"""Import a pinned, curated 450+ skill reference pack.

Only SKILL.md directories are copied. Nothing from a skill is executed.
External instructions remain untrusted and require review before activation.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from zexa.skillpacks import inspect_skill_file  # noqa: E402

SOURCES = (
    {
        "repo": "anthropics/knowledge-work-plugins",
        "commit": "e91a134584eb798bac7fb0379358006a2b63b965",
        "license": "Apache-2.0",
        "expected_skill_files": 252,
    },
    {
        "repo": "MicrosoftDocs/Agent-Skills",
        "commit": "9b16b5c7c7716949c83fc4bbdc448e0ada7f93a3",
        "license": "CC-BY-4.0",
        "expected_skill_files": 201,
    },
)
MINIMUM_SKILLS = 300


def run(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        command, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def clone_sparse(source: dict, destination: Path) -> list[str]:
    url = f"https://github.com/{source['repo']}.git"
    run(["git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1", url, str(destination)])
    run(["git", "fetch", "--depth", "1", "origin", source["commit"]], cwd=destination)
    paths = run(["git", "ls-tree", "-r", "--name-only", source["commit"]], cwd=destination).splitlines()
    skill_files = sorted(p for p in paths if p.lower().endswith("/skill.md") or p.lower() == "skill.md")
    if len(skill_files) < source["expected_skill_files"]:
        raise RuntimeError(
            f"{source['repo']} returned {len(skill_files)} skills; "
            f"expected at least {source['expected_skill_files']}."
        )
    directories = sorted({str(Path(p).parent).replace("\\", "/") for p in skill_files})
    run(["git", "sparse-checkout", "init", "--cone"], cwd=destination)
    run(["git", "sparse-checkout", "set", *directories], cwd=destination)
    run(["git", "checkout", "--detach", source["commit"]], cwd=destination)
    return skill_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a pinned 450+ skill reference pack.")
    parser.add_argument("--dry-run", action="store_true", help="scan and report without copying skill folders")
    args = parser.parse_args()
    output = ROOT / "skillpacks" / "imported"
    if output.exists():
        raise SystemExit(f"{output} already exists; move it aside before importing again.")
    records: list[dict] = []
    rejected: list[dict] = []
    pending_copies: list[tuple[Path, Path]] = []
    license_copies: list[tuple[Path, Path]] = []
    seen: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="zexa-skill-import-") as temp:
        temp_root = Path(temp)
        for source in SOURCES:
            repo_slug = source["repo"].replace("/", "__").lower()
            checkout = temp_root / repo_slug
            skill_files = clone_sparse(source, checkout)
            license_file = checkout / "LICENSE"
            if not license_file.is_file():
                raise RuntimeError(f"Missing source LICENSE file: {source['repo']}")
            for relative in skill_files:
                path = checkout / relative
                try:
                    item = inspect_skill_file(
                        path, checkout, source["repo"], source["commit"], source["license"]
                    )
                    if item.name in seen:
                        rejected.append({"source": source["repo"], "path": relative, "reason": "duplicate skill name"})
                        continue
                    seen.add(item.name)
                    destination = output / repo_slug / Path(relative).parent
                    pending_copies.append((path.parent, destination))
                    records.append({
                        "name": item.name,
                        "description": item.description,
                        "source_repo": item.source_repo,
                        "source_commit": item.source_commit,
                        "source_path": item.relative_path,
                        "imported_path": str((Path(repo_slug) / Path(relative).parent).as_posix()),
                        "license": item.license_id,
                        "sha256": item.sha256,
                        "review_required": item.review_required,
                        "warnings": list(item.warnings),
                        "enabled": False,
                    })
                except Exception as exc:
                    rejected.append({"source": source["repo"], "path": relative, "reason": str(exc)})
            license_copies.append((license_file, Path(repo_slug + "-LICENSE")) )
    if len(records) < MINIMUM_SKILLS:
        raise SystemExit(
            f"Import stopped: only {len(records)} valid unique skills passed checks; "
            f"at least {MINIMUM_SKILLS} are required. No skills were activated."
        )
    report = {
        "schema_version": 1,
        "imported_count": len(records),
        "enabled_count": 0,
        "sources": SOURCES,
        "skills": records,
        "rejected": rejected,
        "execution_policy": "metadata and reference files only; never execute imported scripts or hooks",
    }
    if not args.dry_run:
        output.mkdir(parents=True, exist_ok=False)
        for source_dir, destination in pending_copies:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, destination, dirs_exist_ok=True, symlinks=False, ignore=lambda directory, names: [name for name in names if (Path(directory) / name).is_symlink()])
        license_dir = output / "licenses"
        license_dir.mkdir(parents=True, exist_ok=True)
        for source_file, filename in license_copies:
            shutil.copy2(source_file, license_dir / filename)
        (output / "index.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {len(records)} unique skills from {len(SOURCES)} pinned GitHub repositories.")
    print(f"Rejected or duplicate entries: {len(rejected)}")
    print("Imported skills remain disabled until individually reviewed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
