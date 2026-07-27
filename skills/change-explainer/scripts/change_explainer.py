#!/usr/bin/env python3
"""Render a concise TXT/HTML change explanation from git diff and evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import pathlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass


try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
except Exception:  # pragma: no cover - fallback path
    Console = None
    Panel = None
    Table = None
    Tree = None


@dataclass
class Context:
    repo: pathlib.Path
    repo_name: str
    out_dir: pathlib.Path
    title: str
    why: str
    goal: str
    evidence: list[pathlib.Path]
    diff_stat: str
    changed_files: list[str]
    changed_items: list[tuple[str, str, str]]
    status: str
    detail: bool


def run(cmd: list[str], cwd: pathlib.Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        return ""
    return proc.stdout.rstrip()


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def repo_name(path: pathlib.Path) -> str:
    return path.resolve().name


def collect_evidence(paths: list[str]) -> list[pathlib.Path]:
    result: list[pathlib.Path] = []
    for raw in paths:
        p = pathlib.Path(raw).expanduser()
        if p.is_file():
            result.append(p)
        elif p.is_dir():
            candidates = []
            for pat in (
                "RESULT.md",
                "RESULT.env",
                "*.done",
                "*proof-output.txt",
                "*summary*.txt",
                "*validation*.txt",
                "*validation*.log",
                "*audit*.txt",
                "*check*.log",
                "stdout.txt",
                "stderr.txt",
                "status.txt",
                "command-invocation.json",
                "change-final.json",
            ):
                candidates.extend(p.rglob(pat))
            result.extend(sorted(candidates)[:20])
    return result[:40]


def build_context(args: argparse.Namespace) -> Context:
    repo = pathlib.Path(args.repo).expanduser().resolve()
    name = args.repo_name or repo_name(repo)
    out_dir = pathlib.Path(args.out_dir).expanduser() if args.out_dir else pathlib.Path.home() / ".AGENTS-temp" / name / "change-explainer"
    out_dir.mkdir(parents=True, exist_ok=True)
    diff_stat = run(["git", "diff", "--stat"], repo)
    status = run(["git", "status", "--short"], repo)
    changed_files = []
    changed_items = []
    for line in status.splitlines():
        if not line.strip():
            continue
        raw_code = line[:2].strip() if len(line) >= 2 else ""
        path = line[3:] if len(line) >= 4 and line[2] == " " else line.strip()
        if "D" in raw_code:
            action = "❌ Deleted"
        elif "?" in raw_code or "A" in raw_code:
            action = "❎ Added"
        elif "R" in raw_code:
            action = "🔁 Renamed"
        else:
            action = "👍🏽 Updated"
        changed_files.append(path)
        changed_items.append((action, path, raw_code or "M"))
    return Context(
        repo=repo,
        repo_name=name,
        out_dir=out_dir,
        title=args.title,
        why=args.why,
        goal=args.goal,
        evidence=collect_evidence(args.evidence),
        diff_stat=diff_stat,
        changed_files=changed_files[:40],
        changed_items=changed_items[:40],
        status=status,
        detail=args.detail,
    )


def detect_validation(ctx: Context) -> list[tuple[str, str]]:
    text = "\n".join([ctx.goal, ctx.why] + [read_small(p) for p in ctx.evidence])
    rows = []
    checks = [
        ("FQDN path", r"fqdn_proof=pass|mongo_uri_shape=fqdn|URI shape:\s*`?fqdn`?|replica_set_or_srv=ok|Replica set/SRV:\s*`?ok`?"),
        ("App auth", r"auth=ok|Auth:\s*`?ok`?|App can authenticate|app authentication"),
        ("CRUD cleanup", r"cleanup=ok|Cleanup:\s*`?ok`?|exists_after_cleanup=false|Exists after cleanup:\s*`?false`?|read/write/delete cleanup"),
        ("Secrets printed", r"secret_printed=no|secrets printed: no|Secret-pattern scan.*pass"),
        ("DNS/Route53", r"INSYNC|Route53|private DNS records"),
        ("PROD boundary", r"PROD.*untouched|no PROD mutation|PROD mutation still needs|PROD changes wait|PROD waits|30 June"),
        ("Script syntax", r"bash -n.*pass|py_compile|script_audit=pass|syntax.*pass"),
        ("Repo checks", r"check-skill-repo.*0 errors|diff_check=pass|git diff --check.*pass|checked=.*errors=0"),
    ]
    for label, pat in checks:
        rows.append((label, "PASS" if re.search(pat, text, re.I | re.S) else "CHECK"))
    return rows


def read_small(path: pathlib.Path) -> str:
    try:
        return path.read_text(errors="replace")[:8000]
    except Exception:
        return ""


def plain_output(ctx: Context) -> str:
    file_limit = 20 if ctx.detail else 8
    evidence_limit = 12 if ctx.detail else 5
    files = "\n".join(f"  {action} {ctx.repo_name}: {path}" for action, path, _ in ctx.changed_items[:file_limit]) or "  (no git diff files detected)"
    ev = "\n".join(f"  + {p}" for p in ctx.evidence[:evidence_limit]) or "  (no evidence paths supplied/found)"
    validations = "\n".join(f"  {'[PASS]' if r == 'PASS' else '[CHECK]'} {k}" for k, r in detect_validation(ctx))
    diff_stat = ctx.diff_stat or "(no git diff stat)"
    compact = f"""+------------------------------------------------------------+
