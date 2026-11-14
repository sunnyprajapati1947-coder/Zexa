---
name: accessibility-auditor
description: Audits web interfaces for WCAG 2.1 AA compliance and generates a prioritized fix list. Use when auditing accessibility, preparing for legal compliance, or improving inclusivity.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: accessibility, wcag, a11y, axe, audit, aria
---

## Overview

Performs a thorough accessibility audit against WCAG 2.1 AA (and notes AAA where relevant). Combines automated tools (axe-core, WAVE, Lighthouse), manual testing procedures (keyboard-only navigation, screen reader simulation, zoom, color contrast), common ARIA misuse patterns, and produces a prioritized fix list with severity, effort, and concrete remediation steps.

## When to Use This Skill

- Before launching a new feature or site.
- After a design or code change that affects UI.
- User requests an "accessibility audit", "a11y review", "WCAG compliance", or "make it accessible".
- Legal or procurement requirements (Section 508, ADA, etc.).

## Prerequisites

- The live page or a deployed preview.
- Browser DevTools + axe DevTools extension (or CLI).
- Screen reader (VoiceOver on Mac, NVDA on Windows — free).
- Color contrast tool (WebAIM or built into DevTools).

## Steps

1. **Automated scan**:
   - Run axe-core (browser extension or `axe-core` in CI).
   - Run Lighthouse Accessibility category.
   - Run WAVE (webaim.org/wave).
   - Record all violations with node selectors or screenshots.

2. **Manual keyboard test**:
   - Tab through the entire page.
   - Verify visible focus indicators on every interactive element.
   - Test all functionality (modals, dropdowns, carousels, forms) with keyboard only.
   - Check skip links, logical tab order, and no keyboard traps.

3. **Screen reader test**:
   - Use VoiceOver (Mac) or NVDA.
   - Listen to the page reading order.
   - Verify headings are logical (H1 → H2 etc.).
   - Check that images have alt text, form labels are announced, ARIA live regions work, and dynamic content is announced.
   - Test with rotor/landmarks.

4. **Color & contrast**:
   - Check all text and non-text (icons, buttons) against 4.5:1 (text) / 3:1 (large text, UI components).
   - Test in both light and dark modes if applicable.
   - Simulate color blindness (DevTools or Coblis).

5. **WCAG 2.1 AA checklist** (structured by POUR):
   - **Perceivable**: text alternatives, captions, contrast, resize text, reflow.
   - **Operable**: keyboard, enough time, seizures, navigable, input modalities.
   - **Understandable**: readable, predictable, input assistance.
   - **Robust**: compatible with assistive tech, valid markup.

6. **Common ARIA pitfalls to flag**:
   - `aria-hidden` on focusable elements.
   - Incorrect `role` or missing required ARIA attributes.
   - Over-use of `aria-label` instead of visible text.
   - `tabindex > 0`.

7. **Prioritized fix list**:
   - Severity: Critical (blocks users), High, Medium, Low.
   - Effort estimate.
   - Exact fix (code change or design change).
   - Success criteria for re-test.

8. **Output**:
   - Summary of automated + manual findings.
   - Full prioritized matrix.
   - Before/after code snippets for top issues.
   - Recommendations for ongoing monitoring (axe in CI, manual spot-checks).

## Examples

A sample audit report for a typical dashboard page (with 8-10 findings across categories) and remediation code for the most common issues (missing labels, focus management in modals, color contrast, keyboard navigation in custom components) are included.

## Edge Cases & Error Handling

- **Complex widgets** (data tables, date pickers, rich text editors): Recommend ARIA patterns from WAI-ARIA Authoring Practices or a well-tested library (React Aria, Radix).
- **Third-party components**: Audit them separately; suggest alternatives if they fail badly.
- **Dynamic content**: Ensure live regions and focus management on updates.

## Verification

1. Re-run axe and Lighthouse after fixes — critical violations = 0.
2. Perform the same keyboard + screen reader test — all flows work without assistance.
3. Contrast checker passes for all text/UI.
4. A real user who relies on assistive technology tests the flow (if possible).
5. Success: WCAG 2.1 AA conformance (or as close as the design allows), with documented exceptions if any.

## References

- [WCAG 2.1 Quickref](https://www.w3.org/WAI/WCAG21/quickref/)
- [WAI-ARIA Authoring Practices Guide (APG)](https://www.w3.org/WAI/ARIA/apg/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [WebAIM](https://webaim.org/)
- [Lighthouse Accessibility](https://developer.chrome.com/docs/lighthouse/accessibility/)
- [Inclusive Components](https://inclusive-components.design/)
