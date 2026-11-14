# Community skill pack import

Zexa's optional community pack targets **512 candidate Agent Skills** from three pinned upstream repositories:

- `anthropics/knowledge-work-plugins`: 252 `SKILL.md` files at commit `e91a134584eb798bac7fb0379358006a2b63b965`, Apache-2.0.
- `MicrosoftDocs/Agent-Skills`: 201 `SKILL.md` files at commit `9b16b5c7c7716949c83fc4bbdc448e0ada7f93a3`, CC-BY-4.0.
- `Nikoxkx/Agent-Skills`: 59 `SKILL.md` files at commit `d4fd9165fa786d12c3d836273ac8346f5f3275ab`, Apache-2.0.

These are source-tree counts, not a claim that all 453 will pass Zexa's import checks. The importer requires at least 300 unique, valid skills after frontmatter, license, source-pin, path, and duplicate checks. It stores the exact source commit and SHA-256 for each imported file.

## Import on GitHub or Termux

The feature branch includes a GitHub Actions workflow that validates the pinned sources, imports only if at least 300 unique skills pass, verifies that all imported entries remain disabled, runs the regression suite, and commits the reference pack to the feature branch. It runs when the importer or importer workflow changes, or by manual workflow dispatch. A failed threshold check creates no imported pack.

From the Zexa repository root:

```bash
pkg install git
source .venv/bin/activate
python scripts/import_community_skills.py --dry-run
python scripts/import_community_skills.py
```

The local script uses shallow, blob-filtered clones and sparse checkout. It copies the selected skill directories and upstream license files into `skillpacks/imported/`. The pack is optional and can use substantial storage depending on the upstream reference files.

## Security and compatibility boundary

- Imported skills are **disabled by default**.
- Zexa copies their text and supporting reference files as untrusted data.
- No imported shell scripts, hooks, MCP servers, commands, or other executable files are run by the importer.
- Source repositories are pinned to immutable full commit SHAs.
- The importer rejects missing/unapproved licenses, malformed frontmatter, oversized files, path escapes, invalid names, and duplicate names.
- Potentially unsafe patterns are flagged for manual review; static checks are not a security guarantee.
- Third-party tools/connectors referenced by a skill are not installed or enabled.
- A skill is not an executable Zexa capability until a native handler, permission policy, integration, tests, and an explicit enablement path are implemented.

Do not run scripts from an imported pack just because the pack was imported. Review the source, license, and any referenced dependencies separately.
