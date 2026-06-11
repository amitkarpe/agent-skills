# AWS / DevOps dashboard rules

Use these sections for AWS, DevOps, CloudOps, IaC, security, incidents, and codebase learning.

## Required views
- Architecture overview: components and boundaries.
- Control plane vs data plane when relevant.
- Inputs -> process -> outputs.
- Trust boundaries and IAM/KMS/security notes.
- Failure modes and blast radius.
- Validation checklist.
- Rollback or recovery plan.
- Cost/ops impact when relevant.

## AWS anchors
Use AWS-first language when relevant:
- IAM, STS, KMS, VPC, S3, ECR, EC2, SSM, CloudWatch, CloudTrail.
- CodeBuild, CodePipeline, Batch, Lambda, EventBridge.
- Terraform, Packer, Ansible, AMI, user_data, private subnet, no-internet environment.

## Codebase learning
For repo explanations include:
- File map.
- Entry points.
- Data flow.
- Config and secrets path.
- Build/test/deploy path.
- Risky files.
- Safe next actions.

## Safety
Do not include secrets, account IDs, private endpoints, credentials, or production identifiers unless already intentionally included by the user and safe to quote.
