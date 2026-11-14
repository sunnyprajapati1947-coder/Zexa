---
name: jwt-security-auditor
description: Audits JWT implementation for common security vulnerabilities. Use when reviewing authentication systems that use JSON Web Tokens.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: jwt, json-web-token, authentication, security-audit, alg-confusion, storage
---

## Overview

Audits JWT implementations for common and critical vulnerabilities. Covers JWT structure review (header alg, "none" attack, RS256 vs HS256), signature validation, expiry and clock skew handling, sensitive data in payload, token storage (httpOnly cookies vs localStorage), refresh token security, algorithm confusion attacks, and a comprehensive JWT audit checklist with code-level indicators and fixes.

## When to Use This Skill

- Reviewing or implementing authentication that uses JWTs.
- Auditing an existing auth system (especially custom JWT code).
- The user mentions "JWT", "JSON Web Token", "access token", or is building login/refresh flows.

## Prerequisites

- The JWT implementation code (issuance, validation, refresh).
- Example tokens (valid, expired, malformed).
- Knowledge of how tokens are stored and transmitted on the client.

## Steps

1. **Decode and inspect sample tokens** (use jwt.io or `jwt decode`):
   - Header: `alg`, `typ`, `kid`.
   - Payload: claims (`sub`, `exp`, `iat`, `aud`, `iss`, scopes/roles, any PII?).
   - Signature present and looks valid.

2. **Algorithm & signature validation audit**:
   - Never allow `alg: "none"`.
   - For asymmetric (RS256/ES256): verify with public key, never secret.
   - For symmetric (HS256): use a strong, long, random secret; never hardcode.
   - Check that the library is actually verifying the signature (many footguns in older or custom code).
   - Algorithm confusion (HS256 with public key as secret) — test if the implementation is vulnerable.

3. **Claims validation**:
   - `exp` is checked and enforced (with small clock skew tolerance, e.g., 30-60s).
   - `aud` and `iss` are validated against expected values.
   - `iat` / `nbf` considered where relevant.
   - No critical business logic decisions based solely on unverified claims.

4. **Token storage & transmission**:
   - httpOnly + Secure + SameSite cookies (strongly preferred for web).
   - Never localStorage or sessionStorage for access or refresh tokens (XSS risk).
   - Short-lived access tokens (5-15 min) + rotating refresh tokens.
   - Refresh tokens stored securely (httpOnly cookie or secure backend session) and rotated on use.

5. **Refresh & revocation**:
   - Refresh token rotation (old refresh token is invalidated when a new one is issued).
   - Refresh token reuse detection (if the same old token is presented again → revoke the whole family and force re-login).
   - Ability to revoke individual sessions or all sessions for a user (e.g., on password change or suspected compromise).

6. **Output**:
   - JWT audit checklist (with pass/fail + evidence + severity).
   - Code-level red flags to search for ("alg", "verify", "localStorage.setItem", hard-coded secrets, long-lived tokens, etc.).
   - Recommended secure patterns (httpOnly cookie issuance, refresh rotation, library usage).
   - Test cases (none alg, alg confusion, expired token, missing signature, etc.).
   - Remediation steps for each finding.

## Examples

A complete JWT audit report for a typical custom JWT implementation (using `jsonwebtoken` in Node) with several issues (long-lived tokens, localStorage, missing audience check, no refresh rotation, potential alg confusion due to custom verification) plus the exact fixes and test vectors is included.

## Edge Cases & Error Handling

- **Clock skew between services**: Allow small `exp` leeway but not too much.
- **Key rotation (kid)**: Support multiple public keys during rotation; never use the same key forever.
- **Token binding** (advanced): Consider DPoP or mTLS-bound tokens for high-security scenarios.

## Verification

1. Run the audit checklist against the implementation — findings are documented with evidence.
2. Test vectors (none alg, expired, wrong audience, alg confusion) are run against the validation code — vulnerable paths are identified.
3. After remediation, the same test vectors are rejected.
4. Token storage is verified in browser (httpOnly cookie, no tokens in localStorage).
5. Success: The JWT implementation follows current best practices and resists the common attacks in the checklist.

## References

- [JWT.io](https://jwt.io/)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [RFC 7519 - JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [Auth0 / Okta JWT Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [Refresh Token Rotation](https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)
