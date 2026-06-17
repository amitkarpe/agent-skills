#!/usr/bin/env python3
"""Render a static json-render-style report spec to self-contained offline HTML."""
from __future__ import annotations
import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_CLASS = {
    "success": "ok", "pass": "ok", "done": "ok", "green": "ok",
    "warning": "warn", "warn": "warn", "amber": "warn", "blocked": "bad",
    "error": "bad", "fail": "bad", "failed": "bad", "red": "bad",
    "info": "info", "neutral": "info", "blue": "info"
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def safe_id(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "item").strip("-")
    return value or "item"


def status_class(value: Any) -> str:
    return STATUS_CLASS.get(str(value or "info").lower(), "info")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_items(items: Any) -> str:
    if not isinstance(items, list):
        items = [items]
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def chips(items: Any) -> str:
    if not items:
        return ""
    if not isinstance(items, list):
        items = [items]
    return '<div class="chips">' + ''.join(f'<span class="chip">{esc(item)}</span>' for item in items) + '</div>'


def render_table(headers: Any, rows: Any, title: str = "", caption: str = "") -> str:
    headers = headers if isinstance(headers, list) else []
    rows = rows if isinstance(rows, list) else []
    head = ''.join(f'<th>{esc(h)}</th>' for h in headers)
    body_parts = []
    for row in rows:
        if isinstance(row, dict):
            cells = [row.get(h, "") for h in headers]
        elif isinstance(row, list):
            cells = row
        else:
            cells = [row]
        body_parts.append('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in cells) + '</tr>')
    title_html = f'<h2>{esc(title)}</h2>' if title else ''
    caption_html = f'<p class="muted">{esc(caption)}</p>' if caption else ''
    return f'<section class="panel">{title_html}{caption_html}<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body_parts)}</tbody></table></div></section>'


def render_cards(cards: Any, title: str = "") -> str:
    cards = cards if isinstance(cards, list) else []
    parts = []
    for card in cards:
        if isinstance(card, dict):
            label = card.get("label") or card.get("title") or "Item"
            value = card.get("value") or card.get("text") or card.get("description") or ""
            status = card.get("status") or card.get("level") or "info"
            icon = card.get("icon", "•")
        else:
            label, value, status, icon = "Item", card, "info", "•"
        parts.append(f'<article class="card {status_class(status)}"><div class="card-icon">{esc(icon)}</div><div><div class="card-label">{esc(label)}</div><div class="card-value">{esc(value)}</div></div></article>')
    title_html = f'<h2>{esc(title)}</h2>' if title else ''
    return f'<section class="panel">{title_html}<div class="card-grid">{"".join(parts)}</div></section>'


def render_risks(risks: Any, title: str = "Risks", key: str = "text") -> str:
    risks = risks if isinstance(risks, list) else []
    parts = []
    for risk in risks:
        if isinstance(risk, dict):
            level = risk.get("level", "warning")
            text = risk.get(key) or risk.get("text") or risk.get("description") or risk
        else:
            level, text = "warning", risk
        parts.append(f'<div class="risk {status_class(level)}"><span>{esc(str(level).upper())}</span><p>{esc(text)}</p></div>')
    return f'<section class="panel"><h2>{esc(title)}</h2><div class="risk-list">{"".join(parts)}</div></section>'


def render_timeline(events: Any, title: str = "Timeline") -> str:
    events = events if isinstance(events, list) else []
    parts = []
    for i, ev in enumerate(events, 1):
        if isinstance(ev, dict):
            label = ev.get("label") or ev.get("title") or f"Step {i}"
            detail = ev.get("detail") or ev.get("description") or ev.get("text") or ""
            when = ev.get("time") or ev.get("when") or str(i)
        else:
            label, detail, when = f"Step {i}", ev, str(i)
        parts.append(f'<div class="timeline-item"><div class="dot">{esc(when)}</div><div><strong>{esc(label)}</strong><p>{esc(detail)}</p></div></div>')
    return f'<section class="panel"><h2>{esc(title)}</h2><div class="timeline">{"".join(parts)}</div></section>'


def render_checklist(items: Any, title: str = "Checklist") -> str:
    items = items if isinstance(items, list) else []
    parts = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("label") or item.get("text") or "Item"
            done = bool(item.get("done", False))
        else:
            label, done = item, False
        parts.append(f'<li><span class="check">{"✓" if done else "□"}</span>{esc(label)}</li>')
    return f'<section class="panel"><h2>{esc(title)}</h2><ul class="checklist">{"".join(parts)}</ul></section>'


def render_flow(nodes: Any, edges: Any, lanes: Any = None, title: str = "Workflow") -> str:
    nodes = nodes if isinstance(nodes, list) else []
    lanes = lanes if isinstance(lanes, list) and lanes else sorted({str(n.get("lane", "Flow")) for n in nodes if isinstance(n, dict)}) or ["Flow"]
    by_lane: dict[str, list[dict[str, Any]]] = {str(lane): [] for lane in lanes}
    for node in nodes:
        if isinstance(node, dict):
            by_lane.setdefault(str(node.get("lane", "Flow")), []).append(node)
    lane_html = []
    for lane, lane_nodes in by_lane.items():
        cards = ''.join(f'<div class="flow-node"><strong>{esc(n.get("label", n.get("id", "node")))}</strong><small>{esc(n.get("detail", ""))}</small></div>' for n in lane_nodes)
        lane_html.append(f'<div class="flow-lane"><div class="lane-title">{esc(lane)}</div><div class="lane-nodes">{cards}</div></div>')
    edge_text = ''
    if isinstance(edges, list) and edges:
        edge_text = '<p class="muted">Flow order: ' + esc(' → '.join(' / '.join(map(str, e)) if isinstance(e, list) else str(e) for e in edges[:8])) + '</p>'
    return f'<section class="panel"><h2>{esc(title)}</h2><div class="flow-board">{"".join(lane_html)}</div>{edge_text}</section>'


def render_architecture(groups: Any, edges: Any = None, title: str = "Architecture Map") -> str:
    groups = groups if isinstance(groups, list) else []
    parts = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        name = group.get("name", "Group")
        resources = group.get("resources", [])
        res_html = ''.join(f'<div class="resource">{esc(r.get("label", r.get("name", r))) if isinstance(r, dict) else esc(r)}</div>' for r in (resources if isinstance(resources, list) else []))
        parts.append(f'<div class="arch-group"><div class="arch-title">{esc(name)}</div><div class="arch-resources">{res_html}</div></div>')
    edge_text = ''
    if isinstance(edges, list) and edges:
        edge_text = '<p class="muted">Relationships: ' + esc(' · '.join(' → '.join(map(str, e)) if isinstance(e, list) else str(e) for e in edges[:10])) + '</p>'
    return f'<section class="panel"><h2>{esc(title)}</h2><div class="arch-map">{"".join(parts)}</div>{edge_text}</section>'


def render_decision(options: Any, title: str = "Decision Guide") -> str:
    options = options if isinstance(options, list) else []
    parts = []
    for opt in options:
        if isinstance(opt, dict):
            label = opt.get("label") or opt.get("title") or "Option"
            decision = opt.get("decision") or opt.get("status") or opt.get("level") or "info"
            reason = opt.get("reason") or opt.get("description") or ""
        else:
            label, decision, reason = str(opt), "info", ""
        parts.append(f'<article class="decision {status_class(decision)}"><span>{esc(decision)}</span><strong>{esc(label)}</strong><p>{esc(reason)}</p></article>')
    return f'<section class="panel"><h2>{esc(title)}</h2><div class="decision-grid">{"".join(parts)}</div></section>'


def render_glossary(terms: Any, title: str = "Glossary") -> str:
    terms = terms if isinstance(terms, list) else []
    parts = []
    for term in terms:
        if isinstance(term, dict):
            name = term.get("term") or term.get("name") or "Term"
            meaning = term.get("definition") or term.get("meaning") or ""
        else:
            name, meaning = str(term), ""
        parts.append(f'<dt>{esc(name)}</dt><dd>{esc(meaning)}</dd>')
    return f'<section class="panel"><h2>{esc(title)}</h2><dl class="glossary">{"".join(parts)}</dl></section>'


def render_quiz(questions: Any, title: str = "Recap Quiz") -> str:
    questions = questions if isinstance(questions, list) else []
    parts = []
    for i, q in enumerate(questions, 1):
        if isinstance(q, dict):
            prompt = q.get("question") or q.get("prompt") or f"Question {i}"
            answer = q.get("answer") or ""
        else:
            prompt, answer = str(q), ""
        parts.append(f'<details class="qa"><summary>{esc(i)}. {esc(prompt)}</summary><p>{esc(answer)}</p></details>')
    return f'<section class="panel"><h2>{esc(title)}</h2><div class="quiz">{"".join(parts)}</div></section>'


def render_commands(commands: Any, title: str = "Command Cookbook") -> str:
    commands = commands if isinstance(commands, list) else []
    parts = []
    for cmd in commands:
        if isinstance(cmd, dict):
            label = cmd.get("label") or cmd.get("purpose") or "Command"
            command = cmd.get("command") or ""
            output = cmd.get("expected_output") or cmd.get("output") or ""
        else:
            label, command, output = "Command", str(cmd), ""
        copy = esc(command)
        parts.append(f'<div class="cmd"><div class="cmd-head"><span>{esc(label)}</span><button onclick="navigator.clipboard.writeText(this.dataset.copy)" data-copy="{copy}">Copy</button></div><pre>{esc(command)}</pre>{f"<pre class=\"expected\">{esc(output)}</pre>" if output else ""}</div>')
    return f'<section class="panel"><h2>{esc(title)}</h2>{"".join(parts)}</section>'


def render_component(elem_id: str, spec: dict[str, Any], rendered: set[str]) -> str:
    elements = spec["elements"]
    elem = elements[elem_id]
    etype = elem["type"]
    props = elem.get("props", {})
    children = elem.get("children", [])
    child_html = ''.join(render_component(child, spec, rendered) for child in children)

    if etype == "Page":
        return child_html
    if etype == "Hero":
        return f'<section class="hero"><div><h1>{esc(props.get("title", spec.get("title", "Report")))}</h1><p>{esc(props.get("subtitle", spec.get("subtitle", "")))}</p>{chips(props.get("chips"))}</div><span class="status {status_class(props.get("status", spec.get("meta", {}).get("status", "info")))}">{esc(props.get("status", spec.get("meta", {}).get("status", "info")))}</span></section>'
    if etype == "TLDR":
        return f'<section class="panel accent"><h2>{esc(props.get("title", "TL;DR"))}</h2>{list_items(props.get("items", []))}</section>'
    if etype in ("StatusCards", "SnapshotCards", "ConceptCards", "NavCards", "Flashcards"):
        return render_cards(props.get("cards", []), props.get("title", ""))
    if etype in ("EvidenceTable", "Comparison"):
        return render_table(props.get("headers", []), props.get("rows", []), props.get("title", ""), props.get("caption", ""))
    if etype in ("RiskBox", "RiskRadar"):
        return render_risks(props.get("items", props.get("risks", [])), props.get("title", "Risks"))
    if etype == "NextAction":
        return f'<section class="panel next"><h2>{esc(props.get("title", "Next action"))}</h2>{list_items(props.get("items", []))}</section>'
    if etype == "Timeline":
        return render_timeline(props.get("events", []), props.get("title", "Timeline"))
    if etype == "Checklist":
        return render_checklist(props.get("items", []), props.get("title", "Checklist"))
    if etype in ("FlowDiagram", "ConceptMap"):
        return render_flow(props.get("nodes", []), props.get("edges", []), props.get("lanes"), props.get("title", "Flow"))
    if etype == "ArchitectureMap":
        return render_architecture(props.get("groups", []), props.get("edges", []), props.get("title", "Architecture Map"))
    if etype == "DecisionGuide":
        return render_decision(props.get("options", []), props.get("title", "Decision Guide"))
    if etype == "Glossary":
        return render_glossary(props.get("terms", []), props.get("title", "Glossary"))
    if etype == "Quiz":
        return render_quiz(props.get("questions", []), props.get("title", "Recap Quiz"))
    if etype == "CommandBlocks":
        return render_commands(props.get("commands", []), props.get("title", "Command Cookbook"))
    if etype == "Section":
        summary_html = f'<p class="muted">{esc(props.get("summary"))}</p>' if props.get("summary") else ""
        return f'<section class="panel"><h2>{esc(props.get("icon", ""))} {esc(props.get("title", "Section"))}</h2>{summary_html}{child_html}</section>'
    return f'<section class="panel"><h2>{esc(etype)}</h2>{child_html}</section>'


def css_for(skill: str) -> str:
    base = r"""
:root{--bg:#0f172a;--panel:#111827;--panel2:#1e293b;--line:#334155;--text:#e5e7eb;--muted:#94a3b8;--blue:#38bdf8;--green:#22c55e;--amber:#f59e0b;--red:#ef4444;--violet:#a78bfa}
*{box-sizing:border-box;text-shadow:none;-webkit-text-stroke:0}
html{overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;overflow-x:hidden}
.wrap{max-width:1120px;margin:0 auto;padding:24px;overflow-wrap:anywhere}
.hero{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;background:linear-gradient(135deg,#111827,#172033);border:1px solid var(--line);border-radius:18px;padding:22px;margin-bottom:18px}
.hero h1{margin:0 0 6px;font-size:clamp(28px,4vw,42px);line-height:1.08}
.hero p{margin:0;color:var(--muted);max-width:820px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.chip,.status{border:1px solid var(--line);background:#0b1220;border-radius:999px;padding:5px 10px;font-size:15px}
.status{white-space:nowrap;text-transform:uppercase;font-weight:700}
.ok{border-color:rgba(34,197,94,.55)}
.warn{border-color:rgba(245,158,11,.65)}
.bad{border-color:rgba(239,68,68,.65)}
.info{border-color:rgba(56,189,248,.55)}
.panel{background:rgba(17,24,39,.94);border:1px solid var(--line);border-radius:16px;padding:18px;margin:14px 0}
.panel.accent{border-color:rgba(56,189,248,.55)}
.panel h2{margin:0 0 12px;font-size:22px}
.muted{color:var(--muted);margin:6px 0 12px}
.card-grid,.decision-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.card,.decision{background:#0b1220;border:1px solid var(--line);border-radius:14px;padding:14px;display:flex;gap:12px;min-height:84px}
.card-icon{font-size:22px}
.card-label{color:var(--muted);font-size:15px}
.card-value{font-weight:800;font-size:19px}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse}
th,td{border-bottom:1px solid var(--line);padding:9px;text-align:left;vertical-align:top}
th{color:#bfdbfe;background:#0b1220}
.risk-list{display:grid;gap:10px}
.risk{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--line);border-radius:12px;background:#0b1220;padding:12px}
.risk span,.decision span{font-weight:800;font-size:15px;color:var(--muted);text-transform:uppercase}
.risk p,.decision p{margin:0}
.timeline{display:grid;gap:12px}
.timeline-item{display:grid;grid-template-columns:64px 1fr;gap:12px}
.dot{border:1px solid var(--line);border-radius:999px;text-align:center;padding:5px;background:#0b1220;color:#bfdbfe}
.checklist{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.check{display:inline-block;width:28px;color:#93c5fd}
.flow-board{display:grid;gap:12px}
.flow-lane{display:grid;grid-template-columns:120px 1fr;gap:12px;align-items:stretch}
.lane-title{background:#0b1220;border:1px solid var(--line);border-radius:12px;padding:12px;font-weight:800;color:#bfdbfe}
.lane-nodes{display:flex;flex-wrap:wrap;gap:10px}
.flow-node,.resource{background:#0b1220;border:1px solid var(--line);border-radius:12px;padding:12px;min-width:150px}
.flow-node small{display:block;color:var(--muted);font-size:15px}
.arch-map{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.arch-group{border:1px dashed rgba(56,189,248,.6);border-radius:16px;padding:14px;background:rgba(56,189,248,.04)}
.arch-title{font-weight:900;margin-bottom:10px;color:#bfdbfe}
.arch-resources{display:grid;gap:8px}
.decision{display:block}
.decision strong{display:block;font-size:18px;margin:5px 0}
.glossary{display:grid;grid-template-columns:minmax(120px,220px) 1fr;gap:8px 16px}
.glossary dt{font-weight:900;color:#bfdbfe}
.glossary dd{margin:0;color:var(--muted)}
.qa{background:#0b1220;border:1px solid var(--line);border-radius:12px;padding:12px;margin:8px 0}
.cmd{background:#020617;border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:10px 0}
.cmd-head{display:flex;justify-content:space-between;gap:10px;align-items:center;background:#111827;padding:8px 10px}
.cmd button{background:#1e293b;border:1px solid var(--line);color:var(--text);border-radius:8px;padding:4px 10px;cursor:pointer;font-size:15px}
.cmd pre{margin:0;padding:12px;overflow:auto;color:#93c5fd;white-space:pre-wrap;overflow-wrap:anywhere}
.expected{color:#86efac!important;border-top:1px solid var(--line)}
footer{color:var(--muted);font-size:15px;text-align:center;border-top:1px solid var(--line);margin-top:20px;padding:14px}
@media(max-width:720px){.hero,.flow-lane{display:block}.status{display:inline-block;margin-top:12px}.lane-title{margin-bottom:8px}.glossary{grid-template-columns:1fr}.wrap{padding:14px}}
@media print{body{color:#111;background:#fff}.panel,.hero,.card,.risk,.decision,.cmd,.flow-node,.resource,.lane-title{break-inside:avoid}}
"""
    if skill == "web-html-page":
        return base + ".wrap{max-width:1040px}.hero{padding:18px}.panel{padding:15px;margin:10px 0}.card-value{font-size:17px}\n"
    if skill == "deep-work":
        return base + ".wrap{max-width:1220px}.hero{padding:26px}.panel{padding:20px}.panel h2{font-size:24px}\n"
    return base


def render_document(spec: dict[str, Any]) -> str:
    skill = spec.get("skill", "report")
    root = spec["root"]
    content = render_component(root, spec, set())
    title = spec.get("title", "Report")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = spec.get("meta", {}) if isinstance(spec.get("meta"), dict) else {}
    watermark = meta.get("watermark") or f"{skill} · generated {generated} · deterministic JSON renderer"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{css_for(skill)}</style>
</head>
<body>
<main class="wrap">
{content}
<footer>{esc(watermark)}</footer>
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("output_html")
    parser.add_argument("--skip-spec-validation", action="store_true")
    parser.add_argument("--allow-account-ids", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    validate_script = script_dir / "validate_spec.py"
    spec_path = Path(args.spec).expanduser()
    out_path = Path(args.output_html).expanduser()

    if not args.skip_spec_validation:
        cmd = [sys.executable, str(validate_script), str(spec_path)]
        if args.allow_account_ids:
            cmd.append("--allow-account-ids")
        result = subprocess.run(cmd, text=True, capture_output=True)
        if result.returncode != 0:
            sys.stderr.write(result.stdout + result.stderr)
            return result.returncode

    spec = load_json(spec_path)
    html_text = render_document(spec)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
