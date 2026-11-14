---
name: penetration-test-planner
description: Creates a structured penetration testing plan for web applications and APIs. Use when planning a security assessment, red team exercise, or bug bounty program.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: penetration-testing, red-team, bug-bounty, threat-modeling, owasp, scope
---

## Overview

Creates a professional, scoped penetration testing plan including scope definition, rules of engagement, threat modeling (STRIDE per component), reconnaissance checklist, testing methodology mapped to OWASP Testing Guide / ASVS, tool recommendations per attack category, timeline, deliverables, and a report template.

## When to Use This Skill

- Engaging an external penetration testing firm or red team.
- Running an internal red team exercise.
- Launching or scaling a bug bounty program.
- Preparing for a compliance-driven assessment (SOC 2, etc.).

## Prerequisites

- The application or system to be tested (staging or production with care).
- Clear business and technical owners.
- Budget and timeline.

## Steps

1. **Scope definition** (template):
   - In-scope: specific domains, IP ranges, applications, APIs, mobile apps, cloud accounts, people (social engineering?).
   - Out-of-scope: production customer data, certain endpoints, third-party services, physical, etc.
   - Testing types: black/gray/white box, authenticated vs unauthenticated.

2. **Rules of engagement (RoE)**:
   - Allowed techniques (DDoS? social? physical?).
   - Time windows.
   - Notification procedures (who to contact on finding critical issues).
   - Data handling and destruction after the test.
   - Legal protections (get-out-of-jail-free letter if needed).

3. **Threat modeling**:
   - Draw data flow diagrams.
   - Apply STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) to each component/trust boundary.
   - Prioritize high-impact, high-likelihood threats.

4. **Testing methodology & tools** (per OWASP):
   - Recon: subfinder, amass, Shodan, etc.
   - Web app: Burp Suite Pro, ZAP, sqlmap, ffuf, etc.
   - API: Postman + custom scripts, GraphQL-specific tools.
   - Auth: jwt_tool, etc.
   - Infrastructure: nmap, nuclei, etc.

5. **Timeline & phases**:
   - Recon & mapping (1-2 days).
   - Active testing (3-7 days).
   - Reporting & debrief (2 days).
   - Retest window (optional).

6. **Deliverables**:
   - Executive summary.
   - Detailed findings (severity, reproduction, impact, recommendation, evidence).
   - Risk rating (CVSS or custom).
   - Remediation roadmap.
   - Debrief call.

7. **Output**:
   - Complete penetration test plan document (Markdown) with all sections filled for a typical web + API + cloud application.
   - Scope template.
   - RoE template.
   - Tool list by category.
   - Sample finding write-up.
   - Questions to ask the testing team.

## Examples

A full 8-10 page penetration testing plan for a SaaS web app with REST + GraphQL API, including detailed scope, RoE, STRIDE threat model summary, phased testing plan, tool matrix, and success criteria is included.

## Edge Cases & Error Handling

- **Production testing**: Strongly prefer staging; if production is required, extreme care with data and availability.
- **Third-party integrations**: Explicitly out of scope or require separate permission from the third party.
- **Red team vs pentest**: Clarify goals (find as many vulns as possible vs simulate real attacker with limited initial access).

## Verification

1. The plan is reviewed and signed off by security, engineering, and legal/business stakeholders.
2. The testing team (internal or external) confirms the scope and RoE are clear.
3. Testing proceeds without surprises or scope creep.
4. The final report is actionable and maps back to the original threat model.
5. Success: A high-quality, safe, well-scoped assessment that finds real issues and drives meaningful remediation.

## References

- [OWASP Testing Guide v4](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [PTES (Penetration Testing Execution Standard)](http://www.pentest-standard.org/)
- [STRIDE](https://en.wikipedia.org/wiki/STRIDE_(security))
- [Bugcrowd / HackerOne methodology guides](https://www.bugcrowd.com/)
