#!/usr/bin/env python3
"""Validate local HTML for offline safety and obvious secret leaks."""
from __future__ import annotations
import argparse, re
from pathlib import Path
EXTERNAL_RE = re.compile(
    r"(?is)("
    r"(?:src|href|action|formaction|poster|data|manifest|srcset)\s*=\s*['\"]\s*(?:https?:)?//(?!localhost|127\.0\.0\.1|192\.168\.)"
    r"|@import\s+(?:url\()?['\"]?\s*(?:https?:)?//(?!localhost|127\.0\.0\.1|192\.168\.)"
    r"|url\(\s*['\"]?\s*(?:https?:)?//(?!localhost|127\.0\.0\.1|192\.168\.)"
    r")"
)
SECRET_RE = re.compile(r"(?i)(aws_secret_access_key|secret_access_key|session_token|password\s*=|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})")
ACCOUNT_ID_RE = re.compile(r'(?<!\d)\d{12}(?!\d)')
PRINT_MEDIA_RE = re.compile(r'(?is)@media\s+print\s*\{.*?\}\s*')
SCREEN_WHITE_BG_RE = re.compile(r'(?is)(?:body\s*\{[^}]*background\s*:\s*(?:white|#fff(?:fff)?|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))|background(?:-color)?\s*:\s*(?:white|#fff(?:fff)?|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\)))')

def strip_print_css(text: str) -> str:
    output = []
    pos = 0
    for match in re.finditer(r'(?is)@media\s+print\s*\{', text):
        output.append(text[pos:match.start()])
        depth = 1
        index = match.end()
        while index < len(text) and depth:
            if text[index] == '{':
                depth += 1
            elif text[index] == '}':
                depth -= 1
            index += 1
        pos = index
    output.append(text[pos:])
    return ''.join(output)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('--allow-account-ids', action='store_true')
    args = ap.parse_args()
    path = Path(args.html).expanduser()
    text = path.read_text(encoding='utf-8', errors='replace')
    problems = []
    if not re.search(r'(?is)<!doctype html|<html[\s>]', text): problems.append('source does not look like HTML')
    if EXTERNAL_RE.search(text): problems.append('external browser-fetching URL found')
    if SECRET_RE.search(text): problems.append('credential-like value found')
    if ACCOUNT_ID_RE.search(text) and not args.allow_account_ids: problems.append('12-digit account-like value found')
    screen_text = strip_print_css(text)
    if SCREEN_WHITE_BG_RE.search(screen_text): problems.append('white/day background found outside print CSS')
    if problems:
        for item in problems: print(f'FAIL: {item}')
        return 2
    if not re.search(r'(?is)<title>[^<]+</title>', text): print(f'WARN: html missing <title>: {path}')
    if not re.search(r'(?is)<h1(?:\s[^>]*)?>', text): print(f'WARN: html missing <h1>: {path}')
    print('OK: offline/local-lan validation passed')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
