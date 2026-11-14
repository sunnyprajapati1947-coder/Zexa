---
name: ci-cd-optimizer
description: Analyzes and optimizes CI/CD pipeline speed, reliability, and cost. Use when pipelines are slow, flaky, or expensive.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: ci-cd, optimization, caching, flaky-tests, parallelization, cost
---

## Overview

Provides a systematic 5-step workflow to diagnose and fix slow, flaky, or costly CI/CD pipelines. Covers bottleneck identification, parallelization, smart test selection, caching hierarchy, artifact reuse, flaky test quarantine, and cost optimization techniques with concrete before/after metrics and GitHub Actions examples.

## When to Use This Skill

- Pipelines take too long (developers are waiting).
- High flakiness rate.
- CI costs are rising.
- User says "make the build faster" or "fix flaky tests".

## Prerequisites

- Existing CI configuration (GitHub Actions, GitLab CI, etc.).
- Access to CI logs, timing data, and cost reports.
- Test suite that can be run locally for experimentation.

## Steps

1. **Measure current state**:
   - Record wall time for full pipeline on main.
   - Identify the slowest job(s) from timing graphs.
   - Count flaky test rate (retries needed).

2. **Parallelize**:
   - Split large jobs (e.g., test into shard by file or by package).
   - Use matrix strategy.
   - Run independent jobs in parallel (`needs:` only where required).

3. **Caching hierarchy** (most impactful):
   - Dependencies (node_modules, pip cache, Go modules).
   - Build cache (Next.js, Turborepo, Gradle, etc.).
   - Docker layer cache.
   - Test results / coverage cache.

4. **Smart test selection**:
   - Changed-files detection (only run tests for packages that changed).
   - Use tools like `nx affected`, Turborepo, or custom scripts.
   - Quarantine known flaky tests into a separate "flaky" job that runs less often.

5. **Artifact & reuse**:
   - Upload build artifacts from build job and download in deploy/test jobs instead of rebuilding.
   - Use `actions/cache` or native cache features.

6. **Cost optimization**:
   - Use larger runners only when needed.
   - Cancel in-progress workflows on new pushes to same branch.
   - Self-hosted runners for high-volume repos.

7. **Output**:
   - Diagnosis report template.
   - Optimized workflow diff.
   - Flaky test handling pattern.
   - Before/after timing expectations.

## Examples

A before/after GitHub Actions workflow showing parallel test sharding, aggressive caching, affected tests only, and cancellation is included, along with a flaky test quarantine pattern.

## Edge Cases & Error Handling

- **Monorepos**: Use workspace-aware tools (Nx, Turborepo, pnpm workspaces).
- **Flaky tests that are actually bugs**: Quarantine + create ticket, do not ignore.
- **Cache invalidation bugs**: Provide cache key best practices (hash of lockfile + OS).

## Verification

1. Re-run the pipeline multiple times and record new average duration.
2. Flaky test rate drops (tracked in CI logs or a dashboard).
3. Cost report shows reduction (if applicable).
4. Developers report faster feedback on PRs.
5. Success: Pipeline is 30-70% faster, reliable, and cheaper while maintaining the same quality gates.

## References

- [GitHub Actions Caching](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows)
- [Turborepo Remote Caching](https://turbo.build/repo/docs/core-concepts/remote-caching)
- [Nx Affected](https://nx.dev/nx/affected)
- [Flaky Test Management](https://testing.googleblog.com/2021/04/flaky-tests-10-years-later.html)
