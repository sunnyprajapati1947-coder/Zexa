---
name: dependency-checker
description: Audits third-party dependencies for known vulnerabilities, license issues, and supply chain risks. Use when reviewing dependencies before merging or deploying.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: dependencies, supply-chain, npm-audit, pip-audit, license, dependabot, fossa
---

## Overview

Audits third-party dependencies for vulnerabilities (SCA), problematic licenses, and supply chain risk indicators. Covers `npm audit`, `pip-audit`, `cargo audit`, license checkers (FOSSA, license-checker, `pip-licenses`), dependency graph analysis, Dependabot/Renovate setup, pinning vs ranges, and a weekly dependency review workflow.

## When to Use This Skill

- Before merging a PR that updates or adds dependencies.
- As part of release preparation.
- Regularly (weekly or per sprint) as hygiene.
- After a high-profile supply chain attack (log4shell, etc.).

## Prerequisites

- The project's lockfile(s) and manifest(s) (package-lock.json, yarn.lock, poetry.lock, Cargo.lock, etc.).
- Access to vulnerability databases (tools query them).

## Steps

1. **Vulnerability scanning**:
   - Node: `npm audit` (or `pnpm audit`, `yarn audit`).
   - Python: `pip-audit` or `safety`.
   - Go: `go list -m -json all | nancy sleuth` or `govulncheck`.
   - Rust: `cargo audit`.
   - General: Snyk, Dependabot alerts, GitHub Dependabot.

2. **License auditing**:
   - `license-checker --production --onlyAllow "MIT;Apache-2.0;BSD"` (Node).
   - `pip-licenses --allow-only="MIT;Apache-2.0"` (Python).
   - FOSSA or Snyk License for larger orgs.

3. **Supply chain signals**:
   - Maintainer count, last publish date, download count, provenance (sigstore, etc.).
   - Tools like `socket.dev` or `deps.dev` give risk scores.
   - Check for typosquatting (similar names to popular packages).

4. **Pinning & ranges**:
   - Prefer exact pins in lockfiles (they are).
   - In manifests: use `^` / `~` carefully; document policy (e.g., "patch and minor auto, major manual").
   - For critical security deps, pin more tightly.

5. **Automation**:
   - Dependabot or Renovate for automated PRs (group updates, auto-merge for patch/minor after CI).
   - Require security review for major or high-risk updates.

6. **Weekly review workflow**:
   - Review open Dependabot PRs.
   - Run full audit.
   - Prioritize by severity + reachability.
   - Update + test + merge (or defer with justification).

7. **Output**:
   - Exact audit commands for the languages in the project.
   - Sample report interpretation.
   - Recommended Dependabot / Renovate config.
   - License allow-list policy.
   - Dependency review checklist for PRs.

## Examples

A complete weekly dependency review process for a Node + Python monorepo, including audit commands, a sample Dependabot config that groups security updates, license policy, and a PR template for dependency updates is included.

## Edge Cases & Error Handling

- **Transitive vulnerabilities**: Most tools surface them; focus effort on direct deps you can actually change.
- **No patch available**: Use mitigation (e.g., network controls, input sanitization) + monitor for fix.
- **License conflicts**: Legal review for copyleft in certain contexts.

## Verification

1. Full audit runs cleanly or with only accepted/low findings.
2. License check passes against the allow-list.
3. Dependabot/Renovate is configured and creating PRs.
4. A known vulnerable dependency (intentionally added) is detected and a fix PR is opened.
5. Success: The project has a repeatable process that keeps dependencies reasonably current and free of critical known vulnerabilities and problematic licenses.

## References

- [npm audit](https://docs.npmjs.com/cli/v8/commands/npm-audit)
- [pip-audit](https://pypi.org/project/pip-audit/)
- [Dependabot](https://docs.github.com/en/code-security/dependabot)
- [Renovate](https://docs.renovatebot.com/)
- [FOSSA](https://fossa.com/)
- [Socket.dev](https://socket.dev/)
- [deps.dev](https://deps.dev/)
