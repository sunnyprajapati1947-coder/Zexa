---
name: auth-flow-builder
description: Implements authentication flows including login, registration, password reset, and session management. Use when adding auth to a web app using JWT, sessions, or OAuth.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: auth, jwt, oauth, sessions, nextauth, security, cookies
---

## Overview

Implements secure authentication flows (login, register, forgot password, reset, logout, session refresh) using modern best practices: httpOnly cookies for tokens (never localStorage), PKCE for OAuth, CSRF protection, refresh token rotation, and clear guidance on JWT vs session vs OAuth tradeoffs. Provides complete flows for NextAuth.js / Auth.js, custom JWT, and session-based approaches.

## When to Use This Skill

- Adding authentication to a new or existing web application.
- User requests "login page", "sign up", "protected route", "OAuth", or "session management".
- You need to choose between JWT, sessions, or OAuth and implement it securely.

## Prerequisites

- Backend framework (Next.js, Express, etc.).
- Database or user store (Prisma, Drizzle, or auth provider).
- For OAuth: provider credentials (Google, GitHub, etc.).
- HTTPS in production (mandatory for cookies and OAuth).

## Steps

1. **Choose auth strategy**:
   - **Sessions + httpOnly cookie**: Simplest, good for traditional apps.
   - **JWT in httpOnly cookie + refresh rotation**: Stateless, good for APIs and microservices.
   - **OAuth 2.1 + PKCE**: For third-party login (recommended when possible).
   - Compare pros/cons in the output.

2. **Secure token storage**:
   - Always httpOnly + SameSite=Strict/Lax + Secure cookies.
   - Never store tokens in localStorage or sessionStorage.

3. **Implement flows**:
   - Login: validate credentials → issue tokens/cookie → redirect.
   - Register: validate, hash password (bcrypt/argon2), create user.
   - Password reset: time-limited token via email, one-time use.
   - Refresh: short-lived access token + rotating refresh token.
   - Logout: clear cookies, invalidate refresh token on server.

4. **CSRF protection**: Use SameSite + double-submit cookie or framework built-in.

5. **Protected routes / middleware**:
   - Next.js middleware example that checks for valid session/JWT.
   - Redirect unauthenticated users to /login with return URL.

6. **NextAuth.js / Auth.js integration** (recommended for most Next.js apps):
   - Full config with credentials provider + Google/GitHub.
   - Custom pages.
   - Session callback to enrich user object.

7. **Output**:
   - Complete auth service functions.
   - Route handlers or API routes for each flow.
   - Middleware.
   - Frontend login/register forms (or point to form-validator skill).
   - Environment variable list.
   - Security checklist.

## Examples

Full NextAuth config, custom JWT login/register handlers with httpOnly cookies, password reset flow with email token, and protected route middleware are included.

## Edge Cases & Error Handling

- **Invalid/expired refresh token**: Force re-login, clear all cookies.
- **Brute force**: Rate limit login attempts per email/IP.
- **Email verification**: Optional but recommended step after registration.
- **Account linking**: For OAuth + credentials.
- **Session fixation**: Regenerate session on login.

## Verification

1. Register a new user.
2. Login — verify httpOnly cookie is set (inspect in DevTools → Application → Cookies).
3. Access a protected page while logged out — redirected to login.
4. Refresh the page while logged in — session persists.
5. Logout — cookie cleared.
6. Attempt password reset end-to-end.
7. Success: All flows work, no tokens in localStorage, cookies are httpOnly and secure-flagged in production.

## References

- [Auth.js / NextAuth.js Docs](https://authjs.dev/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [RFC 6749 OAuth 2.0 + PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [HTTP Cookie Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
