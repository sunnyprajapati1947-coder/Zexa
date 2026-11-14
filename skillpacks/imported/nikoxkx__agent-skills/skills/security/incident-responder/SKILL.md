---
name: incident-responder
description: Guides through the steps of a security incident response: detection, containment, eradication, and recovery. Use when a security incident occurs or when building an incident response plan.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: security
  tags: incident-response, ir, containment, forensics, runbook, post-mortem
---

## Overview

Provides a clear, actionable incident response playbook based on NIST / SANS phases (Preparation, Detection & Analysis, Containment, Eradication, Recovery, Lessons Learned). Includes severity classification, immediate containment checklists, evidence preservation, stakeholder notification templates (internal and external), forensic approach, root cause analysis template, and a post-incident review process.

## When to Use This Skill

- A security incident is suspected or confirmed (credential leak, unauthorized access, data exfiltration, malware, etc.).
- Building or improving an incident response plan / runbooks.
- Training the team on how to respond to incidents.
- After an incident for the post-mortem.

## Prerequisites

- An incident has been declared (or you are writing the plan in advance).
- Access to relevant systems (logs, cloud consoles, ticketing, communication channels).
- Pre-defined roles (Incident Commander, Communications Lead, Technical Lead, Legal, etc.).
- Contact lists and escalation paths.

## Steps

1. **Preparation** (do this now, before any incident):
   - Define severity levels (Sev 1 Critical, Sev 2 High, Sev 3 Medium, Sev 4 Low).
   - Create on-call rotation and escalation matrix.
   - Pre-authorize certain containment actions (e.g., "Incident Commander can disable a user or revoke tokens without further approval for Sev 1/2").
   - Maintain "go bags" / runbooks and access to forensic tools.
   - Tabletop exercises.

2. **Detection & Analysis**:
   - Triage the alert or report.
   - Determine if it is a real incident (vs false positive or bug).
   - Classify severity.
   - Assemble the response team.
   - Start a dedicated Slack/Teams channel + incident ticket.
   - Preserve evidence (do not reboot, image disks if possible, export logs with timestamps, take screenshots of consoles).

3. **Containment** (short-term & long-term):
   - Short-term: isolate affected systems/users (disable accounts, revoke tokens, block IPs, take instances out of LB, enable WAF rules).
   - Long-term: patch, re-image, rotate secrets, improve detection.
   - Document every containment action with time and who performed it.

4. **Eradication**:
   - Remove malware, backdoors, unauthorized accounts, malicious code.
   - Patch vulnerabilities that were exploited.
   - Rebuild affected systems from known-good images where possible.

5. **Recovery**:
   - Restore systems from backups (verify they are clean).
   - Gradually bring services back online with increased monitoring.
   - Validate that the threat is no longer present (re-scan, re-authenticate users, etc.).
   - Monitor for re-compromise.

6. **Lessons Learned / Post-Incident Review (PIR)**:
   - Blameless post-mortem within 1-2 weeks.
   - Timeline reconstruction.
   - What went well, what didn't, root cause (5 Whys or similar).
   - Action items with owners and due dates (fix the vulnerability, improve detection, update runbooks, training, etc.).
   - Update this playbook and other relevant docs.

7. **Communication**:
   - Internal: status updates at regular cadence (every 30-60 min for Sev 1).
   - External (customers, regulators, press): coordinated through legal/comms, factual, timely, empathetic.
   - Templates provided for initial notification, updates, and post-incident transparency report.

8. **Output**:
   - Incident severity matrix.
   - Immediate containment checklist (per common incident types: credential compromise, data breach, ransomware, supply chain, etc.).
   - Evidence preservation checklist.
   - Stakeholder notification templates (internal + customer).
   - Post-incident review template (timeline, 5 Whys, action items).
   - Sample runbook for "suspected credential leak".

## Examples

A complete, ready-to-use incident response playbook with severity definitions, role definitions, containment checklists for the top 5 incident types a web company faces, notification templates, and a PIR template is included.

## Edge Cases & Error Handling

- **Legal / regulatory notification deadlines** (GDPR 72h, state breach laws, etc.): Have legal pre-review the templates and know the thresholds.
- **Ransomware**: Do not pay without legal + executive approval; focus on containment and recovery from backups.
- **Insider threat**: Involve HR/legal early; preserve chain of custody for evidence.

## Verification

1. The team can locate the playbook quickly when an incident occurs.
2. A tabletop exercise using a realistic scenario completes the full cycle (detection → containment → PIR) without major gaps.
3. After a real (or simulated) incident, the PIR produces actionable improvements that are tracked to completion.
4. Communication templates are used and feel appropriate.
5. Success: Incidents are handled methodically, damage is limited, evidence is preserved, stakeholders are informed appropriately, and the organization learns and improves.

## References

- [NIST SP 800-61 Rev. 2 - Computer Security Incident Handling Guide](https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final)
- [SANS Incident Handler's Handbook](https://www.sans.org/white-papers/33901/)
- [Google SRE Incident Management](https://sre.google/sre-book/managing-incidents/)
- [FIRST Incident Response](https://www.first.org/standards/)
