#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 <profile> <region> [output_dir]" >&2
  exit 2
fi

PROFILE="$1"
REGION="$2"
OUTDIR="${3:-$HOME/.AGENTS-temp/agent-skills/gitlab-triage/elb-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUTDIR"

aws --profile "$PROFILE" --region "$REGION" elb describe-load-balancers \
  --load-balancer-names gitlab \
  --output json > "$OUTDIR/classic-elb.json"

aws --profile "$PROFILE" --region "$REGION" elb describe-instance-health \
  --load-balancer-name gitlab \
  --output json > "$OUTDIR/classic-elb-health.json"

echo "ELB"
cat "$OUTDIR/classic-elb.json"
echo
echo "HEALTH"
cat "$OUTDIR/classic-elb-health.json"
