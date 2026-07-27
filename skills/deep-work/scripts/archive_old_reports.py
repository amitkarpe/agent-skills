#!/usr/bin/env python3
"""Archive or delete old deep reports under /opt/crypto-web."""
from __future__ import annotations
import argparse, shutil, time
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/opt/crypto-web/deep')
    ap.add_argument('--days', type=int, required=True)
    ap.add_argument('--delete', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    root = Path(args.root)
    cutoff = time.time() - args.days * 86400
    archive = root / '.archive'
    count = 0
    for html in root.rglob('*.html'):
        if '.archive' in html.parts or html.with_suffix(html.suffix + '.keep').exists():
            continue
        if html.stat().st_mtime >= cutoff:
            continue
        count += 1
        if args.dry_run:
            print(f'would archive/delete: {html}')
            continue
        if args.delete:
            html.unlink()
        else:
            dest = archive / html.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(html), str(dest))
    print(f'processed {count} old report(s)')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
