---
name: tailwind-design-system
description: Creates a Tailwind CSS design system with custom tokens, component classes, and dark mode. Use when establishing a consistent design language for a project.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: tailwind, design-system, tokens, dark-mode, css, components
---

## Overview

Establishes a complete, maintainable Tailwind CSS design system by extending the config with semantic design tokens (colors, spacing, typography, shadows, radii), creating reusable component classes via `@apply` or a component library approach, setting up dark mode (class or media), and providing plugin examples for custom utilities.

## When to Use This Skill

- Starting a new project that will use Tailwind and needs a design language from day one.
- Standardizing an existing Tailwind project that has inconsistent colors, spacing, or component styles.
- Building or contributing to a design system / component library.

## Prerequisites

- Tailwind CSS 3.4+ installed (or via CDN for prototypes).
- `tailwind.config.ts` or `.js` in the project root.
- PostCSS and build pipeline set up.
- Design tokens or brand guidelines (or the skill will propose a sensible neutral + accent system).

## Steps

1. **Audit current usage** (if existing project): Find all hard-coded colors, spacing, fonts.

2. **Design token architecture in tailwind.config.ts**:
   - Extend `theme.extend.colors` with semantic names (`primary`, `neutral`, `success`, `background`, `foreground`).
   - Use OKLCH or HSL for better dark mode and accessibility.
   - Define spacing scale, typography scale, border radius, box shadows as tokens.

3. **Dark mode setup**:
   - Preferred: `darkMode: 'class'` + `dark:` variants.
   - Alternative: `media` for system preference.
   - Provide a theme toggle component (button that adds/removes `dark` class on `<html>`).

4. **Component abstraction strategy**:
   - For simple components: use `@apply` in a `components.css` layer.
   - For complex or highly reusable: create actual React/Vue/Svelte components.
   - Document pros/cons of each approach.

5. **Create custom plugins** (optional but powerful):
   - Plugin for `text-balance`, `container-query` utilities, or brand-specific helpers.

6. **Output**:
   - Complete `tailwind.config.ts` with tokens and plugins.
   - `app/globals.css` or equivalent with layers and component classes.
   - 3 example custom components (Button, Card, Input) using the tokens.
   - Theme toggle implementation.
   - Documentation of the token system.

## Examples

Full recommended `tailwind.config.ts`, CSS layers, and three component examples (Button with variants, Card, Form Input) are included in the skill output, along with dark mode toggle code.

## Edge Cases & Error Handling

- **Design token drift**: Recommend a token studio or Figma Tokens plugin for sync.
- **Bundle size**: Use Tailwind's content paths correctly and purge in production.
- **Arbitrary values abuse**: Provide a "when to use arbitrary" guideline.

## Verification

1. Build the project — Tailwind classes generate correctly.
2. Toggle dark mode — all components adapt properly.
3. Check contrast ratios for primary/foreground pairs.
4. Success: New developers can use `bg-primary`, `text-foreground`, etc. consistently without guessing hex values.

## References

- [Tailwind CSS Configuration](https://tailwindcss.com/docs/configuration)
- [Tailwind Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [Designing with Tailwind CSS (book)](https://tailwindcss.com/)
- [OKLCH Color Space](https://oklch.com/)
