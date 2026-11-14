---
name: threat-model-designer
description: Creates a structured threat model for an application using STRIDE or PASTA methodology. Use when designing security into a new system or assessing an existing one.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: threat-modeling, stride, pasta, data-flow-diagram, risk, mitigation
---

## Overview

Creates a structured, actionable threat model using STRIDE (or PASTA) methodology. Includes data flow diagram creation, trust boundary identification, threat enumeration worksheet, risk rating (likelihood × impact), mitigation mapping, and a complete threat model document template that can be maintained as living documentation.

## When to Use This Skill

- Designing security controls for a new system or major feature.
- Assessing the security posture of an existing application before a pentest or launch.
- Onboarding new team members to the security context of a product.
- The user says "threat model this", "what are the threats to X", or provides an architecture diagram.

## Prerequisites

- Architecture diagrams or a clear description of components, data flows, and trust boundaries.
- Knowledge of the data being processed (especially sensitive/PII data).
- Stakeholders who can validate assumptions (engineering, product, security).

## Steps

1. **Draw the system** (Data Flow Diagram - DFD):
   - External entities (users, other systems).
   - Processes (your services, functions).
   - Data stores (databases, caches, S3, etc.).
   - Data flows (arrows with labels: "user credentials", "order data", "JWT").
   - Trust boundaries (dashed lines: "internet", "DMZ", "internal VPC", "app trust boundary").

2. **Identify trust boundaries**:
   - Where does untrusted input enter?
   - Where does privileged data cross from one component to another?
   - Where are different privilege levels (unauth, user, admin, service-to-service)?

3. **Enumerate threats using STRIDE** (per element or per flow):
   - **S**poofing (authentication)
   - **T**ampering (integrity)
   - **R**epudiation (non-repudiation / logging)
   - **I**nformation Disclosure (confidentiality)
   - **D**enial of Service (availability)
   - **E**levation of Privilege (authorization)

4. **Rate each threat**:
   - Likelihood (Low/Medium/High) — considering attacker motivation, capability, and current controls.
   - Impact (Low/Medium/High) — data sensitivity, blast radius, business harm.
   - Risk = Likelihood × Impact (or use DREAD / custom matrix).

5. **Map mitigations**:
   - For each high/medium risk threat, list existing or planned controls.
   - Note residual risk after mitigation.
   - Assign owners and target dates for missing mitigations.

6. **Document**:
   - Executive summary.
   - DFD (Mermaid or draw.io export).
   - Threat table (ID, element, STRIDE category, description, likelihood, impact, risk, mitigation, status).
   - Assumptions and out-of-scope items.
   - Recommendations and open questions.

7. **Maintain as living doc**:
   - Revisit on major architecture changes.
   - Link findings to tickets or ADRs.
   - Review before pentests or launches.

8. **Output**:
   - Complete threat model document (Markdown) for a realistic web application (SPA + API + DB + background jobs + third-party integrations).
   - Mermaid DFD source.
   - Threat enumeration worksheet (table template).
   - Risk rating guidance.
   - Example mitigations for common web threats.

## Examples

A full threat model for a typical SaaS application (user-facing web app, REST/GraphQL API, Postgres, Redis, background workers, S3, third-party payment + email providers) with ~25-30 enumerated threats, risk ratings, and mitigations is included, along with the DFD and a maintenance checklist.

## Edge Cases & Error Handling

- **Complex microservices**: Focus on inter-service trust boundaries and authz between services.
- **Third-party services**: Treat as external entities; document what you trust them with and what compensating controls you have.
- **Evolving architecture**: Version the threat model alongside the architecture docs.

## Verification

1. The DFD accurately reflects the current (or planned) architecture (validated by engineers).
2. All major trust boundaries and data flows are covered.
3. High-risk threats have concrete mitigations (or explicit acceptance with compensating controls).
4. The document is understandable by both security and engineering teams.
5. New team members can read it and understand the key security considerations.
6. Success: Security is designed in from the start (or gaps in an existing system are clearly documented and prioritized).

## References

- [STRIDE](https://en.wikipedia.org/wiki/STRIDE_(security))
- [PASTA Threat Modeling](https://versprite.com/pasta-threat-modeling/)
- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [Microsoft Threat Modeling Tool](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool)
- [Data Flow Diagrams in Threat Modeling](https://owasp.org/www-community/Threat_Modeling_Process#data-flow-diagrams)
