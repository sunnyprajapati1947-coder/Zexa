---
name: secret-detector
description: Detects hardcoded secrets, API keys, and credentials in codebases and git history. Use when auditing code for leaked secrets or setting up pre-commit secret detection.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: secrets, gitleaks, trufflehog, pre-commit, git-history, api-keys
---

## Overview

Detects hardcoded secrets, API keys, tokens, passwords, and other credentials in source code, configuration, and git history. Covers gitleaks and truffleHog setup and usage, custom regex patterns for common secrets (AWS, GitHub, Stripe, Slack, database URLs, private keys), pre-commit hook installation, full git history scanning, post-detection rotation procedure, and GitHub secret scanning / push protection setup.

## When to Use This Skill

- Auditing a new or existing codebase for leaked credentials.
- Setting up automated secret detection in CI and developer workflows.
- After a suspected leak or as part of security onboarding.
- The user mentions "check for secrets", "API keys in code", "gitleaks", or "trufflehog".

## Prerequisites

- The repository (local clone or GitHub).
- `gitleaks` and/or `truffleHog` installed (or Docker).
- Git history access.

## Steps

1. **Install & basic scan (current code)**:
   ```bash
   gitleaks detect --source . --report-path gitleaks-report.json
   trufflehog git file://. --only-verified
   ```

2. **Scan full git history** (most important):
   - Both tools support `--since` or full history by default.
   - `gitleaks detect --source . --report-all`

3. **Custom rules** (add to `.gitleaks.toml` or equivalent):
   - AWS access keys, GitHub tokens, Stripe keys, Slack tokens, private keys (PEM), database connection strings, JWTs, etc.
   - High-entropy string detection.

4. **Pre-commit hook** (prevent new leaks):
   - Install `pre-commit` or use gitleaks built-in hook.
   - `.pre-commit-config.yaml` with gitleaks hook.
   - Block commits that introduce secrets.

5. **CI integration**:
   - Run on every PR and on push to main.
   - Fail the build on findings (or comment + require manual review for false positives).

6. **GitHub native features**:
   - Enable secret scanning (for public repos it's free; private requires GHAS).
   - Enable push protection (blocks pushes containing known secret patterns).

7. **Post-detection procedure** (runbook):
   - Immediately rotate the secret in the provider.
   - Remove from git history (bfg-repo-cleaner or git filter-repo — destructive, coordinate with team).
   - Update any dependent systems.
   - Add the pattern to detection rules if it was a new secret type.
   - Post-incident review.

8. **Output**:
   - Exact commands for gitleaks + truffleHog.
   - Recommended `.gitleaks.toml` with common rules.
   - Pre-commit config.
   - GitHub Actions workflow for CI scanning.
   - Rotation runbook template.
   - False positive handling guidance.

## Examples

A complete setup for a typical monorepo (gitleaks config with 15+ custom rules, pre-commit hook, CI job that fails on high-confidence secrets, and a sample rotation runbook) is included.

## Edge Cases & Error Handling

- **False positives** (e.g., example keys in docs): Allow-list in the config with justification + review.
- **Secrets in test fixtures**: Use clearly fake values (`AKIAFAKE...`) or mark with `# gitleaks:allow`.
- **Binary files / large repos**: Tools handle this; tune `--max-target-megabytes` if needed.

## Verification

1. Run the scanner on the current repo — it finds (or confirms absence of) secrets in the working tree.
2. Full history scan completes and reports any historical leaks.
3. Pre-commit hook blocks a commit that adds a fake secret.
4. CI job fails on a PR that introduces a secret (or passes cleanly).
5. GitHub secret scanning / push protection is enabled.
6. Success: No new secrets are introduced, historical leaks are known and rotated, and the team has an automated safety net.

## References

- [gitleaks](https://github.com/gitleaks/gitleaks)
- [truffleHog](https://github.com/trufflesecurity/trufflehog)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [bfg-repo-cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [Pre-commit](https://pre-commit.com/)
