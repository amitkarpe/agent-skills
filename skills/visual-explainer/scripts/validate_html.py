#!/usr/bin/env python3
"""Validate local HTML for offline safety and obvious secret leaks."""
from __future__ import annotations
import argparse, re
from pathlib import Path
EXTERNAL_RE = re.compile(r"(?i)(?:src|href)\s*=\s*['\"]\s*(https?:)?//(?!localhost|127\.0\.0\.1|192\.168\.)")
SECRET_RE = re.compile(r"(?i)(aws_secret_access_key|secret_access_key|session_token|password\s*=|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})")
ACCOUNT_ID_RE = re.compile(r'(?<!\d)\d{12}(?!\d)')

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('--allow-account-ids', action='store_true')
    args = ap.parse_args()
    path = Path(args.html).expanduser()
    text = path.read_text(encoding='utf-8', errors='replace')
    problems = []
    if EXTERNAL_RE.search(text): problems.append('external src/href found')
    if SECRET_RE.search(text): problems.append('credential-like value found')
    if ACCOUNT_ID_RE.search(text) and not args.allow_account_ids: problems.append('12-digit account-like value found')
    if problems:
        for item in problems: print(f'FAIL: {item}')
        return 2
    print('OK: offline/local-lan validation passed')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
