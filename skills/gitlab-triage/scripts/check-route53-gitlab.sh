#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <profile> [output_dir]" >&2
  exit 2
fi

PROFILE="$1"
OUTDIR="${2:-$HOME/.AGENTS-temp/agent-skills/gitlab-triage/route53-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUTDIR"

aws --profile "$PROFILE" route53 list-hosted-zones --output json > "$OUTDIR/hosted_zones.json"

python3 - <<'PY' "$OUTDIR/hosted_zones.json" "$OUTDIR" "$PROFILE"
import json, os, subprocess, sys
zones_path, outdir, profile = sys.argv[1], sys.argv[2], sys.argv[3]
with open(zones_path) as f:
    zones = json.load(f)["HostedZones"]
results = []
for zone in zones:
    zid = zone["Id"].split("/")[-1]
    rr_path = os.path.join(outdir, f"zone-{zid}-rrsets.json")
    subprocess.run(
        ["aws", "--profile", profile, "route53", "list-resource-record-sets", "--hosted-zone-id", zid, "--output", "json"],
        check=True,
        stdout=open(rr_path, "w"),
    )
    with open(rr_path) as rf:
        rrsets = json.load(rf)["ResourceRecordSets"]
    for rr in rrsets:
        name = rr.get("Name", "")
        alias = rr.get("AliasTarget", {}).get("DNSName", "")
        values = " | ".join(v["Value"] for v in rr.get("ResourceRecords", []))
        row = [zid, zone.get("Name", ""), name, rr.get("Type", ""), alias, values]
        text = " ".join(row).lower()
        if "gitlab" in text or "lifebit" in text:
          results.append(row)
out_path = os.path.join(outdir, "results.tsv")
with open(out_path, "w") as out:
    for row in results:
        out.write("\t".join(row) + "\n")
print(out_path)
PY

cat "$OUTDIR/results.tsv"
