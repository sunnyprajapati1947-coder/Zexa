---
name: css-animation-crafter
description: Creates CSS keyframe animations, transitions, and micro-interactions. Use when adding motion to web UIs without JavaScript animation libraries.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: css, animation, keyframes, transitions, accessibility, micro-interactions
---

## Overview

Produces high-quality, performant CSS animations and transitions using modern best practices. The skill generates keyframe definitions, timing functions, accessibility-respecting motion (prefers-reduced-motion), GPU-accelerated properties, stagger patterns, scroll-driven animations, and ready-to-use recipes for common UI motions such as fades, slides, bounces, loading states, and hover effects.

## When to Use This Skill

- Adding subtle motion to buttons, cards, modals, loaders, or page transitions.
- The user explicitly requests "CSS animation", "keyframe", "transition", "micro-interaction", or "motion".
- Avoiding JavaScript animation libraries (Framer Motion, GSAP, anime.js) for performance or bundle size reasons.
- Implementing loading states, success/error feedback, or attention-guiding animations.
- Creating scroll-triggered or entrance animations.

## Prerequisites

- A web project using CSS (plain CSS, Tailwind, SCSS, etc.).
- Target browsers that support modern CSS (Chrome 90+, Firefox 90+, Safari 15+ recommended for advanced features like `@property` or scroll timelines).
- For scroll-driven animations, the page must have scrollable content.
- No JavaScript required unless the skill explicitly adds a tiny progressive enhancement script.

## Steps

1. **Analyze the motion requirement**:
   - Identify the trigger (hover, focus, load, click, scroll, state change).
   - Determine the animation type: entrance, exit, attention, feedback, loading, or continuous.
   - Choose properties that are GPU-composited: `transform` (translate, scale, rotate), `opacity`, `filter`. Avoid animating `width`, `height`, `left`, `top`, `margin`, `padding` when possible.

2. **Respect user motion preferences (mandatory)**:
   - Always wrap animations in `@media (prefers-reduced-motion: no-preference) { ... }`.
   - Provide a reduced or static fallback for users who prefer reduced motion.
   - Never animate on load for users with reduced motion unless it is essential.

3. **Select timing and easing**:
   - Use `cubic-bezier()` for custom easings (e.g., `cubic-bezier(0.4, 0, 0.2, 1)` for material design).
   - Common durations: 150ms (micro), 250-300ms (standard), 400-600ms (emphasis), 800ms+ (page-level).
   - Use `animation-fill-mode: both` or `forwards`/`backwards` as needed.
   - Prefer `transition` for simple state changes; use `@keyframes` + `animation` for complex or repeating sequences.

4. **Write the keyframes**:
   - Name them descriptively (e.g., `fadeInUp`, `pulse`, `modalEnter`).
   - Use percentage-based or `from`/`to`.
   - Keep keyframe lists short (3-5 stops maximum for most UI work).

5. **Implement stagger for lists**:
   - Use `animation-delay` with incremental values (e.g., `calc(var(--i) * 80ms)`).
   - Set `--i` via inline style or CSS counters on list items.

6. **Add scroll-driven animations** (modern):
   - Use `animation-timeline: view()` or `scroll()` when supported.
   - Provide a JavaScript fallback using IntersectionObserver for older browsers.

7. **Provide multiple recipe variants**:
   - Always deliver the animation in a self-contained code block.
   - Show how to apply it to real HTML elements.
   - Include Tailwind arbitrary value versions when relevant.

8. **Include performance and accessibility notes**:
   - List which properties are safe.
   - Warn about `will-change` usage (use sparingly).
   - Document how the animation respects reduced motion.

9. **Output complete, copy-pasteable code**:
   - Include the CSS (and minimal HTML demo if helpful).
   - Add comments explaining key decisions.

## Examples

**Example 1: Fade + Slide Up Entrance Animation (with stagger)**

