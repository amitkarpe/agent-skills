#!/usr/bin/env python3
"""Publish a self-contained HTML file to /opt/agent-web and print the LAN URL."""
from __future__ import annotations
import argparse, os, re, shutil
from datetime import datetime, timezone
from pathlib import Path

EXTERNAL_RE = re.compile(r"(?i)(?:src|href)\s*=\s*['\"]\s*(https?:)?//(?!localhost|127\.0\.0\.1|192\.168\.)")
SECRET_RE = re.compile(r"(?i)(aws_secret_access_key|secret_access_key|session_token|password\s*=|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})")

def slugify(value: str, default: str = 'report') -> str:
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9._-]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-._')
    return value[:90] or default

def validate_html(path: Path) -> None:
    text = path.read_text(encoding='utf-8', errors='replace')
    if EXTERNAL_RE.search(text):
        raise SystemExit('blocked: html contains external src/href. no cdn or remote assets allowed by default.')
    if SECRET_RE.search(text):
        raise SystemExit('blocked: html appears to contain credential-like data. sanitize before publishing.')

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('input_html')
    p.add_argument('--skill', choices=['web-html-page','visual-explainer','deep-work'], required=True)
    p.add_argument('--project', default='unknown-project')
    p.add_argument('--lane', default='current')
    p.add_argument('--category', default='general')
    p.add_argument('--topic', default='untitled')
    p.add_argument('--slug', default='')
    p.add_argument('--lan-ip', default=os.environ.get('AGENT_WEB_LAN_IP','192.168.0.9'))
    p.add_argument('--keep', action='store_true')
    args = p.parse_args()

    src = Path(args.input_html).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f'input not found: {src}')
    validate_html(src)

    slug = slugify(args.slug or src.stem)
    project = slugify(args.project, 'unknown-project')
    lane = slugify(args.lane, 'current')
    category = slugify(args.category, 'general')
    topic = slugify(args.topic, 'untitled')

    if args.skill == 'deep-work':
        rel_dir = Path('deep') / category / topic
        evidence_dir = Path.home() / '.AGENTS-temp' / 'deep-work' / category / topic
    else:
        rel_dir = Path(project) / lane
        evidence_dir = Path.home() / '.AGENTS-temp' / project / lane / args.skill

    out_dir = Path('/opt/agent-web') / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f'{slug}.html'
    shutil.copy2(src, out_file)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    shutil.copy2(src, evidence_dir / f'{stamp}-{slug}.html')
    if args.keep:
        out_file.with_suffix(out_file.suffix + '.keep').write_text('keep\n', encoding='utf-8')

    url = f'http://{args.lan_ip}/{rel_dir.as_posix()}/{slug}.html'
    print(url)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