| WHY THIS CHANGE MATTERS                                   |
+------------------------------------------------------------+
{ctx.why}

WHAT CHANGED
------------
Goal:
  {ctx.goal}

Before -> After:
  hard-to-scan raw diff -> change map + evidence file

FILES CHANGED
-------------
{files}

EVIDENCE
--------
{ev}

VALIDATION LEDGER
-----------------
{validations}

RISK / GATE FOOTER
------------------
REVERSIBLE  see repo/evidence rollback notes
BLAST       current repo/task scope only
PROD        no PROD mutation unless explicitly approved
SECRETS     never print credential values
"""
    if not ctx.detail:
        return compact
    code_delta = "\n".join(
        f"  {action} repo={ctx.repo_name} path={path}"
        for action, path, _ in ctx.changed_items[:20]
    ) or "  (no repo delta detected)"
    evidence_facts = "\n".join(
        f"  🟢 Evidence repo={ctx.repo_name} path={p}"
        for p in ctx.evidence[:12]
    ) or "  (no evidence facts supplied/found)"
    return compact + f"""

DETAIL: CAUSAL SPINE
--------------------
TRIGGER  {ctx.goal}
   |
   v
CHANGE   repo/code/infra updates in {ctx.repo_name}
   |
   v
EFFECT   task behavior is now easier to understand and validate
   |
   v
EVIDENCE saved result packets and validation outputs
   |
   v
GATE     PROD waits for explicit approval/date when applicable

DETAIL: DELTA / DIFF STAT
-------------------------
{diff_stat}

DETAIL: CODE / REPO DELTA
-------------------------
{code_delta}

DETAIL: AWS RESOURCES / EVIDENCE FACTS
--------------------------------------
{evidence_facts}

DETAIL: GOAL EXECUTION
----------------------
Goal:
  {ctx.goal}
Progress:
  {len(ctx.changed_files)} changed file paths and {len(ctx.evidence)} evidence files are mapped.
Status:
  PASS when required validation rows are green and boundary rows are held.

DETAIL: TASK IMPROVEMENT
------------------------
Next time:
  - Start with a change explainer so Amit can review why the work matters before reading logs.
Avoid:
  - Plain Markdown-only summaries for complex code/infra changes.
