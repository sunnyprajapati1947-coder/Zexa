---
name: terraform-module-builder
description: Creates reusable Terraform modules for cloud infrastructure. Use when provisioning AWS, GCP, or Azure resources with Infrastructure as Code.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: devops
  tags: terraform, iac, aws, gcp, azure, modules, state
---

## Overview

Builds well-structured, reusable Terraform modules following best practices: `main.tf`, `variables.tf` (with validation), `outputs.tf`, `versions.tf`, remote state backend configuration, and a complete example module for a common pattern (VPC + EC2 + S3 bucket, or equivalent on other clouds).

## When to Use This Skill

- Provisioning or refactoring cloud infrastructure as code.
- Creating reusable components that multiple teams or projects will use.
- The user says "Terraform", "IaC", "provision AWS", "create VPC", etc.

## Prerequisites

- Terraform >= 1.5 installed.
- Cloud provider credentials configured (AWS profile, GCP application default, Azure CLI).
- Remote state backend (S3 + DynamoDB for AWS, GCS for GCP, etc.).

## Steps

1. **Module structure**:
   ```
   modules/vpc/
     main.tf
     variables.tf
     outputs.tf
     versions.tf
   ```

2. **variables.tf**:
   - Descriptive descriptions.
   - `type` constraints.
   - `default` where safe.
   - `validation` blocks for important vars.

3. **main.tf**:
   - Resources with consistent naming (use `local.name` or `var.name` prefix).
   - Data sources.
   - Locals for computed values.

4. **outputs.tf**:
   - Only expose what consumers need.
   - Sensitive outputs marked.

5. **State & backend**:
   - Recommend remote backend from day one.
   - Provide `backend.tf` example (commented for module, required in root).

6. **Complete example**:
   - A full root module that uses the VPC module + creates an EC2 instance + S3 bucket with proper IAM.

7. **Output**:
   - All module files.
   - Example usage in a root `main.tf`.
   - `terraform init/plan/apply` commands.
   - State migration notes.

## Examples

A complete, reusable `vpc` module for AWS (with public/private subnets, NAT, route tables, security groups) plus a root example that provisions a small web server behind it and an S3 bucket is included.

## Edge Cases & Error Handling

- **Existing resources**: Use `terraform import` guidance.
- **Multi-region / multi-account**: Show workspace or provider alias patterns.
- **Drift detection**: Regular `terraform plan` in CI.

## Verification

1. `terraform init`.
2. `terraform plan` — clean plan.
3. `terraform apply` — resources created.
4. `terraform destroy` — cleans up.
5. Module can be called from another repo with `source = "git::..."` or Terraform Registry.
6. Success: Infrastructure is reproducible, state is remote and locked, variables are validated, and the module is easy to reuse.

## References

- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [Terraform Module Best Practices](https://developer.hashicorp.com/terraform/language/modules/develop)
- [AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
