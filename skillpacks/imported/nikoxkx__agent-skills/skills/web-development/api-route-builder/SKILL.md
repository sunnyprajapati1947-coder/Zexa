---
name: api-route-builder
description: Designs and implements RESTful or tRPC API routes with input validation, error handling, and OpenAPI documentation. Use when building backend routes in Next.js, Express, Fastify, or similar.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: api, rest, trpc, validation, zod, openapi, error-handling
---

## Overview

Designs and implements secure, well-documented API routes following REST conventions or tRPC patterns. The skill produces route handlers with strong input validation (Zod or Joi), consistent error responses, proper HTTP status codes, rate limiting stubs, security headers, middleware ordering, and OpenAPI/Swagger annotations or tRPC router definitions.

## When to Use This Skill

- Creating or refactoring backend API endpoints (Next.js App Router, Express, Fastify, tRPC).
- The user describes a resource or action ("user profile", "create order", "list products with filters").
- You need consistent error handling, validation, and documentation across an API.
- Preparing an API for production or for consumption by frontend/mobile clients.

## Prerequisites

- Backend framework decided (Next.js API routes / App Router, Express, Fastify, tRPC + Next.js, etc.).
- Validation library installed or ready to install (`zod`, `joi`, `yup`).
- Authentication/authorization strategy known (JWT, sessions, API keys, OAuth).
- Database or service layer that the route will call.
- For OpenAPI: `swagger-ui-express`, `redoc`, or built-in Next.js OpenAPI tooling.

## Steps

1. **Determine API style and resource**:
   - REST (resource-oriented, HTTP verbs) vs tRPC (type-safe procedures).
   - Resource name (plural for collections, e.g., `/users`, `/orders`).
   - Action for non-CRUD (e.g., `POST /orders/{id}/cancel`).

2. **Select HTTP method and status codes** (use this table):
   | Method | Success | Created | No Content | Common Errors |
   |--------|---------|---------|------------|---------------|
   | GET    | 200     | —       | —          | 404, 400      |
   | POST   | 200/201 | 201     | —          | 400, 409, 422 |
   | PUT    | 200     | —       | 204        | 400, 404, 409 |
   | PATCH  | 200     | —       | 204        | 400, 404      |
   | DELETE | 200/204 | —       | 204        | 404, 409      |

3. **Define input validation schema** (Zod recommended):
   - Path params, query params, body, headers.
   - Use `.strict()` to reject unknown fields.
   - Coerce types where safe (e.g., `z.coerce.number()` for IDs from URLs).
   - Provide human-friendly error messages.

4. **Implement consistent error response format**:
   ```json
   {
     "error": {
       "code": "VALIDATION_ERROR",
       "message": "Invalid input",
       "details": [...]
     }
   }
   ```
   - Define a small set of standard error codes.

5. **Structure the handler**:
   - Parse & validate input first.
   - Authorize the request (call auth middleware or check session).
   - Perform business logic (call service/repository).
   - Return success response or throw/return typed error.
   - Use try/catch with centralized error handler.

6. **Add middleware chain** (in order):
   - CORS (if needed)
   - Rate limiting
   - Body parser (framework default)
   - Authentication
   - Authorization / RBAC
   - Validation (or do inside handler)
   - Logging / request ID

7. **Add rate limiting stub**:
   - Use `express-rate-limit`, `upstash/ratelimit`, or Next.js middleware.
   - Document the limits (e.g., 100 requests per 15 minutes per IP for public endpoints).

8. **Document with OpenAPI**:
   - Add JSDoc or comment annotations that tools can convert (or use `zod-to-openapi`).
   - Include request/response schemas, auth requirements, error responses.

9. **Security checklist** (always apply):
   - Validate all input (never trust client).
   - Use parameterized queries / ORM to prevent SQL injection.
   - Sanitize output (especially user-generated content).
   - Set security headers (Helmet or manual: CSP, HSTS, X-Frame-Options, etc.).
   - Return generic error messages to clients; log full details server-side.
   - Implement proper CORS (never `*` in production).

10. **Output the complete route + supporting code**:
    - The route/handler file.
    - Zod schemas in a separate `schemas.ts` if complex.
    - Example curl or HTTP request.
    - Test suggestions.

## Examples

**Example 1: Create User (POST /api/users) - Next.js App Router + Zod**

```ts
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  password: z.string().min(8).max(128),
}).strict();

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = CreateUserSchema.parse(body);

    // TODO: hash password, check for existing user, create in DB
    const user = await createUser(data);

    return NextResponse.json(
      { id: user.id, email: user.email, name: user.name },
      { status: 201 }
    );
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'Invalid input', details: error.errors } },
        { status: 422 }
      );
    }
    console.error('Create user error:', error);
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'Something went wrong' } },
      { status: 500 }
    );
  }
}
```

**OpenAPI annotation example** also included.

**Example 2: tRPC Procedure** (similar complete router definition).

## Edge Cases & Error Handling

- **Validation fails**: Return 422 with structured `details` array. Never leak internal validation library names.
- **Resource not found**: Return 404 with a standard error body. Do not distinguish "not found" vs "no permission" for security.
- **Rate limit exceeded**: Return 429 with `Retry-After` header.
- **Concurrent modification (409)**: For optimistic locking or unique constraint violations.
- **Large payloads**: Enforce body size limits at the framework level + document in the route.
- **Idempotency**: For POST that should be idempotent, require an `idempotency-key` header and implement deduplication.
- **Authentication failures**: Always return 401 (not 403) for missing/invalid credentials. 403 only for insufficient permissions on a known identity.

## Verification

1. Add the route to the project and run the dev server.
2. Test with curl or Postman using the exact examples provided.
3. Send invalid payloads — verify 422 responses with clear messages.
4. Check that sensitive fields (passwords, tokens) are never returned in responses.
5. Run `npm run build` — TypeScript clean.
6. If OpenAPI generated, open Swagger UI and confirm the endpoint appears with correct schemas.
7. Load test the rate limiting (use `ab` or `hey`).
8. Success: All happy paths return correct status + shape. Error paths return consistent error objects. No secrets leaked. Validation prevents bad data.

## References

- [REST API Design Best Practices](https://restfulapi.net/)
- [Zod Documentation](https://zod.dev/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x00-header/)
- [RFC 7807 Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)
- Framework-specific docs (Next.js Route Handlers, Express, tRPC)
