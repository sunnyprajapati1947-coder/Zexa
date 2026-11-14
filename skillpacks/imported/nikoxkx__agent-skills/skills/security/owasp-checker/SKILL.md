---
name: owasp-checker
description: Reviews a web application against the OWASP Top 10 vulnerabilities. Use when performing a security review or preparing a security assessment report.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: owasp-top-10, web-security, a1-injection, a3-xss, a5-broken-access-control, security-review
---

## Overview

Reviews a web application against the OWASP Top 10 (2021) vulnerabilities with code-level indicators, automated scanner integration, manual test procedures, remediation examples, and a structured finding report template. Provides a practical, developer-friendly checklist that can be used in code reviews, architecture reviews, or as input to a penetration test.

## When to Use This Skill

- Performing a security review of a web application or feature.
- Preparing for a penetration test or bug bounty launch.
- Training developers on common web vulnerabilities.
- The user asks for an "OWASP Top 10 review" or "web app security audit".

## Prerequisites

- Access to the application source code and a running instance (staging ideal).
- Ability to perform both automated scans and manual testing.
- (Helpful) Previous findings or known issues.

## Steps

1. **OWASP Top 10 2021 quick reference** (with detection + remediation for each):
   - A01:2021 – Broken Access Control
   - A02:2021 – Cryptographic Failures
   - A03:2021 – Injection (SQL, NoSQL, Command, etc.)
   - A04:2021 – Insecure Design
   - A05:2021 – Security Misconfiguration
   - A06:2021 – Vulnerable and Outdated Components
   - A07:2021 – Identification and Authentication Failures
   - A08:2021 – Software and Data Integrity Failures
   - A09:2021 – Security Logging and Monitoring Failures
   - A10:2021 – Server-Side Request Forgery (SSRF)

2. **Automated scanning**:
   - DAST: OWASP ZAP, Burp Suite, Nikto, Nuclei.
   - SAST: Semgrep (with OWASP rules), SonarQube, CodeQL, Snyk Code.
   - SCA: Snyk, Dependabot, Trivy.
   - Record findings with location and severity.

3. **Manual / code review per category**:
   - Look for specific anti-patterns (e.g., string concatenation in SQL queries, missing `HttpOnly` on cookies, direct object references without authz checks, etc.).
   - Test with real (or realistic) data and different user roles.

4. **Prioritized findings**:
   - Use CVSS or a simple Critical/High/Medium/Low.
   - Include reproduction steps, impact, and concrete remediation (with code example when possible).

5. **Output**:
   - Structured OWASP Top 10 review report (Markdown) with:
     - Summary table (Axx | Status | Severity | # Findings)
     - Detailed findings per category (or "None found" with evidence of review).
     - Positive security controls observed.
     - Prioritized remediation roadmap.
   - Code search patterns / Semgrep rules for the common issues.
   - Manual test checklist.

## Examples

A complete OWASP Top 10 review for a realistic web application (with findings in Broken Access Control, Injection, Security Misconfiguration, Vulnerable Components, and Identification failures, plus "clean" categories with the checks that were performed) is included, along with remediation code snippets and a sample executive summary.

## Edge Cases & Error Handling

- **Modern frameworks mitigate many issues by default** (e.g., parameterized queries in ORMs, auto-escaping in templates): still verify they are actually being used and not bypassed.
- **Client-side only protections**: Always flag as insufficient.
- **Third-party components**: Cross-reference with SCA results.

## Verification

1. The review covers all 10 categories with evidence (scans + code review + manual tests).
2. High/critical findings have clear reproduction and impact.
3. Remediation guidance is specific and actionable (not "fix the vulnerability").
4. Re-review after fixes shows improvement.
5. Success: The application has a documented security posture against the OWASP Top 10, with known gaps tracked and prioritized.

## References

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Semgrep OWASP Rules](https://semgrep.dev/r?q=owasp)
- [ZAP / Burp](https://www.zaproxy.org/, https://portswigger.net/burp)