"""


def rich_output(ctx: Context, record: bool = False) -> Console:
    console = Console(record=record, width=110, color_system="truecolor")
    console.print(Panel(f"[bold]{ctx.why}[/bold]", title="🔥 WHY THIS CHANGE MATTERS", border_style="cyan"))
    console.print()
    changed_lines = [
        f"🎯 Goal: {ctx.goal}",
        "",
        "✗ before: hard-to-scan raw diff",
        "✓ after : change map + evidence file",
    ]
    if ctx.diff_stat:
        stat_preview = "\n".join(ctx.diff_stat.splitlines()[:5])
        changed_lines.extend(["", stat_preview])
    if ctx.changed_files:
        changed_lines.extend(["", "📁 Touched files:"])
        changed_lines.extend(f"  {action} {ctx.repo_name}: {path}" for action, path, _ in ctx.changed_items[:8])
    console.print(Panel("\n".join(changed_lines), title="🧩 WHAT CHANGED", border_style="magenta"))
    console.print()

    evidence_lines = [str(p) for p in ctx.evidence[:5]]
    if not evidence_lines:
        evidence_lines = ["(no evidence paths supplied/found)"]
    console.print(Panel("\n".join(evidence_lines), title="🧾 EVIDENCE", border_style="blue"))
    console.print()

    table = Table(title="✅ VALIDATION LEDGER", show_header=True, header_style="bold cyan")
    table.add_column("●", width=4)
    table.add_column("CHECK")
    table.add_column("RESULT")
    for label, status in detect_validation(ctx):
        glyph = "🟢" if status == "PASS" else "🟡"
        table.add_row(glyph, label, status)
    table.add_row("⛔", "PROD mutation", "boundary/date approval required")
    console.print(table)
    console.print()

    footer = "↺ REVERSIBLE  see repo/evidence rollback notes\n💥 BLAST       current repo/task scope only\n⛔ PROD        no PROD mutation unless explicitly approved\n🔒 SECRETS     never print credential values"
    console.print(Panel(footer, title="RISK / GATE", border_style="yellow"))
    if ctx.detail:
        console.print()
        tree = Tree("🧭 [bold cyan]DETAIL: CAUSAL SPINE[/bold cyan]")
        t1 = tree.add(f"TRIGGER  {ctx.goal}")
        t2 = t1.add(f"CHANGE   repo/code/infra updates in {ctx.repo_name}")
        t3 = t2.add("EFFECT   behavior is validated through evidence")
        t4 = t3.add("EVIDENCE result packets + validation outputs")
        t4.add("GATE     PROD waits for explicit approval/date when applicable")
        console.print(tree)
        console.print()
        code = Table(title="📁 DETAIL: CODE / REPO DELTA", show_header=True, header_style="bold cyan")
        code.add_column("Change", width=12)
        code.add_column("Repo", width=18)
        code.add_column("Path", overflow="fold")
        for action, path, _ in ctx.changed_items[:20]:
            code.add_row(action, ctx.repo_name, path)
        if not ctx.changed_items:
            code.add_row("🟡 None", ctx.repo_name, "(no git diff files detected)")
        console.print(code)
        console.print()
        facts = Table(title="☁ DETAIL: AWS RESOURCES / EVIDENCE FACTS", show_header=True, header_style="bold cyan")
        facts.add_column("Change", width=14)
        facts.add_column("Repo", width=18)
        facts.add_column("Evidence / fact", overflow="fold")
        for p in ctx.evidence[:12]:
            facts.add_row("🟢 Evidence", ctx.repo_name, str(p))
        if not ctx.evidence:
            facts.add_row("🟡 Missing", ctx.repo_name, "(no evidence paths supplied/found)")
        console.print(facts)
        console.print()
        goal = (
            f"Goal:\n  {ctx.goal}\n\n"
            "Progress:\n"
            f"  {len(ctx.changed_files)} changed file paths and {len(ctx.evidence)} evidence files are mapped.\n\n"
            "Status:\n"
            "  PASS when required validation rows are green and boundary rows are held."
        )
        console.print(Panel(goal, title="DETAIL: GOAL EXECUTION", border_style="green"))
        console.print()
        improvement = (
            "Next time:\n"
            "  - Generate a change explainer before final handoff so review starts from why and blast radius.\n"
            "Avoid:\n"
            "  - Leaving TXT/ANSI evidence unverified or relying only on raw diffs/logs."
        )
        console.print(Panel(improvement, title="DETAIL: TASK IMPROVEMENT", border_style="blue"))
    return console


def write_html(ctx: Context, path: pathlib.Path) -> None:
    file_items = "".join(f"<li>{html.escape(f)}</li>" for f in ctx.changed_files[:30])
    ev_items = "".join(f"<li>{html.escape(str(p))}</li>" for p in ctx.evidence[:20])
    rows = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(r)}</td></tr>" for k, r in detect_validation(ctx))
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(ctx.title)}</title>
<style>
body{{margin:0;background:#07111f;color:#edf7ff;font:16px system-ui,sans-serif;line-height:1.5}}
.wrap{{max-width:1180px;margin:auto;padding:28px}}.panel{{background:#0d1b2e;border:1px solid #25445f;border-radius:8px;padding:18px;margin:14px 0}}
h1{{font-size:42px;margin:0 0 10px}}h2{{margin:0 0 10px}}code{{color:#d9f99d}}.flow{{display:flex;gap:10px;flex-wrap:wrap}}
.box{{border:1px solid #315a7a;background:#10243b;border-radius:8px;padding:14px;min-width:150px}}.ok{{border-color:#4ade80}}.warn{{border-color:#fbbf24}}
table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #25445f;padding:8px;text-align:left}}
</style></head><body><main class="wrap">
<h1>🧭 {html.escape(ctx.title)}</h1>
<section class="panel"><h2>🔥 Why This Change Matters</h2><p>{html.escape(ctx.why)}</p></section>
<section class="panel"><h2>Path / Flow / Direction</h2><div class="flow">
<div class="box">TRIGGER<br><code>{html.escape(ctx.goal)}</code></div><div class="box">CHANGE<br>{html.escape(ctx.repo_name)}</div><div class="box ok">EFFECT<br>validated behavior</div><div class="box ok">EVIDENCE<br>saved proof</div><div class="box warn">GATE<br>approval/date</div>
</div></section>
<section class="panel"><h2>Files Changed</h2><ul>{file_items}</ul></section>
<section class="panel"><h2>Evidence</h2><ul>{ev_items}</ul></section>
<section class="panel"><h2>Validation Ledger</h2><table><tr><th>Check</th><th>Result</th></tr>{rows}</table></section>
</main></body></html>"""
    path.write_text(doc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", choices=["txt", "html", "both"], default="txt")
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--repo-name")
    parser.add_argument("--out-dir")
    parser.add_argument("--title", default="Change Explainer")
    parser.add_argument("--why", default="This change matters because it changes behavior, risk, or repeatability.")
    parser.add_argument("--goal", default="current task")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--slug", default=None)
    parser.add_argument("--detail", action="store_true", help="render expanded panels for complex changes")
    args = parser.parse_args()
    ctx = build_context(args)
    stamp = timestamp()
    raw_base = args.slug or f"change-explainer-{stamp}"
    base = re.sub(r"[^a-z0-9._-]+", "-", raw_base.lower()).strip("-._")
    if not base:
        base = "change-explainer"

    if args.mode in ("txt", "both"):
        if Console:
            console = rich_output(ctx, record=True)
            text = console.export_text(styles=False, clear=False)
            ansi = console.export_text(styles=True, clear=True)
        else:
            text = plain_output(ctx)
            ansi = text
            print(text)
        txt_path = ctx.out_dir / f"{base}.txt"
        ansi_path = ctx.out_dir / f"{base}.ansi"
        txt_path.write_text(text)
        ansi_path.write_text(ansi)
        if Console and ansi_path.stat().st_size == 0:
            raise RuntimeError(f"ANSI evidence file is empty: {ansi_path}")
        recommended = ansi_path if Console and ansi_path.stat().st_size > 0 else txt_path
        latest_path = pathlib.Path("/tmp/change.ansi")
        shutil.copyfile(recommended, latest_path)
        print(f"recommended_cat={recommended}")
        print(f"latest_change={latest_path}")
        print(f"txt_evidence={txt_path}")
        print(f"ansi_evidence={ansi_path}")

    if args.mode in ("html", "both"):
        html_dir = pathlib.Path("/opt/crypto-web/demos") / base
        html_dir.mkdir(parents=True, exist_ok=True)
        html_path = html_dir / "index.html"
        write_html(ctx, html_path)
        url = f"http://home/demos/{base}/"
        if not shutil.which("curl"):
            raise RuntimeError("HTML written but URL validation requires curl")
        check = subprocess.run(
            ["curl", "-fsSI", "--max-time", "5", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if check.returncode != 0:
            raise RuntimeError(f"HTML written but URL validation failed: {url}")
        print(f"html={url}")
        print(f"html_file={html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
