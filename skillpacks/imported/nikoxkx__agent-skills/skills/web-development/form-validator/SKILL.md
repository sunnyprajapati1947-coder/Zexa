---
name: form-validator
description: Implements client-side and server-side form validation with accessible error messaging. Use when adding validation to any HTML or React form.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: forms, validation, zod, react-hook-form, accessibility, error-handling
---

## Overview

Implements robust, accessible form validation that works on both client and server. The skill produces validation schemas (Zod recommended), real-time and submit-time validation strategies, accessible error display patterns (`aria-invalid`, `aria-describedby`), common field validators (email, phone, password strength, date ranges, file uploads), and full integration examples with React Hook Form + Zod or vanilla HTML forms.

## When to Use This Skill

- Building or improving any form (login, registration, checkout, settings, multi-step wizards).
- The user mentions "form validation", "validate input", "error messages", or provides a form description.
- You need both client-side (UX) and server-side (security) validation.
- Ensuring WCAG-compliant error presentation.

## Prerequisites

- Form framework decided (plain HTML + JS, React, React Hook Form, Formik, etc.).
- Validation library: `zod` (strongly recommended), `yup`, or `joi`.
- For React: `react-hook-form` + `@hookform/resolvers` is the modern standard.
- Server-side endpoint that will receive the form data.
- Accessibility knowledge (or the skill will guide).

## Steps

1. **Identify all fields and validation rules**:
   - Required/optional.
   - Type (text, email, number, date, file, etc.).
   - Format rules (min/max length, regex, range).
   - Cross-field validation (password confirmation, date start < end).
   - File-specific rules (type, size, count).

2. **Create a single source of truth schema** (Zod):
   - Define once, use for client (via resolver) and server (parse).
   - Use `.refine()` for cross-field rules.
   - Add `.transform()` for sanitization when safe.

3. **Decide validation timing strategy**:
   - **Real-time (onChange/onBlur)**: Best UX for long forms. Show errors as user types or leaves field.
   - **Submit-time only**: Simpler for short forms or when you want to avoid error noise.
   - Hybrid: Validate on blur + full validation on submit.
   - Document the chosen strategy and why.

4. **Implement accessible error display**:
   - Every invalid field gets `aria-invalid="true"`.
   - Error message gets a unique `id` and is referenced via `aria-describedby`.
   - Error messages are placed immediately after the input (or in a live region for complex cases).
   - Never rely on color alone; use icon + text.
   - For screen readers, use `role="alert"` on error containers when appropriate.

5. **Common field patterns** (include ready-to-use validators):
   - Email: `z.string().email()`
   - Phone: regex or `libphonenumber-js`
   - Password: length + complexity rules + confirmation match
   - Date ranges: custom refine
   - File upload: size, mime type, multiple files
   - URL, slug, username availability (async)

6. **React Hook Form + Zod integration** (most common):
   - `useForm({ resolver: zodResolver(schema) })`
   - `register` with proper props.
   - `FormProvider` for nested or complex forms.
   - `setError` for server-side errors after submit.

7. **Server-side validation**:
   - Always re-validate with the same schema.
   - Return field-specific errors in a consistent shape.
   - Never trust client-only validation.

8. **Output**:
   - Zod schema file or inline.
   - Client form component (or vanilla JS + HTML).
   - Server handler snippet.
   - Example of error response shape.
   - Accessibility notes and test instructions.

## Examples

**Example 1: Registration Form (React + React Hook Form + Zod)**

```tsx
// schemas/registration.ts
import { z } from 'zod';

export const registrationSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
    .regex(/[0-9]/, 'Must contain at least one number'),
  confirmPassword: z.string(),
  fullName: z.string().min(2).max(100),
  acceptTerms: z.boolean().refine(val => val === true, {
    message: 'You must accept the terms and conditions',
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

export type RegistrationInput = z.infer<typeof registrationSchema>;
```

```tsx
// components/RegistrationForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { registrationSchema, type RegistrationInput } from '@/schemas/registration';

export function RegistrationForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegistrationInput>({
    resolver: zodResolver(registrationSchema),
    mode: 'onBlur',
  });

  const onSubmit = async (data: RegistrationInput) => {
    // Server call here — server will also validate
    const res = await fetch('/api/register', { method: 'POST', body: JSON.stringify(data) });
    // handle response...
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          {...register('email')}
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? 'email-error' : undefined}
          className={errors.email ? 'border-red-500' : ''}
        />
        {errors.email && (
          <p id="email-error" role="alert" className="text-red-600 text-sm mt-1">
            {errors.email.message}
          </p>
        )}
      </div>
      {/* more fields... */}
      <button type="submit" disabled={isSubmitting}>Create account</button>
    </form>
  );
}
```

**Server-side validation snippet** also provided.

**Example 2: Vanilla HTML + JS form** with the same schema logic (using Zod in browser via CDN or bundled).

## Edge Cases & Error Handling

- **Async validation** (username availability): Use `useForm`'s `validate` or server-side only + debounced check. Show loading state on the field.
- **Server returns field errors after submit**: Use `setError(field, { type: 'server', message: 'Taken' })` for each field.
- **Very long forms / multi-step**: Validate only the current step on "Next". Keep one schema or split into step schemas.
- **File validation**: Check `file.size` and `file.type` client-side, but always re-validate on server (never trust client file metadata).
- **International phone numbers**: Recommend `libphonenumber-js` or `react-phone-number-input`.
- **Password managers**: Never disable autocomplete on login/registration fields.
- **Error message clarity**: Write messages that tell the user what to do, not just what is wrong ("Enter a valid email" vs "Invalid email format").

## Verification

1. Fill the form with valid data → submits successfully.
2. Submit with each invalid field one-by-one → correct, accessible error appears next to the field.
3. Test keyboard navigation and screen reader (VoiceOver/NVDA) — errors are announced when they appear.
4. Run axe DevTools on the form in error state — no violations related to forms or ARIA.
5. Submit the same invalid data directly to the server endpoint (bypass client) — server rejects with proper 422 and field errors.
6. Test password mismatch, file too large, etc.
7. Success: Users can correct errors without confusion. Screen reader users understand problems. Server is protected. No validation bypass possible.

## References

- [React Hook Form + Zod](https://react-hook-form.com/get-started#SchemaValidation)
- [Zod](https://zod.dev/)
- [WebAIM Form Validation](https://webaim.org/techniques/forms/validation)
- [ARIA Authoring Practices - Form](https://www.w3.org/WAI/ARIA/apg/patterns/form/)
- [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
