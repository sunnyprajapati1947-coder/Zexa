---
name: api-security-auditor
description: Audits REST or GraphQL APIs for OWASP API Top 10 vulnerabilities. Use when reviewing or testing the security of an API before launch or after changes.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: api-security, owasp-api-top-10, authentication, authorization, bola, idor, injection
---

## Overview

Performs a structured security audit of REST or GraphQL APIs against the OWASP API Security Top 10. Provides detection methods (code review + testing), authentication/authorization review, BOLA/IDOR testing procedure, injection point identification, rate limiting testing, and a professional audit report template with findings, risk ratings, and remediation recommendations.

## When to Use This Skill

- Before launching a new API or major version.
- After significant changes to auth, authorization, or data access logic.
- As part of a security review or bug bounty prep.
- The user asks for an "API security audit" or "OWASP API Top 10 review".

## Prerequisites

- Access to the API source code and/or a running instance (staging preferred).
- Authentication credentials or tokens for different roles/users (if testing with auth).
- Tools: Postman/Insomnia or curl, Burp Suite or ZAP (for proxying), or custom scripts.

## Steps

1. **OWASP API Top 10 2023 checklist** (with detection method for each):
   - API1:2023 Broken Object Level Authorization (BOLA/IDOR)
   - API2:2023 Broken Authentication
   - API3:2023 Broken Object Property Level Authorization
   - API4:2023 Unrestricted Resource Consumption (rate limiting, DoS)
   - API5:2023 Broken Function Level Authorization
   - API6:2023 Unrestricted Access to Sensitive Business Flows
   - API7:2023 Server Side Request Forgery (SSRF)
   - API8:2023 Security Misconfiguration
   - API9:2023 Improper Inventory Management
   - API10:2023 Unsafe Consumption of APIs (third-party)

2. **Authentication & session review**:
   - JWT validation (alg, exp, signature, claims).
   - Token storage and transmission.
   - OAuth scopes and PKCE.
   - Password/reset flows.

3. **Authorization testing (BOLA/IDOR)**:
   - Systematically change IDs in requests (user_id, order_id, document_id) while authenticated as different users.
   - Test horizontal (same role, different user) and vertical (lower role accessing higher).
   - GraphQL: test for missing authorization on every field/resolver.

4. **Injection & input validation**:
   - SQLi, NoSQLi, command injection in query params, body, headers.
   - Mass assignment / over-posting.
   - GraphQL: introspection enabled in prod? deep nesting DoS?

5. **Rate limiting & resource limits**:
   - Test with high volume from one IP / one user.
   - Check for per-user vs per-IP limits.
   - Look for expensive operations without limits (search, export, report generation).

6. **Output**:
   - Structured audit report (Markdown template) with:
     - Executive summary
     - Findings table (OWASP item | Severity | Location | Evidence | Recommendation)
     - Positive findings (what is done well)
     - Remediation roadmap
   - Specific test cases / curl commands used.
   - Code-level indicators to look for in reviews.

## Examples

A complete audit report template filled with realistic findings for a typical REST + GraphQL API (BOLA on `/users/{id}/orders`, missing rate limit on search, JWT alg confusion, over-fetching in GraphQL, etc.) plus the exact test procedures and curl examples used to discover them is included.

## Edge Cases & Error Handling

- **Authorization logic in the client**: Flag as critical — server must always enforce.
- **GraphQL**: Field-level auth, query cost analysis, depth limiting.
- **Microservices**: Auth must be validated at every service boundary (or use a service mesh with mTLS + auth).

## Verification

1. The auditor follows the checklist and produces a report.
2. At least the critical/high findings have clear reproduction steps.
3. Code review confirms the vulnerable patterns exist (or the fix is in place).
4. Re-test after remediation — the issue is closed.
5. Success: The API has no critical OWASP API Top 10 issues, or they are explicitly accepted with compensating controls and timelines.

## References

- [OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x00-header/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [GraphQL Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html)
- [JWT Security](https://jwt.io/)
