---
name: security-hardening
description: Hardens server, container, and cloud infrastructure against common attacks. Use when preparing infrastructure for production or after a security audit.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: security, hardening, docker, ssh, iam, firewall, least-privilege
---

## Overview

Provides a prioritized hardening checklist and implementation guide for OS, containers, and cloud accounts. Covers unattended upgrades, SSH key-only access + fail2ban, firewall (ufw or security groups), Docker non-root + read-only FS + no privileged, cloud IAM least-privilege + SCPs, secret management, network segmentation, and a severity-based checklist.

## When to Use This Skill

- Preparing infrastructure for production or a security review.
- After a penetration test or vulnerability scan highlights infrastructure issues.
- Onboarding a new cloud account or server.

## Prerequisites

- Servers or containers you control.
- Cloud account (AWS/GCP/Azure) admin access for IAM work.
- Ability to rebuild or update existing infrastructure.

## Steps

1. **OS hardening (Linux)**:
   - Automatic security updates (unattended-upgrades on Debian/Ubuntu, dnf-automatic on RHEL).
   - SSH: key-only auth, disable password, disable root login, change port or use fail2ban.
   - Firewall: ufw or firewalld — allow only necessary ports from specific sources.

2. **Docker / container hardening**:
   - Run as non-root user (create user in Dockerfile, `USER` instruction).
   - Read-only root filesystem + tmpfs for writable dirs.
   - Drop all capabilities, add only needed ones.
   - No `--privileged`, no `--network host` unless absolutely required.
   - Use distroless or minimal base images.

3. **Cloud IAM**:
   - Least privilege: start with zero and grant only required actions/resources.
   - Use IAM roles for EC2 / service accounts instead of long-lived keys.
   - Enable MFA for all human users.
   - Service control policies (SCPs) / organization policies to prevent dangerous actions at scale.

4. **Secrets**:
   - Never in env vars or code.
   - Use AWS Secrets Manager / Parameter Store / GCP Secret Manager / HashiCorp Vault.
   - Rotate regularly.

5. **Network**:
   - Private subnets for app/DB tiers.
   - Security groups / NACLs / firewall rules with least exposure.
   - WAF in front of public endpoints.

6. **Output**:
   - Hardening checklist by severity (Critical / High / Medium).
   - Dockerfile snippet showing hardened user + read-only.
   - Terraform / cloudformation snippets for IAM roles and security groups.
   - Ansible / cloud-init for OS hardening.
   - Verification commands (`ss -tuln`, `docker inspect`, `aws iam simulate-principal-policy`).

## Examples

A hardened Dockerfile, ufw + SSH config, least-privilege IAM role for a web app, and a full checklist with commands are included.

## Edge Cases & Error Handling

- **Legacy apps that require root**: Document the risk and isolate them as much as possible.
- **Break-glass access**: Maintain emergency procedures with additional approvals.

## Verification

1. Run CIS benchmarks or a scanner (Lynis, Docker Bench, Prowler, ScoutSuite).
2. Attempt SSH with password — denied.
3. Container runs as non-root and read-only FS (test by trying to write to /).
4. IAM policy simulation shows only allowed actions.
5. Success: Infrastructure passes automated hardening scanners with minimal or no critical findings, and manual tests confirm reduced attack surface.

## References

- [CIS Benchmarks](https://www.cisecurity.org/benchmarks/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [Prowler](https://github.com/prowler-cloud/prowler) (cloud security scanner)
