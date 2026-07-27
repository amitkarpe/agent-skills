#!/usr/bin/env python3
"""
Build a deep-work portal: generate index.html and all-in-one.html from a manifest.

Usage:
  python3 portal_builder.py manifest.json --out-dir /opt/crypto-web/deep/ami-factory/

Manifest format (JSON):
  {
    "title": "AMI Factory Ops Portal",
    "version": "2026-06-13",
    "env": "DEV 672172129528 / PROD 021577063369",
    "evidence_date": "2026-06-13",
    "ttl": "2026-12-13",
    "owner": "Amit / CC",
    "pages": [
      {"filename": "architecture.html",  "label": "Architecture", "icon": "🗺️",  "desc": "Account boundary, E2E swimlane, AMI lineage"},
      {"filename": "inventory.html",     "label": "Inventory",    "icon": "📋", "desc": "All 3 lanes: AMI IDs, EC2s, SSM pointers"},
      {"filename": "ami-boxes.html",     "label": "AMI Boxes",    "icon": "📦", "desc": "What is baked into each AMI"},
      {"filename": "resource-kb.html",   "label": "Resource KB",  "icon": "🗄️", "desc": "AWS resource categories, CLI checks, gotchas"},
      {"filename": "runbook.html",       "label": "Runbook",      "icon": "📖", "desc": "Decision trees, cleanup rules, escalation"}
    ]
  }
"""
from __future__ import annotations
import argparse, json, re
from datetime import date
from pathlib import Path

NAV_STYLE = (
    "background:#1e2130;border:1px solid #2a2d3e;padding:4px 10px;"
    "border-radius:6px;font-size:11px;color:#8892a4;text-decoration:none"
)
NAV_ACTIVE_STYLE = (
    "background:#4f8ef7;border:1px solid #4f8ef7;padding:4px 10px;"
    "border-radius:6px;font-size:11px;color:#fff;text-decoration:none"
)


def _nav_html(pages: list[dict], active: str | None = None) -> str:
    links = ['<a href="index.html" style="' + (NAV_ACTIVE_STYLE if active == "index" else NAV_STYLE) + '">🏠 Home</a>']
    for p in pages:
        style = NAV_ACTIVE_STYLE if p["filename"] == active else NAV_STYLE
        links.append(f'<a href="{p["filename"]}" style="{style}">{p["icon"]} {p["label"]}</a>')
    links.append('<a href="all-in-one.html" style="' + (NAV_ACTIVE_STYLE if active == "all-in-one.html" else NAV_STYLE) + '">📄 Export</a>')
    return "\n    ".join(links)


def _header_html(manifest: dict, active: str | None) -> str:
    nav = _nav_html(manifest["pages"], active)
    return f"""<header style="background:linear-gradient(135deg,#111827,#1a1d27);border-bottom:1px solid #2a2d3e;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:34px;height:34px;background:#4f8ef7;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px">🏭</div>
    <div>
      <div style="font-size:16px;font-weight:700;color:#e0e4f0">{manifest['title']}</div>
      <div style="font-size:11px;color:#8892a4">{manifest['env']} · v{manifest['version']}</div>
    </div>
  </div>
  <nav style="display:flex;gap:6px;flex-wrap:wrap">
    {nav}
  </nav>
</header>"""


def _footer_html(manifest: dict) -> str:
    return (
        f'<footer style="border-top:1px solid #2a2d3e;padding:14px 24px;'
        f'text-align:center;color:#8892a4;font-size:11px;margin-top:32px">'
        f'{manifest["title"]} · v{manifest["version"]} · {manifest["env"]} · '
        f'evidence current as of {manifest["evidence_date"]} · review by {manifest["ttl"]}'
        f'</footer>'
    )


