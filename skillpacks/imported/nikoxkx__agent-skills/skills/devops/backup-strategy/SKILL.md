---
name: backup-strategy
description: Designs and implements a backup and disaster recovery strategy for databases and file storage. Use when setting up backups for production data.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: backup, disaster-recovery, rpo, rto, postgres, s3, encryption
---

## Overview

Designs a complete backup and disaster recovery (DR) strategy including RPO/RTO definitions, backup methods for databases (pg_dump, WAL archiving, snapshots), file/object storage backups, S3 lifecycle rules, encryption at rest and in transit, automated restore testing, retention schedules following the 3-2-1 rule, and an incident runbook template for restore scenarios.

## When to Use This Skill

- Setting up production data protection for the first time.
- Auditing or improving existing backup processes.
- Preparing for compliance or business continuity requirements.

## Prerequisites

- Production databases and file storage identified.
- Access to S3 or equivalent object storage with versioning/lifecycle.
- Ability to run backup jobs (cron, Kubernetes CronJob, cloud scheduled tasks).

## Steps

1. **Define RPO and RTO** for each data tier:
   - RPO (Recovery Point Objective): How much data loss is acceptable?
   - RTO (Recovery Time Objective): How long to restore service?

2. **Database backup methods** (choose per DB):
   - Full logical (pg_dump, mysqldump) — good for small DBs or point-in-time restore needs.
   - Continuous WAL / PITR (PostgreSQL pg_basebackup + archiving, MySQL binlog).
   - Storage snapshots (EBS, GCP PD, Azure Disk) — fast for large DBs.
   - Managed service backups (RDS automated, Cloud SQL, etc.).

3. **File / object storage**:
   - S3 versioning + cross-region replication.
   - Lifecycle policies: transition to IA/Glacier after 30/90 days, expire after retention period.

4. **Encryption & security**:
   - Encrypt backups at rest (KMS or S3 SSE).
   - Encrypt in transit (TLS).
   - Least-privilege IAM for backup jobs.

5. **Retention (3-2-1 rule)**:
   - 3 copies of data.
   - 2 different media/types.
   - 1 offsite / in different region/account.

6. **Automated restore testing**:
   - Schedule monthly/quarterly restore to a staging environment.
   - Script the restore and verify data integrity (row counts, checksums).
   - Document the runbook.

7. **Output**:
   - Backup architecture diagram (text or Mermaid).
   - Cron / CronJob / cloud schedule definitions.
   - Restore scripts (example for Postgres from S3).
   - Retention policy.
   - Incident runbook template for "data loss event".

## Examples

A complete strategy for a PostgreSQL + S3 user uploads system is included, with pg_dump + WAL shipping to S3, lifecycle rules, a restore script, and a quarterly restore test CronJob.

## Edge Cases & Error Handling

- **Partial corruption**: PITR allows restoring to just before the corruption.
- **Ransomware / malicious delete**: Immutable backups (S3 Object Lock, WORM) or cross-account backups.
- **Cost control**: Lifecycle policies + infrequent access / Glacier.

## Verification

1. Backups are running on schedule and landing in the correct location.
2. A test restore completes within the target RTO and data is verified correct.
3. Delete a file or row in prod and confirm it can be recovered from backup.
4. Check that old backups are being expired per policy.
5. Success: RPO and RTO targets are met, restores are tested regularly, and data is protected against common failure modes including human error and ransomware.

## References

- [3-2-1 Backup Rule](https://www.backblaze.com/blog/the-3-2-1-backup-rule/)
- [PostgreSQL Backup & PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [AWS S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
