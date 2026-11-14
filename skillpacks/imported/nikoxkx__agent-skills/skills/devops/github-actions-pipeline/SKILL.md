---
name: github-actions-pipeline
description: Creates GitHub Actions CI/CD pipelines with build, test, lint, and deploy stages. Use when setting up or improving automated workflows in GitHub.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: github-actions, ci-cd, workflow, caching, deploy, vercel, aws
---

## Overview

Designs complete, efficient GitHub Actions workflows for CI and CD. Includes triggers, job matrices, intelligent caching (npm/pip/pnpm/yarn), secret management, conditional execution, artifact handling, and deployment patterns to common platforms (Vercel, AWS, GCP, Fly.io, self-hosted).

## When to Use This Skill

- Setting up CI for a new repository.
- Improving slow, flaky, or expensive existing pipelines.
- Adding deployment automation.

## Prerequisites

- GitHub repository with Actions enabled.
- Tests, linters, and build commands already defined in package.json / Makefile / etc.
- Secrets configured in GitHub repo settings (or org level).

## Steps

1. **Define triggers** (on push to main, PRs, manual, schedule for nightly).

2. **Create jobs**:
   - `lint`
   - `test` (with matrix for node versions or browsers if needed)
   - `build`
   - `deploy` (only on main, after tests pass)

3. **Caching**:
   - Use `actions/cache` or `actions/setup-node` with cache for node_modules / pnpm store.
   - Cache Docker layers when building images.

4. **Secrets & environments**:
   - Use `${{ secrets.VAR }}`.
   - Protect production deploys with Environments + required reviewers.

5. **Conditional steps** and `needs:` for dependency.

6. **Reusable workflows** for common patterns across repos.

7. **Deployment examples**:
   - Vercel (using `vercel` action or CLI).
   - AWS (ECS, Lambda, S3 + CloudFront).
   - Fly.io, Railway, Render, etc.

8. **Output**:
   - Full `.github/workflows/ci.yml` and `cd.yml` (or combined).
   - Required secrets list.
   - How to add environments.

## Examples

A production-grade CI workflow with pnpm caching, parallel jobs, and a CD workflow that deploys to Vercel on main (with preview deploys on PRs) is included, plus patterns for AWS and Docker-based deploys.

## Edge Cases & Error Handling

- **Flaky tests**: Add retry logic or quarantine jobs.
- **Long builds**: Use `actions/cache` aggressively and consider self-hosted runners for very large repos.
- **Secret leaks**: Never `echo` secrets; use `::add-mask::`.

## Verification

1. Push a PR — CI runs and reports status.
2. Merge to main — CD triggers and deploys successfully.
3. Check Actions tab for clean logs and artifacts.
4. Success: Every PR is validated, main is always deployable, deploys are automatic and safe.

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [actions/cache](https://github.com/actions/cache)
- [Vercel GitHub Integration](https://vercel.com/docs/concepts/git/vercel-for-github)
