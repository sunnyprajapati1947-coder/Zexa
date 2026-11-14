---
name: html-component-builder
description: Builds reusable, semantic HTML components from descriptions or wireframes. Use when creating UI elements like cards, modals, navbars, footers, forms, or any HTML structure without a JS framework.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: html, semantic, accessibility, components, ui
---

## Overview

Generates production-quality, semantic, accessible HTML5 components with inline or external CSS, proper ARIA attributes, responsive variants, and BEM or clear class naming. The skill transforms verbal descriptions, wireframes, or design specs into complete, copy-pasteable HTML that follows modern web standards.

## When to Use This Skill

- The user asks to build a UI element (card, modal, navbar, form, table, accordion, etc.) using plain HTML/CSS/JS (no React, Vue, etc.).
- You need a semantic, accessible starting point before adding a framework.
- Creating prototypes, landing pages, emails, or static sites.
- The request mentions "HTML component", "pure HTML", "semantic markup", or provides a wireframe/sketch.
- You must ensure WCAG 2.1 AA compliance for the component.

## Prerequisites

- Basic understanding of HTML5, CSS3, and ARIA is assumed for the agent.
- Target project should support modern browsers (no IE11 support needed unless specified).
- For responsive work, assume mobile-first approach.
- If using external CSS, the project must have a place for component-specific styles (e.g., `components/` folder or a design system CSS file).
- No external dependencies required (vanilla HTML + CSS + minimal JS).

## Steps

1. **Clarify requirements** if the description is ambiguous. Ask for or infer: component name/purpose, key content sections, interactive states (hover, focus, open/closed), responsive breakpoints, accessibility needs, and whether to use inline styles, a `<style>` block, or external CSS file.

2. **Choose semantic HTML structure**:
   - Use the most appropriate elements: `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`, `<form>`, `<fieldset>`, `<button>`, `<dialog>`, etc.
   - Never use `<div>` as the only wrapper when a more semantic tag exists.
   - Apply BEM naming: `block__element--modifier` (e.g., `card__title`, `modal__close--large`).

3. **Implement accessibility (WCAG 2.1 AA minimum)**:
   - Add `aria-*` attributes, `role` where needed (e.g., `role="dialog"` for modals, `aria-expanded` for accordions).
   - Provide visible focus states (outline or ring) and `tabindex` where appropriate.
   - Use `<label>` for all form controls with `for`/`id` matching. Use `aria-describedby` for error/help text.
   - Include `alt` text for all meaningful images; `aria-hidden="true"` for decorative ones.
   - Ensure keyboard operability for all interactive elements.

4. **Handle responsive design**:
   - Use mobile-first: base styles for mobile, then `@media (min-width: ...)` for larger screens.
   - Common breakpoints: 640px (sm), 768px (md), 1024px (lg), 1280px (xl).
   - Make components fluid with `max-width`, `width: 100%`, and flex/grid where appropriate.
   - Provide variants: e.g., stacked on mobile, side-by-side on desktop.

5. **Decide CSS strategy**:
   - **Inline styles**: Only for one-off prototypes or emails.
   - **`<style>` block** in the HTML file: Good for self-contained demos or single-file components.
   - **External CSS**: Preferred for production. Suggest creating `components/component-name.css` and link it. Use CSS custom properties for theming.
   - Always include a "plain" version and note how to extract to external.

6. **Add interactivity with minimal vanilla JS** (if needed):
   - Use `<details>`/`<summary>` for accordions where possible (no JS).
   - For modals, dropdowns, tabs: provide a small, commented `<script>` block using native APIs or a tiny vanilla implementation.
   - Prefer CSS-only solutions (e.g., `:checked` for toggles, `details`).

7. **Include customization slots / patterns**:
   - Document how to customize: CSS variables, data attributes, or named slots via comments.
   - Provide a "base" version and 1-2 variants (e.g., "compact", "featured").

