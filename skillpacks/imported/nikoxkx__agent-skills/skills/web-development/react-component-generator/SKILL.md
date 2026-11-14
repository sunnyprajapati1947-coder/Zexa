---
name: react-component-generator
description: Generates production-ready React functional components with TypeScript, props interface, default props, and JSDoc. Use when scaffolding new React components from descriptions or design specs.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: react, typescript, components, functional, props, storybook
---

## Overview

Creates complete, production-grade React functional components using TypeScript. The skill outputs a component with a strict `Props` interface (using `interface` or `type`), sensible default props via destructuring, full JSDoc, proper `forwardRef` when needed, `React.memo` guidance, `data-testid` attributes for testing, a basic Storybook story stub, and accessibility considerations baked in.

## When to Use This Skill

- Scaffolding a new UI component in a React + TypeScript project.
- The user provides a component name, list of props, behavior description, or a design spec/wireframe.
- You need consistent, high-quality component boilerplate that follows team conventions (props naming, JSDoc, testing attributes).
- Starting a component library, design system, or feature with many similar components.

## Prerequisites

- Existing React project (Next.js, Vite, CRA, or custom) using TypeScript.
- Component library conventions already established (or the skill will propose sensible defaults).
- `react` and `@types/react` installed (version 18+ recommended).
- For Storybook stories: Storybook 7+ or 8+ configured in the project.
- Optional but recommended: `clsx` or `tailwind-merge` for className merging if using Tailwind.

## Steps

1. **Gather component specification**:
   - Component name (PascalCase).
   - List of props with types and whether they are required.
   - Behavioral description (what it does, variants, states).
   - Accessibility requirements.
   - Whether it needs `ref` forwarding, children, or complex state.
   - Styling approach (Tailwind, CSS Modules, styled-components, plain CSS).

2. **Define the Props interface**:
   - Use `interface ComponentNameProps { ... }` (preferred for declaration merging).
   - Make optional props explicit with `?`.
   - Use union types for variants (e.g., `variant?: 'primary' | 'secondary' | 'danger'`).
   - Include `className?: string` and `children?: React.ReactNode` where appropriate.
   - Add JSDoc to every prop.

3. **Implement the component function**:
   - Use arrow function with explicit return type `React.FC<ComponentNameProps>` or just the function for better tree-shaking.
   - Destructure props with defaults: `const { variant = 'primary', ... } = props;`.
   - Apply `React.forwardRef` when the component renders a DOM element that should expose a ref (buttons, inputs, etc.).
   - Use `React.memo` only when the component is pure and props are frequently stable (document the decision).

4. **Add accessibility and ARIA**:
   - Include `aria-*` attributes based on role and state.
   - Use semantic HTML elements inside the component.
   - Add `role` only when necessary (avoid over-using).

5. **Include testing helpers**:
   - Add `data-testid={testId || 'component-name'}` on the root or key interactive elements.
   - Suggest a basic test file structure using React Testing Library.

6. **Generate a Storybook story stub**:
   - Create a `.stories.tsx` file with the component imported.
   - Include controls for all variants and states.
   - Add a "Playground" story and 2-3 specific stories (e.g., "Primary", "Disabled", "WithIcon").

7. **Handle styling**:
   - If Tailwind: use `clsx` or template literals with conditional classes.
   - Provide a `cn` utility example if the project doesn't have one.
   - Keep style logic inside the component or extract to a separate `variants.ts` when complex.

8. **Add JSDoc and displayName**:
   - Top-level JSDoc describing the component purpose and usage.
   - `Component.displayName = 'ComponentName';` for better debugging in React DevTools.

9. **Output files**:
   - The main component file (`ComponentName.tsx`).
   - The story file (`ComponentName.stories.tsx`).
   - Optional: a basic test file skeleton.
   - Usage example in the skill response.

10. **Recommend follow-up**:
    - If form-related, suggest `form-validator`.
    - If animation needed, suggest `css-animation-crafter`.

## Examples

**Example 1: Button Component**

**User request**: "Create a Button component in React + TS. Variants: primary, secondary, ghost, danger. Sizes: sm, md, lg. Supports disabled, loading, left/right icon, and full width. Use Tailwind."

**Generated Component** (abbreviated for brevity in this example; full in real output):

```tsx
import React from 'react';
import { clsx } from 'clsx';

export interface ButtonProps {
  /** Visual style variant */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether the button is in a loading state */
  isLoading?: boolean;
  /** Left icon element */
  leftIcon?: React.ReactNode;
  /** Right icon element */
  rightIcon?: React.ReactNode;
  /** Make button take full width of container */
  fullWidth?: boolean;
  /** Disable the button */
  disabled?: boolean;
  children: React.ReactNode;
  className?: string;
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
}

/**
 * A versatile, accessible button component with multiple variants and states.
 * 
 * @example
 * <Button variant="primary" size="md">Click me</Button>
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      children,
      className,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
    
    const variantStyles = {
      primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
      secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500',
      ghost: 'text-gray-700 hover:bg-gray-100 focus:ring-gray-500',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    };

    const sizeStyles = {
      sm: 'px-3 py-1.5 text-sm gap-1.5',
      md: 'px-4 py-2 text-base gap-2',
      lg: 'px-6 py-3 text-lg gap-2.5',
    };

    return (
      <button
        ref={ref}
        type="button"
        disabled={disabled || isLoading}
        className={clsx(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          fullWidth && 'w-full',
          className
        )}
        aria-busy={isLoading}
        data-testid="button"
        {...props}
      >
        {isLoading && <span className="animate-spin mr-2">⏳</span>}
        {leftIcon && <span className="mr-2">{leftIcon}</span>}
        {children}
        {rightIcon && <span className="ml-2">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
```

**Storybook stub** also generated with all controls.

**Example 2: Card with children and ref forwarding** (similar detailed output).

## Edge Cases & Error Handling

- **Polymorphic component** (as="a" or as="div"): Provide an `as` prop using a generic or `asChild` pattern with Radix-style slot if the project uses it. Otherwise, keep it simple with a `Component` variable.
- **Complex children**: Document when to use `children` vs dedicated props (e.g., `title` and `description` for a card).
- **Performance**: If the component renders lists or has expensive children, document when to wrap with `React.memo` and provide a custom `areEqual` example.
- **TypeScript strictness**: Always use `strict` mode friendly types. Avoid `any`. Use `React.ComponentPropsWithoutRef<'button'>` for native props spreading when appropriate.
- **Icon libraries**: Show how to accept `React.ReactNode` for icons so any icon library works (Heroicons, Lucide, etc.).
- **Ref forwarding with generics**: Provide the correct generic signature for `forwardRef`.

## Verification

1. Create the files in the project.
2. Run `npm run build` or `tsc --noEmit` — zero TypeScript errors.
3. Import and render the component in a page or Storybook. Verify it matches the spec.
4. Open React DevTools — confirm `displayName` is set and props look clean.
5. Run Storybook and interact with all controls.
6. Write a quick test using the `data-testid` and run it with your test runner.
7. Check accessibility with axe or Lighthouse on a story that exercises all states.
8. Success: Component is typed correctly, renders without warnings, passes tests, and is easy for other developers to use and extend.

## References

- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Storybook for React](https://storybook.js.org/docs/react/get-started/introduction)
- [React.forwardRef Documentation](https://react.dev/reference/react/forwardRef)
- [React.memo](https://react.dev/reference/react/memo)
- Project's existing component library for style alignment (ask user for link or examples)