def build_index(manifest: dict, out_dir: Path) -> None:
    cards = []
    for p in manifest["pages"]:
        cards.append(
            f'<a href="{p["filename"]}" style="background:#1e2130;border:1px solid #2a2d3e;'
            f'border-radius:10px;padding:16px;text-decoration:none;display:block">'
            f'<div style="font-size:22px;margin-bottom:8px">{p["icon"]}</div>'
            f'<div style="font-weight:700;color:#e0e4f0;margin-bottom:4px">{p["label"]}</div>'
            f'<div style="font-size:12px;color:#8892a4">{p["desc"]}</div></a>'
        )
    cards.append(
        '<a href="all-in-one.html" style="background:#1e2130;border:1px solid #2a2d3e;'
        'border-radius:10px;padding:16px;text-decoration:none;display:block">'
        '<div style="font-size:22px;margin-bottom:8px">📄</div>'
        '<div style="font-weight:700;color:#e0e4f0;margin-bottom:4px">Export (All-in-One)</div>'
        '<div style="font-size:12px;color:#8892a4">Full portal as a single page — print or convert to docx</div></a>'
    )
    grid = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px">' + "".join(cards) + '</div>'

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generated" content="{manifest['version']}">
<title>{manifest['title']}</title>
<style>
body{{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:#0f1117;color:#e0e4f0;line-height:1.6}}
a{{color:#4f8ef7}}
</style>
</head>
<body>
{_header_html(manifest, "index")}
<main style="max-width:1100px;margin:0 auto;padding:28px 20px">
<h1 style="font-size:22px;font-weight:800;margin-bottom:6px">{manifest['title']}</h1>
<p style="color:#8892a4;margin-bottom:24px">{manifest['env']} · Owner: {manifest['owner']} · v{manifest['version']}</p>
{grid}
</main>
{_footer_html(manifest)}
</body>
</html>"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote: {out_dir}/index.html")


def build_all_in_one(manifest: dict, out_dir: Path) -> None:
    """Concatenate all page bodies into one export-safe HTML. Strips <details>/<summary>."""
    bodies: list[str] = []
    for p in manifest["pages"]:
        src = out_dir / p["filename"]
        if not src.exists():
            bodies.append(f'<h2>{p["icon"]} {p["label"]}</h2><p style="color:#e74c3c">[page not found: {p["filename"]}]</p>')
            continue
        text = src.read_text(encoding="utf-8", errors="replace")
        # Extract <main>...</main> body
        m = re.search(r"<main[^>]*>(.*?)</main>", text, re.DOTALL | re.IGNORECASE)
        body = m.group(1) if m else text
        # Remove <details>/<summary> wrappers but keep their content
        body = re.sub(r"<details[^>]*>", "", body, flags=re.IGNORECASE)
        body = re.sub(r"</details>", "", body, flags=re.IGNORECASE)
        body = re.sub(r"<summary[^>]*>.*?</summary>", "", body, flags=re.DOTALL | re.IGNORECASE)
        # Remove sticky nav, toggle buttons inside body
        body = re.sub(r'<header[^>]*class="top"[^>]*>.*?</header>', "", body, flags=re.DOTALL | re.IGNORECASE)
        bodies.append(f'<section style="page-break-before:always;margin-bottom:40px">'
                      f'<h2 style="font-size:18px;font-weight:800;border-bottom:2px solid #2a2d3e;padding-bottom:8px;margin-bottom:16px">'
                      f'{p["icon"]} {p["label"]}</h2>{body}</section>')

    cover = f"""<section style="padding:40px 0;border-bottom:2px solid #2a2d3e;margin-bottom:40px">
<h1 style="font-size:24px;font-weight:900;margin-bottom:16px">{manifest['title']} — Full Reference</h1>
<table style="border-collapse:collapse;font-size:13px;width:auto">
<tr><th style="text-align:left;padding:5px 12px 5px 0;color:#8892a4">Version</th><td style="padding:5px 0">v{manifest['version']}</td></tr>
<tr><th style="text-align:left;padding:5px 12px 5px 0;color:#8892a4">Generated</th><td style="padding:5px 0">{date.today().isoformat()}</td></tr>
<tr><th style="text-align:left;padding:5px 12px 5px 0;color:#8892a4">Owner</th><td style="padding:5px 0">{manifest['owner']}</td></tr>
<tr><th style="text-align:left;padding:5px 12px 5px 0;color:#8892a4">Environment</th><td style="padding:5px 0">{manifest['env']}</td></tr>
<tr><th style="text-align:left;padding:5px 12px 5px 0;color:#8892a4">Review by</th><td style="padding:5px 0">{manifest['ttl']}</td></tr>
<tr><th style="text-align:left;padding:5px 12px 5px 0;color:#8892a4">Convert to docx</th><td style="padding:5px 0;font-family:monospace;font-size:12px">pandoc all-in-one.html --from html --to docx -o portal.docx</td></tr>
</table>
</section>"""

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generated" content="{manifest['version']}">
<title>{manifest['title']} — All-in-One Export</title>
<style>
body{{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:#0f1117;color:#e0e4f0;line-height:1.6;padding:32px}}
h1{{font-size:22px;font-weight:800}}h2{{font-size:16px;font-weight:700}}h3{{font-size:13px;font-weight:600;color:#8892a4}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#1a1d27;color:#8892a4;text-align:left;padding:6px 10px;border-bottom:1px solid #2a2d3e;font-size:11px}}
td{{padding:6px 10px;border-bottom:1px solid #2a2d3e;vertical-align:top}}
pre{{background:#020617;border:1px solid #2a2d3e;border-radius:6px;padding:8px 10px;font-size:11px;color:#93c5fd;overflow-x:auto;white-space:pre-wrap;word-break:break-all}}
code{{font-family:'Courier New',monospace;background:rgba(255,255,255,.06);padding:1px 4px;border-radius:3px;font-size:11px}}
a{{color:#4f8ef7}}
@media print{{body{{background:#fff;color:#000}}pre{{background:#f5f5f5;color:#000}}th{{background:#eee;color:#333}}}}
</style>
</head>
<body>
{cover}
{"".join(bodies)}
{_footer_html(manifest)}
</body>
</html>"""
    (out_dir / "all-in-one.html").write_text(html, encoding="utf-8")
    print(f"wrote: {out_dir}/all-in-one.html")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", help="Path to portal manifest JSON")
    ap.add_argument("--out-dir", required=True, help="Output directory (portal root)")
    ap.add_argument("--index-only", action="store_true", help="Regenerate index.html only")
    ap.add_argument("--export-only", action="store_true", help="Regenerate all-in-one.html only")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.export_only:
        build_index(manifest, out_dir)
    if not args.index_only:
        build_all_in_one(manifest, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
