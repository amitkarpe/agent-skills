#!/usr/bin/env python3
"""
Embed a PNG file as a base64 <img> tag for self-contained HTML.

Usage:
  python3 embed_png_base64.py arch-account-boundary.png
  # prints an <img> tag with inline base64 src

  python3 embed_png_base64.py arch-account-boundary.png --alt "Account boundary diagram" --style "max-width:100%;border-radius:8px"
  # with alt text and inline style

  python3 embed_png_base64.py --check-diagrams
  # checks if diagrams library and graphviz are available
"""
from __future__ import annotations
import argparse, base64, shutil, subprocess, sys
from pathlib import Path


def check_diagrams() -> int:
    ok = True
    try:
        import diagrams  # noqa: F401
        print("OK: diagrams library available")
    except ImportError:
        print("MISSING: diagrams library — install with: pip install diagrams")
        ok = False
    if shutil.which("dot"):
        result = subprocess.run(["dot", "-V"], capture_output=True, text=True)
        version = (result.stdout or result.stderr).strip().split("\n")[0]
        print(f"OK: graphviz available — {version}")
    else:
        print("MISSING: graphviz (dot) — install with: brew install graphviz  OR  sudo apt install graphviz")
        ok = False
    return 0 if ok else 1


def embed_png(path: Path, alt: str, style: str, width: str | None) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    attrs = f'src="data:image/png;base64,{data}" alt="{alt}"'
    if style:
        attrs += f' style="{style}"'
    if width:
        attrs += f' width="{width}"'
    return f"<img {attrs}>"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("png", nargs="?", help="Path to PNG file")
    ap.add_argument("--alt", default="Architecture diagram", help="Alt text for the image")
    ap.add_argument("--style", default="max-width:100%;border-radius:8px;display:block;margin:12px 0",
                    help="Inline CSS style")
    ap.add_argument("--width", default=None, help="Optional width attribute (e.g. 900)")
    ap.add_argument("--check-diagrams", action="store_true", help="Check if diagrams+graphviz are available")
    args = ap.parse_args()

    if args.check_diagrams:
        return check_diagrams()

    if not args.png:
        ap.error("PNG file path required unless --check-diagrams is used")

    path = Path(args.png)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1
    if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".svg"):
        print(f"WARN: unexpected extension {path.suffix} — proceeding anyway", file=sys.stderr)

    print(embed_png(path, args.alt, args.style, args.width))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