8. **Add micro-copy and states**:
   - Include realistic placeholder text.
   - Show loading, error, empty, success, and disabled states where relevant.
   - Use proper heading hierarchy (never start with `<h1>` inside a component unless it's a page section).

9. **Output the complete component**:
   - Provide the full HTML in a single code block that can be copied into an `.html` file or into a larger document.
   - Include a comment at the top with usage instructions and customization notes.

10. **Provide verification and next steps**:
    - Tell the user how to test responsiveness, accessibility (keyboard + screen reader simulation), and performance.
    - Suggest follow-up skills if needed (e.g., `css-animation-crafter`, `form-validator`).

## Examples

**Example 1: Product Card Component**

**User request**: "Create a semantic HTML product card for an e-commerce site. It should show image, title, price, rating, short description, and an 'Add to Cart' button. Make it responsive and accessible. Use Tailwind classes for quick styling but keep it self-contained."

**Expected Output** (complete HTML):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Product Card Example</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8">
  <!-- Product Card Component -->
  <article 
    class="w-full max-w-sm mx-auto bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-200 hover:shadow-md transition-shadow"
    aria-labelledby="product-title"
  >
    <!-- Image -->
    <div class="relative aspect-[4/3] bg-gray-100">
      <img 
        src="https://picsum.photos/id/1011/400/300" 
        alt="Wireless Noise-Cancelling Headphones in matte black with silver accents"
        class="w-full h-full object-cover"
        loading="lazy"
      >
      <!-- Badge -->
      <span class="absolute top-3 left-3 bg-emerald-600 text-white text-xs font-medium px-2.5 py-0.5 rounded-full">Bestseller</span>
    </div>

    <div class="p-5">
      <!-- Header -->
      <div class="flex items-start justify-between gap-2">
        <h3 id="product-title" class="text-lg font-semibold text-gray-900 leading-tight">
          Sony WH-1000XM5
        </h3>
        <div class="text-right">
          <span class="text-xl font-bold text-gray-900">$398</span>
          <span class="block text-xs text-gray-500 line-through">$448</span>
        </div>
      </div>

      <!-- Rating -->
      <div class="flex items-center gap-1.5 mt-1.5" aria-label="4.8 out of 5 stars based on 1243 reviews">
        <div class="flex text-amber-400" aria-hidden="true">
          ★★★★☆
        </div>
        <span class="text-sm text-gray-600">4.8 <span class="text-gray-400">(1,243)</span></span>
      </div>

      <!-- Description -->
      <p class="mt-3 text-sm text-gray-600 line-clamp-2">
        Industry-leading noise cancelling headphones with 30-hour battery life and exceptional sound quality.
      </p>

      <!-- Actions -->
      <div class="mt-5 flex items-center gap-3">
        <button 
          type="button"
          class="flex-1 bg-gray-900 hover:bg-gray-800 active:bg-black text-white font-medium py-2.5 px-4 rounded-xl text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900"
          aria-label="Add Sony WH-1000XM5 to cart"
        >
          Add to Cart
        </button>
        
        <button 
          type="button"
          class="px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl border border-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900"
          aria-label="Save Sony WH-1000XM5 to wishlist"
        >
          ♡ Save
        </button>
      </div>
    </div>
  </article>
</body>
</html>
```

**Customization notes** (included in the skill output):
- Change image via `src` and `alt`.
- Use CSS variables or Tailwind config for brand colors.
- For external CSS, extract the Tailwind classes into a `product-card.css` file.

**Example 2: Accessible Modal Dialog**

**User request**: "Build an accessible confirmation modal for deleting an item. Include title, message, cancel and delete buttons. Make it keyboard accessible and announce properly to screen readers."

**Expected Output**: A complete `<dialog>` or div-based modal with `role="dialog"`, `aria-modal="true"`, focus trap (vanilla JS), proper button labels, and escape key handling. Full code provided with comments explaining each ARIA attribute.

## Edge Cases & Error Handling

- **Ambiguous description**: Default to a sensible semantic structure and explicitly note assumptions (e.g., "Assumed this is a marketing card — added `article` instead of `section`").
- **Image-heavy component**: Always require `alt` text. Provide guidance on using `srcset` for responsive images.
- **Complex interactions**: If the user requests heavy JS (e.g., drag-and-drop), provide a progressive enhancement note and suggest a follow-up skill or library.
- **Dark mode**: Include a `prefers-color-scheme` or class-based dark variant using CSS custom properties.
- **Performance**: Warn against large inline SVGs or base64 images unless necessary. Recommend `loading="lazy"` and `decoding="async"`.
- **Internationalization**: Use semantic elements and note that copy should be externalized for i18n.
- **Very small viewports**: Test the component at 320px width and provide overflow/scroll strategies.

## Verification

1. Copy the generated HTML into a `.html` file and open in a browser.
2. **Visual & responsive check**: Resize the window through all breakpoints (320px, 768px, 1024px+). Verify no overflow or broken layouts.
3. **Keyboard test**: Tab through all interactive elements. Confirm visible focus rings, logical order, and that modals/accordions are operable with keyboard only.
4. **Accessibility audit**:
   - Run the component through [axe DevTools](https://www.deque.com/axe/devtools/) browser extension — zero critical violations.
   - Use a screen reader (VoiceOver on Mac or NVDA) to verify announcements match visible content.
5. **Semantic validation**: Run the HTML through [Nu HTML Checker](https://validator.w3.org/nu/) — no errors.
6. **Color contrast**: Use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) or Lighthouse — minimum 4.5:1 for text.
7. Success criteria: Component renders cleanly, is fully keyboard + screen reader usable, and matches the original description without extra divitis.

## References

- [MDN HTML Elements Reference](https://developer.mozilla.org/en-US/docs/Web/HTML/Element)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Web Content Accessibility Guidelines (WCAG) 2.1](https://www.w3.org/TR/WCAG21/)
- [BEM Naming Convention](https://getbem.com/)
- [HTML5 Semantics Guide](https://html.spec.whatwg.org/multipage/semantics.html)
