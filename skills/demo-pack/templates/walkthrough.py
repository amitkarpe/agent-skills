#!/usr/bin/env python3
"""Build static walkthrough pages from recorded data. No scripts, no network.
Usage: python3 walkthrough.py steps.json out_dir
steps.json: [{"title": "...", "body": "<p>html allowed</p>"}, ...]"""
import html, json, pathlib, sys

CSS = ("body{margin:0;padding:48px;background:#0f172a;color:#e2e8f0;"
       "font:20px/1.5 system-ui,sans-serif}h1{margin-top:0}"
       "nav{margin-bottom:24px}nav a{color:#7dd3fc;margin-right:16px}"
       "pre{background:#020617;padding:16px;border-radius:8px;overflow:auto}"
       "table{border-collapse:collapse;margin-top:16px;font-size:17px}th,td{border:1px solid #334155;padding:8px 14px;text-align:left}"
       "th{background:#1e293b}code{background:#1e293b;padding:2px 6px;border-radius:4px}")

def page(title, body, links):
    nav = "".join(f'<a href="{h}">{html.escape(t)}</a>' for h, t in links)
    return (f'<!doctype html><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f'<style>{CSS}</style><nav>{nav}</nav><h1>{html.escape(title)}</h1>{body}')

steps = json.loads(pathlib.Path(sys.argv[1]).read_text())
out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
names = [f"{i:02d}.html" for i in range(1, len(steps) + 1)]
links = [("index.html", "Index")] + [(n, s["title"]) for n, s in zip(names, steps)]
for n, s in zip(names, steps):
    (out / n).write_text(page(s["title"], s["body"], links))
items = "".join(f'<li><a href="{n}">{html.escape(s["title"])}</a></li>' for n, s in zip(names, steps))
(out / "index.html").write_text(page("Demo walkthrough", f"<ol>{items}</ol>", []))
print(f"wrote {len(steps) + 1} pages to {out}")
