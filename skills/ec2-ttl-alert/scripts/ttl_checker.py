"""
EC2 TTL checker Lambda.

Single-account by default. This function scans the current account for running
and stopped instances and alerts on missing, invalid, expired, or soon-expiring
TTL tags.
"""

from __future__ import annotations

import os
from datetime import date, datetime

import boto3


SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
WARN_DAYS = int(os.environ.get("WARN_DAYS", "3"))
ACCOUNT_LABEL = os.environ.get("ACCOUNT_LABEL", "current-account")


def collect_findings() -> tuple[list[str], list[str], list[str]]:
    ec2 = boto3.client("ec2", region_name=REGION)
    paginator = ec2.get_paginator("describe_instances")
    today = date.today()

    expired: list[str] = []
    expiring: list[str] = []
    missing: list[str] = []

    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]
    ):
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                state = instance["State"]["Name"]
                tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                name = tags.get("Name", "(no name)")
                ttl = tags.get("TTL")
                env = tags.get("env", "-")

                if not ttl:
                    missing.append(
                        f"  {instance_id}  {name:<40} state={state} env={env}  [{ACCOUNT_LABEL}]"
                    )
                    continue

                try:
                    ttl_date = datetime.strptime(ttl, "%Y-%m-%d").date()
                except ValueError:
                    missing.append(
                        f"  {instance_id}  {name:<40} state={state} TTL=INVALID({ttl})  [{ACCOUNT_LABEL}]"
                    )
                    continue

                delta = (ttl_date - today).days
                if delta < 0:
                    expired.append(
                        f"  {instance_id}  {name:<40} state={state} TTL={ttl} ({abs(delta)}d ago)  [{ACCOUNT_LABEL}]"
                    )
                elif delta <= WARN_DAYS:
                    expiring.append(
                        f"  {instance_id}  {name:<40} state={state} TTL={ttl} (in {delta}d)  [{ACCOUNT_LABEL}]"
                    )

    return expired, expiring, missing


def lambda_handler(event, context):
    today = date.today().isoformat()
    expired, expiring, missing = collect_findings()
    total = len(expired) + len(expiring) + len(missing)

    if total == 0:
        print("All instances have valid TTL values. No alert sent.")
        return {"status": "ok", "findings": 0}

    lines = [f"[AWS TTL Alert] {total} EC2 instance(s) need review — {today}", ""]

    if expired:
        lines += [f"EXPIRED ({len(expired)}):"] + expired + [""]
    if expiring:
        lines += [f"EXPIRING WITHIN {WARN_DAYS} DAYS ({len(expiring)}):"] + expiring + [""]
    if missing:
        lines += [f"MISSING OR INVALID TTL ({len(missing)}):"] + missing + [""]

    lines += [f"Account label: {ACCOUNT_LABEL}", "Action: Review, stop, or terminate as needed."]
    message = "\n".join(lines)
    print(message)

    sns = boto3.client("sns", region_name=REGION)
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"[AWS TTL Alert] {total} EC2 instance(s) need review — {today}",
        Message=message,
    )
    return {"status": "alert_sent", "findings": total}
