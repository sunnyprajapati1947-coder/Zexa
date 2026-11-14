---
name: nextjs-app-scaffold
description: Scaffolds a production Next.js 14+ App Router project with TypeScript, Tailwind, ESLint, Prettier, testing, and CI. Use when starting a new Next.js project from scratch.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: nextjs, app-router, typescript, tailwind, eslint, vercel, scaffold
---

## Overview

Provides a complete, production-ready Next.js 14+ (App Router) project scaffold including recommended directory structure, TypeScript strict config, Tailwind, ESLint + Prettier, testing setup (Jest or Vitest + React Testing Library), basic CI with GitHub Actions, environment variable conventions, middleware example, image optimization config, and a Vercel deployment checklist.

## When to Use This Skill

- Starting a brand new Next.js project.
- The user says "create a new Next.js app", "scaffold Next.js", or "set up a Next.js project with best practices".
- You want to avoid the default `create-next-app` minimal setup and jump straight to a hardened production template.

## Prerequisites

- Node.js 18.17+ or 20+.
- `npx create-next-app@latest` or manual setup.
- Git initialized.
- Vercel account (recommended for deployment) or other hosting.

## Steps

1. **Initialize the project**:
   ```bash
   npx create-next-app@latest . --yes --tailwind --eslint --yes --app
   ```

2. **Upgrade to latest stable** and install additional deps:
   - `typescript`, `@types/node`, `react`, `react-dom` (already there).
   - Add: `zod`, `clsx`, `tailwind-merge`, `@hookform/resolvers`, `react-hook-form` (common), `lucide-react` or heroicons.
   - Dev: `prettier`, `eslint-config-prettier`, `husky`, `lint-staged`, `@testing-library/react`, `jest` or `vitest`.

3. **Directory structure** (create these folders):
   ```
   app/
     (marketing)/          # route groups
     (dashboard)/
     api/
   components/
   lib/                    # utils, constants, db clients
   hooks/
   types/
   middleware.ts
   next.config.mjs         # hardened
   ```

4. **Configure next.config.mjs** with security and performance:
   - Headers for security.
   - Image remote patterns.
   - Experimental features if needed.
   - Output: 'standalone' for Docker if relevant.

5. **Set up environment variables**:
   - `.env.example`
   - `NEXT_PUBLIC_` for client-exposed.
   - Server-only vars loaded via `process.env` with Zod validation in `lib/env.ts`.

6. **Add middleware** for auth redirects, i18n, etc.

7. **Linting & formatting**:
   - `.eslintrc.json` extending recommended + prettier.
   - `.prettierrc`
   - `lint-staged` + husky pre-commit hook.

8. **Testing setup**:
   - Jest/Vitest config.
   - Example test for a component.
   - `testing-library` setup.

9. **GitHub Actions CI** (`.github/workflows/ci.yml`):
   - Install, lint, typecheck, test, build.

10. **Vercel / deploy checklist**:
    - Environment variables in dashboard.
    - Preview deployments.
    - Custom domain + HTTPS.
    - Analytics + Speed Insights.

## Examples

Full `next.config.mjs`, `lib/env.ts` Zod schema, sample `app/layout.tsx` with metadata, middleware example, and CI workflow are provided in the skill output.

## Edge Cases & Error Handling

- **Monorepo**: Note adjustments for Turborepo or Nx.
- **Internationalization**: Recommend `next-intl` or built-in.
- **Authentication**: Suggest adding `next-auth` or Lucia in a follow-up step.
- **Database**: Prisma or Drizzle setup guidance.

## Verification

1. `npm run dev` — app runs cleanly.
2. `npm run build` — successful production build.
3. `npm run lint` and typecheck pass.
4. Run tests.
5. Deploy to Vercel preview and verify.
6. Success: Project starts with all modern best practices, zero config debt on day one.

## References

- [Next.js 14 App Router Docs](https://nextjs.org/docs/app)
- [Vercel Deployment](https://vercel.com/docs)
- [Next.js Security Best Practices](https://nextjs.org/docs/app/building-your-application/security)
