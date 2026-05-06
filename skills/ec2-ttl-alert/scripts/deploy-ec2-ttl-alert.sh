#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:?usage: deploy-ec2-ttl-alert.sh <profile> [region]}"
REGION="${2:-ap-southeast-1}"

FUNCTION_NAME="${TTL_ALERT_FUNCTION_NAME:-ec2-ttl-checker}"
ROLE_NAME="${TTL_ALERT_ROLE_NAME:-ec2-ttl-checker-role}"
TOPIC_NAME="${TTL_ALERT_TOPIC_NAME:-ec2-ttl-alerts}"
RULE_NAME="${TTL_ALERT_RULE_NAME:-ec2-ttl-daily}"
WARN_DAYS="${TTL_ALERT_WARN_DAYS:-3}"
EMAILS="${TTL_ALERT_EMAILS:-}"
SCHEDULE="${TTL_ALERT_SCHEDULE:-cron(0 1 * * ? *)}"

OUT_DIR="${HOME}/.AGENTS-temp/agent-skills/ec2-ttl-alert"
ZIP_PATH="${OUT_DIR}/ttl_checker.zip"
INVOKE_OUT="${OUT_DIR}/lambda-test-response.json"
mkdir -p "${OUT_DIR}"

AWS=(aws --profile "${PROFILE}" --region "${REGION}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] START: deploy ec2 ttl alert for profile=${PROFILE} region=${REGION}"

TOPIC_ARN="$("${AWS[@]}" sns create-topic --name "${TOPIC_NAME}" --query TopicArn --output text)"
ACCOUNT_ID="$("${AWS[@]}" sts get-caller-identity --query Account --output text)"
ACCOUNT_LABEL="${PROFILE}:${ACCOUNT_ID}"

if [[ -n "${EMAILS}" ]]; then
  for email in ${EMAILS}; do
    "${AWS[@]}" sns subscribe \
      --topic-arn "${TOPIC_ARN}" \
      --protocol email \
      --notification-endpoint "${email}" >/dev/null || true
  done
fi

TRUST_DOC="$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)"

ROLE_ARN="$("${AWS[@]}" iam create-role \
  --role-name "${ROLE_NAME}" \
  --assume-role-policy-document "${TRUST_DOC}" \
  --query Role.Arn \
  --output text 2>/dev/null || \
  "${AWS[@]}" iam get-role --role-name "${ROLE_NAME}" --query Role.Arn --output text)"

"${AWS[@]}" iam attach-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null

INLINE_POLICY="$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:DescribeInstances"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "${TOPIC_ARN}"
    }
  ]
}
EOF
)"

"${AWS[@]}" iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name ttl-checker-inline \
  --policy-document "${INLINE_POLICY}" >/dev/null

(
  cd "${SCRIPT_DIR}"
  zip -q -j "${ZIP_PATH}" ttl_checker.py
)

FUNCTION_ARN="$("${AWS[@]}" lambda get-function \
  --function-name "${FUNCTION_NAME}" \
  --query Configuration.FunctionArn \
  --output text 2>/dev/null || true)"

if [[ -z "${FUNCTION_ARN}" || "${FUNCTION_ARN}" == "None" ]]; then
  FUNCTION_ARN="$("${AWS[@]}" lambda create-function \
    --function-name "${FUNCTION_NAME}" \
    --runtime python3.12 \
    --role "${ROLE_ARN}" \
    --handler ttl_checker.lambda_handler \
    --zip-file "fileb://${ZIP_PATH}" \
    --timeout 60 \
    --environment "Variables={SNS_TOPIC_ARN=${TOPIC_ARN},WARN_DAYS=${WARN_DAYS},ACCOUNT_LABEL=${ACCOUNT_LABEL}}" \
    --query FunctionArn \
    --output text)"
else
  "${AWS[@]}" lambda update-function-code \
    --function-name "${FUNCTION_NAME}" \
    --zip-file "fileb://${ZIP_PATH}" >/dev/null
  "${AWS[@]}" lambda update-function-configuration \
    --function-name "${FUNCTION_NAME}" \
    --environment "Variables={SNS_TOPIC_ARN=${TOPIC_ARN},WARN_DAYS=${WARN_DAYS},ACCOUNT_LABEL=${ACCOUNT_LABEL}}" >/dev/null
fi

RULE_ARN="$("${AWS[@]}" events put-rule \
  --name "${RULE_NAME}" \
  --schedule-expression "${SCHEDULE}" \
  --state ENABLED \
  --query RuleArn \
  --output text)"

"${AWS[@]}" lambda add-permission \
  --function-name "${FUNCTION_NAME}" \
  --statement-id "allow-eventbridge-${RULE_NAME}" \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "${RULE_ARN}" >/dev/null 2>&1 || true

"${AWS[@]}" events put-targets \
  --rule "${RULE_NAME}" \
  --targets "Id=ttl-checker,Arn=${FUNCTION_ARN}" >/dev/null

"${AWS[@]}" lambda invoke \
  --function-name "${FUNCTION_NAME}" \
  --log-type Tail \
  "${INVOKE_OUT}" >/dev/null

echo "Deployed:"
echo "  profile=${PROFILE}"
echo "  region=${REGION}"
echo "  account=${ACCOUNT_ID}"
echo "  topic=${TOPIC_ARN}"
echo "  function=${FUNCTION_ARN}"
echo "  rule=${RULE_ARN}"
echo "  test_output=${INVOKE_OUT}"
