---
name: performance-auditor
description: Audits web application performance and generates an actionable improvement plan. Use when a web app is slow, fails Lighthouse checks, or has poor Core Web Vitals scores.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: performance, lighthouse, web-vitals, bundle-analysis, optimization
---

## Overview

Performs a structured performance audit using Lighthouse, the `web-vitals` library, bundle analyzers, network waterfall analysis, and caching review. Produces a prioritized, actionable fix list with estimated impact and implementation effort for each issue.

## When to Use This Skill

- A page or app feels slow.
- Lighthouse score is low (<90 in Performance).
- User complains about load time, interactivity, or layout shift.
- Preparing for a performance budget or before a major launch.

## Prerequisites

- The running application (local dev or deployed preview).
- Node.js for running Lighthouse CLI.
- Access to build output for bundle analysis.
- Browser DevTools.

## Steps

1. **Run Lighthouse**:
   ```bash
   npx lighthouse https://example.com --view --preset=desktop
   npx lighthouse https://example.com --view --preset=mobile
   ```

2. **Measure real user metrics**:
   - Add `web-vitals` library and log to console or analytics.
   - Or use Chrome DevTools Performance panel + Web Vitals extension.

3. **Bundle analysis**:
   - For webpack/Next.js: `next build` + `ANALYZE=true` or `webpack-bundle-analyzer`.
   - Identify large dependencies, duplicate code, unused exports.

4. **Network waterfall review**:
   - Record in DevTools Network tab (disable cache).
   - Look for: render-blocking resources, large unoptimized images, many small requests, no compression, long TTFB.

5. **Caching & headers audit**:
   - Check `Cache-Control`, `ETag`, `Last-Modified`.
   - Recommend immutable assets for hashed files, stale-while-revalidate for others.

6. **Image & media optimization**:
   - Use `next/image` or `<picture>` + modern formats (AVIF, WebP).
   - Proper `width`/`height` or aspect-ratio to prevent CLS.
   - Lazy loading.

7. **JavaScript & interactivity**:
   - Code splitting, dynamic imports.
   - Defer non-critical scripts.
   - Optimize event handlers and re-renders (React Profiler).

8. **Generate prioritized fix list**:
   - Format: Issue | Current metric | Target | Effort | Impact | How to fix (concrete steps).

9. **Output**:
   - Lighthouse report summary.
   - Bundle size breakdown.
   - Specific code patches for top 5-7 issues.
   - Monitoring recommendation (add web-vitals to analytics).

## Examples

Sample Lighthouse command output interpretation, a typical "top issues" report, and concrete fixes (e.g., "Replace this 1.2MB hero image with next/image + AVIF", "Add `loading="lazy"` to below-the-fold images", "Split this heavy modal into dynamic import") are provided.

## Edge Cases & Error Handling

- **Third-party scripts**: Identify and suggest async/defer or partytown.
- **Large vendor bundles**: Recommend tree-shaking, replacing heavy libs (e.g., moment → date-fns).
- **SPA vs MPA**: Different strategies for each.

## Verification

1. Re-run Lighthouse after fixes — score improvement documented.
2. Measure LCP, CLS, INP before/after with web-vitals.
3. Bundle size reduced (compare `next build` output).
4. Real user metrics improve in analytics.
5. Success: Measurable, sustained improvement in user-perceived performance.

## References

- [Lighthouse](https://developer.chrome.com/docs/lighthouse/)
- [web-vitals](https://github.com/GoogleChrome/web-vitals)
- [webpack-bundle-analyzer](https://github.com/webpack-contrib/webpack-bundle-analyzer)
- [Next.js Performance](https://nextjs.org/docs/app/building-your-application/optimizing)
- [web.dev Performance](https://web.dev/performance/)