```css
/* Fade In Up Animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: no-preference) {
  .fade-in-up {
    animation: fadeInUp 400ms cubic-bezier(0.4, 0, 0.2, 1) both;
  }
  
  /* Staggered list items */
  .stagger-list > * {
    --stagger-delay: 80ms;
    animation-delay: calc(var(--i, 0) * var(--stagger-delay));
  }
}

/* Usage */
<div class="stagger-list">
  <div class="fade-in-up" style="--i: 0">Item 1</div>
  <div class="fade-in-up" style="--i: 1">Item 2</div>
  <div class="fade-in-up" style="--i: 2">Item 3</div>
</div>
```

**Example 2: Subtle Button Micro-interaction (Scale + Shadow)**

```css
@media (prefers-reduced-motion: no-preference) {
  .btn-primary {
    transition: transform 150ms cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 150ms cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  .btn-primary:hover {
    transform: translateY(-1px) scale(1.02);
    box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  }
  
  .btn-primary:active {
    transform: translateY(0) scale(0.985);
    transition-duration: 75ms;
  }
}
```

**Example 3: Loading Spinner (Infinite, GPU only)**

```css
@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: no-preference) {
  .spinner {
    width: 24px;
    height: 24px;
    border: 3px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 9999px;
    animation: spin 800ms linear infinite;
  }
}
```

**Example 4: Scroll-Driven Fade (with fallback)**

```css
/* Modern scroll-driven */
@media (prefers-reduced-motion: no-preference) and (prefers-reduced-motion: no-preference) {
  @supports (animation-timeline: view()) {
    .scroll-fade {
      animation: fadeIn linear both;
      animation-timeline: view();
      animation-range: entry 0% entry 50%;
    }
  }
}

/* JS fallback for older browsers */
.scroll-fade {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 400ms ease, transform 400ms ease;
}

.scroll-fade.is-visible {
  opacity: 1;
  transform: none;
}
```

(Include a small IntersectionObserver script in the output when using the fallback.)

**Example 5: Attention Pulse (for notifications)**

```css
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

@media (prefers-reduced-motion: no-preference) {
  .attention-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  }
}
```

## Edge Cases & Error Handling

- **User has `prefers-reduced-motion: reduce`**: Always provide a no-animation path. For loading spinners that are essential, use a static indicator + ARIA live region instead of infinite animation.
- **Animation causes layout thrashing**: Only animate `transform` and `opacity`. If the user requests width/height animation, provide a `transform: scale` alternative and explain the performance difference.
- **Too many staggered items**: Cap stagger at ~10-12 items or use a CSS variable that the agent can adjust. Suggest IntersectionObserver + class toggle for very long lists.
- **Browser support**: For advanced features (scroll timelines, `@property`), always provide a progressive enhancement comment and a basic fallback.
- **Accessibility**: Never use animation to convey critical information without a static alternative. For attention animations, also use color or icon changes.
- **Performance on low-end devices**: Recommend testing with DevTools throttling. Suggest `will-change: transform` only on the animating element and remove it after the animation ends.
- **Conflict with Tailwind**: Show how to use arbitrary values (`animate-[spin_800ms_linear_infinite]`) and how to extend Tailwind config with custom keyframes.

## Verification

1. Paste the generated CSS + HTML into a test file and open in Chrome, Firefox, and Safari.
2. **Reduced motion test**: Set `prefers-reduced-motion: reduce` in DevTools (Rendering panel) — confirm animations are disabled or greatly simplified.
3. **Performance check**: Use Chrome DevTools Performance tab while triggering the animation. Confirm no layout thrashing (purple bars minimal) and GPU compositing (green bars for the layer).
4. **Accessibility**: Use keyboard to trigger hover/focus states. Verify focus is never lost due to animation. Run axe or Lighthouse — motion-related issues should be absent.
5. **Stagger verification**: Inspect computed `animation-delay` values on list items; they should increment correctly.
6. Success: Animations are smooth (60fps), respect user preferences, use only safe properties, and enhance (not distract from) the UI.

## References

- [MDN CSS Animations](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations)
- [MDN CSS Transitions](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions)
- [prefers-reduced-motion on MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- [Scroll-driven Animations Spec](https://drafts.csswg.org/css-animations-2/#scroll-driven-animations)
- [CSS Triggers](https://csstriggers.com/) — which properties cause layout/paint
- [Cubic-bezier.com](https://cubic-bezier.com) for custom easing visualization
