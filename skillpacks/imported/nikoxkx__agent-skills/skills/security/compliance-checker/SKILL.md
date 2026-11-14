---
name: compliance-checker
description: Checks application and infrastructure compliance against SOC 2, GDPR, HIPAA, or PCI-DSS requirements. Use when preparing for compliance audits or implementing regulatory requirements.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: compliance, soc2, gdpr, hipaa, pci-dss, audit, evidence, policy
---

## Overview

Helps prepare for and perform gap analyses against major compliance frameworks (SOC 2, GDPR, HIPAA, PCI-DSS). Includes framework comparison, control categories, automated evidence collection (AWS Config, CloudTrail, etc.), policy and procedure templates, gap analysis procedure, evidence artifact checklist, and a realistic audit preparation timeline.

## When to Use This Skill

- Preparing for a SOC 2 Type I or II audit, GDPR assessment, HIPAA compliance project, or PCI-DSS assessment.
- Building or maturing a compliance program.
- The user mentions "SOC 2", "GDPR", "HIPAA", "PCI", "compliance audit", or "evidence collection".

## Prerequisites

- The systems, processes, and policies to be assessed.
- Access to cloud provider consoles, ticketing system, HR system, etc. for evidence.
- (For formal audits) An auditor or assessor engaged.

## Steps

1. **Framework selection & scoping**:
   - SOC 2 (common for SaaS — security, availability, confidentiality, processing integrity, privacy).
   - GDPR (EU data protection — consent, rights, transfers, DPIA, etc.).
   - HIPAA (US healthcare — administrative, physical, technical safeguards).
   - PCI-DSS (cardholder data — 12 requirements, SAQ or ROC).

2. **Control mapping**:
   - List the relevant controls from the chosen framework(s).
   - Map each control to existing or needed policies, technical controls, and evidence sources.

3. **Gap analysis**:
   - For each control: Implemented? Partially? Not implemented?
   - Document current state, gap, owner, target date, evidence needed.
   - Prioritize by risk and audit timeline.

4. **Evidence collection (automated where possible)**:
   - AWS: Config rules, CloudTrail, IAM Access Analyzer, GuardDuty findings, S3 bucket policies, etc.
   - GCP / Azure equivalents.
   - Application: access logs, change management tickets, incident records, vulnerability scan reports, access reviews.
   - HR / vendor: background check records, NDA repository, vendor risk assessments.

5. **Policy & procedure development**:
   - Information security policy, access control, change management, incident response, vendor management, data retention, etc.
   - Use templates from frameworks or reputable sources; customize to your org.

6. **Audit preparation timeline** (example for SOC 2 Type II):
   - 3-6 months before: gap analysis, remediate critical gaps, implement monitoring.
   - 1-2 months: collect evidence, run access reviews, update policies.
   - During audit: respond to requests quickly, have a single point of contact.

7. **Output**:
   - Gap analysis spreadsheet or Notion page (controls × status × evidence × owner).
   - Evidence collection checklist per framework.
   - Policy templates (or links to good public ones).
   - Sample evidence package structure.
   - 90-day preparation timeline with milestones.
   - Common pitfalls and how to avoid them.

## Examples

A realistic SOC 2 Type II gap analysis for a growing SaaS company (with ~40 controls mapped, many already implemented via AWS + basic policies, gaps in formal access reviews and vendor management), plus a 12-week preparation plan and evidence checklist is included. Similar high-level guidance for GDPR and HIPAA.

## Edge Cases & Error Handling

- **Multi-framework** (SOC 2 + GDPR + HIPAA): Map once to a unified control framework (e.g., using a GRC tool) to avoid duplicate work.
- **Inherited controls** (from cloud providers): Use the provider's SOC 2 / ISO reports + bridge letters.
- **Evidence that is hard to produce**: Automate as much as possible; for manual processes, create recurring calendar tasks.

## Verification

1. Gap analysis is complete and reviewed by security + legal.
2. Critical gaps have owners and target dates before the audit window.
3. Evidence for a sample of controls can be produced on demand within minutes (automated) or hours (manual).
4. Policies are approved and communicated.
5. Mock audit or pre-assessment with the auditor goes smoothly.
6. Success: The organization passes the audit with no (or only minor) findings, and the process is repeatable for future audits.

## References

- [AICPA SOC 2](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-attest-standards/soc-2)
- [GDPR.eu](https://gdpr.eu/)
- [HHS HIPAA](https://www.hhs.gov/hipaa/index.html)
- [PCI Security Standards](https://www.pcisecuritystandards.org/)
- [Vanta, Drata, Secureframe](https://www.vanta.com/) (compliance automation platforms — great for evidence collection)
- [AWS Compliance](https://aws.amazon.com/compliance/)
