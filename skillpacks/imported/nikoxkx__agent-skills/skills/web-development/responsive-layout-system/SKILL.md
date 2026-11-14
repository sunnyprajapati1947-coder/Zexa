---
name: responsive-layout-system
description: Creates a responsive layout using CSS Grid and Flexbox with mobile-first breakpoints. Use when building page layouts that must work across all screen sizes.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: css, responsive, grid, flexbox, layout, mobile-first, container-queries
---

## Overview

Designs and implements robust, maintainable responsive page and component layouts using modern CSS (Grid for 2D, Flexbox for 1D), mobile-first methodology, CSS custom property design tokens for spacing and breakpoints, container queries where appropriate, and common layout patterns (sidebar, holy grail, masonry, dashboard).

## When to Use This Skill

- Building the overall page layout or major sections (header, hero, main content, sidebar, footer).
- The user mentions "responsive", "mobile first", "works on all screen sizes", or provides a wireframe that needs to adapt.
- Creating reusable layout primitives for a design system.
- When performance and simplicity are priorities over heavy layout libraries.

## Prerequisites

- CSS file or Tailwind setup in the project.
- Understanding of viewport vs container queries.
- Target breakpoints defined (or the skill will propose sensible ones: 640, 768, 1024, 1280).
- For advanced masonry or subgrid, modern browser support or fallbacks.

## Steps

1. **Define design tokens**:
   - Create CSS custom properties for spacing scale, container widths, and breakpoints.
   - Example: `--space-4: 1rem; --container-max: 1280px;`

2. **Choose layout primitives**:
   - Use Flexbox for one-dimensional flows (navbars, toolbars, button groups, card rows).
   - Use Grid for two-dimensional layouts (page templates, card grids, dashboards).
   - Consider subgrid and masonry for modern browsers.

3. **Apply mobile-first**:
   - Write base styles for the smallest screen (usually 320-375px).
   - Layer improvements with `min-width` media queries.
   - Never hide critical content on mobile; use progressive disclosure instead.

4. **Implement container queries** (preferred for components):
   - Use `@container` for components that should adapt to their parent width rather than viewport.
   - Fallback to media queries when container queries are not supported.

5. **Build common patterns**:
   - Holy grail (header, sidebar, main, footer)
   - Sidebar + content (collapsible on mobile)
   - Masonry grid
   - Dashboard (multiple resizable panels)
   - Sticky header + scrollable content area

6. **Handle safe areas and notches**:
   - Use `env(safe-area-inset-*)` for mobile devices.
   - Test on iPhone with notch/dynamic island.

7. **Add debug helpers** (optional but useful):
   - A temporary outline or grid overlay toggle for development.

8. **Output**:
   - Complete CSS (or Tailwind config + component classes).
   - HTML structure example.
   - Responsive demo notes.

## Examples

**Example: Holy Grail Layout with Sidebar**

```css
:root {
  --sidebar-width: 280px;
  --header-height: 64px;
}

.layout {
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar main"
    "footer footer";
  grid-template-rows: var(--header-height) 1fr auto;
  grid-template-columns: var(--sidebar-width) 1fr;
  min-height: 100dvh;
}

@media (max-width: 768px) {
  .layout {
    grid-template-areas:
      "header"
      "main"
      "footer";
    grid-template-columns: 1fr;
  }
  .sidebar { display: none; } /* or use a drawer pattern */
}

.header { grid-area: header; }
.sidebar { grid-area: sidebar; }
.main { grid-area: main; }
.footer { grid-area: footer; }
```

Full HTML + more patterns (masonry using `grid-template-columns: repeat(auto-fill, minmax(240px, 1fr))` with `masonry-auto-flow` or JS fallback) included in the skill output.

## Edge Cases & Error Handling

- **Very narrow screens (320px)**: Ensure no horizontal scroll. Use `overflow-x: hidden` on body and test all components.
- **Container vs viewport**: Prefer container queries for cards/grids that live in sidebars.
- **Print styles**: Provide a separate print stylesheet or `@media print` rules that collapse sidebars and optimize for paper.
- **High zoom levels**: Layouts must not break at 200%+ zoom (reflow, not zoom).
- **Dynamic content**: Account for variable height headers/footers using `min-height: 100dvh` and `grid`.

## Verification

1. Open the layout in browser and resize from 320px to 1920px.
2. Use DevTools device toolbar for iPhone, iPad, desktop.
3. Test with real devices if possible.
4. Run Lighthouse — no layout shift issues (CLS < 0.1).
5. Check that all content remains accessible and no overflow at any size.
6. Success: Layout adapts gracefully, no horizontal scroll, content hierarchy preserved on mobile.

## References

- [MDN CSS Grid](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)
- [MDN Flexbox](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout)
- [Container Queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Container_Queries)
- [Every Layout](https://every-layout.dev/)
- [CSS-Tricks Complete Guide to Grid](https://css-tricks.com/snippets/css/complete-guide-grid/)
