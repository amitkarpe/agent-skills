#!/usr/bin/env python3
"""Generate a small Midnight Learning Dashboard scaffold.

This is intentionally dependency-free. It is a scaffold/smoke-test helper, not a
replacement for Codex writing a high-quality custom dashboard from the skill.
"""
from __future__ import annotations
import argparse
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "midnight-dashboard-template.html"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def card(icon: str, title: str, body: str) -> str:
    return f'<div class="card"><div class="icon">{icon}</div><h3>{esc(title)}</h3><p>{esc(body)}</p></div>'


def metric(label: str, body: str) -> str:
    return f'<div class="metric"><b>{esc(label)}</b><span>{esc(body)}</span></div>'


def flow_step(num: int, title: str, body: str) -> str:
    return f'<div class="step"><div class="num">{num}</div><h3>{esc(title)}</h3><p>{esc(body)}</p></div>'


def quiz(question: str, answer: str) -> str:
    return (
        '<div class="q"><b>' + esc(question) + '</b><br>'
        '<button onclick="this.parentElement.classList.toggle(\'open\')">Reveal answer</button>'
        '<div class="answer">' + esc(answer) + '</div></div>'
    )


def load_input(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")[:4000]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a dashboard scaffold")
    parser.add_argument("--title", required=True)
    parser.add_argument("--input", help="Optional markdown/text file to summarize into the scaffold")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = load_input(args.input)
    title = args.title.strip()
    thesis = "A visual learning dashboard for scanning, understanding, applying, and remembering this topic."
    if source:
        first = " ".join(source.split())[:220]
        thesis = first + ("..." if len(first) >= 220 else "")

    chips = "".join(f'<span class="pill">{esc(x)}</span>' for x in ["Visual map", "Workflow", "Decision guide", "Deep dives", "Recap quiz"])
    scorecards = "".join([
        metric("Scan", "Start with cards and nav"),
        metric("Map", "See the mental model"),
        metric("Apply", "Use examples/checklists"),
        metric("Recall", "Finish with quiz"),
    ])
    snapshot = "".join([
        card("&#x1F680;", "Why it matters", "Shows the topic in multiple forms instead of one dense text block."),
        card("&#x1F9E0;", "Mental model", "Turns abstract ideas into relationships, flows, and decisions."),
        card("&#x26A0;", "Watch-outs", "Separates facts, assumptions, risks, and open questions."),
    ])
    concept_map = (
        '<div class="model-card"><h3>Core idea</h3><p>What this topic is really about.</p><ul><li>Main purpose</li><li>Key components</li><li>Primary user impact</li></ul></div>'
        '<div class="arrow">&#x21C4;</div>'
        '<div class="model-card"><h3>Practical use</h3><p>How to apply it safely.</p><ul><li>Where it helps</li><li>When to avoid</li><li>How to validate</li></ul></div>'
    )
    flow = "".join([
        flow_step(1, "Input", "Collect the source material or code context."),
        flow_step(2, "Extract", "Find the important concepts, actors, and decisions."),
        flow_step(3, "Visualize", "Create map, flow, comparison, and timeline."),
        flow_step(4, "Apply", "Add examples, risks, and practical next actions."),
        flow_step(5, "Remember", "Finish with quiz and memory hooks."),
    ])
    compare = """
<table class="compare"><thead><tr><th>Lens</th><th>Simple view</th><th>Deep view</th></tr></thead>
<tbody><tr><td>Goal</td><td>Understand fast</td><td>Build reusable mental model</td></tr>
<tr><td>Best for</td><td>Quick scan</td><td>Permanent learning</td></tr>
<tr><td>Output</td><td>Cards and bullets</td><td>Dashboard, flow, quiz, risks</td></tr></tbody></table>
"""
    decision = "".join([
        '<div class="light"><h3><span class="dot green"></span>Use</h3><p>When content is dense, technical, or boring but important.</p></div>',
        '<div class="light"><h3><span class="dot yellow"></span>Customize</h3><p>When the topic needs AWS, codebase, incident, or research-specific views.</p></div>',
        '<div class="light"><h3><span class="dot red"></span>Avoid</h3><p>When a short answer is enough and no durable learning artifact is needed.</p></div>',
    ])
    deep = """
<details><summary>How to deepen this dashboard</summary><p>Add source-specific diagrams, timelines, code/file maps, risks, and validation checks.</p></details>
<details><summary>How to make it more ADHD-friendly</summary><p>Keep the first screen simple, hide dense text, add visual repetition, and end with active recall.</p></details>
"""
    quiz_block = "".join([
        quiz("What is the fastest section to read first?", "The 30-second view and decision guide."),
        quiz("Why show the same idea multiple ways?", "It improves recall and reduces reading fatigue."),
        quiz("Where should dense text go?", "Inside tabs or collapsible deep dives."),
    ])

    replacements = {
        "{{TITLE}}": esc(title),
        "{{THESIS}}": esc(thesis),
        "{{CHIPS}}": chips,
        "{{SCORECARDS}}": scorecards,
        "{{REMEMBER}}": "Understand the topic by scanning, then deepen only where needed.",
        "{{SNAPSHOT_CARDS}}": snapshot,
        "{{MAP_INTRO}}": "Use this map to see the topic as relationships, not a wall of text.",
        "{{CONCEPT_MAP}}": concept_map,
        "{{FLOW_STEPS}}": flow,
        "{{COMPARE_BLOCK}}": compare,
        "{{DECISION_GUIDE}}": decision,
        "{{TAB_OVERVIEW}}": "<p>Start here for the simplified view.</p>",
        "{{TAB_ENGINEER}}": "<p>Add implementation details, system boundaries, commands, or validation checks here.</p>",
        "{{TAB_MEMORY}}": "<p>Use this lane for mnemonics, flashcards, and recap questions.</p>",
        "{{DEEP_DIVES}}": deep,
        "{{QUIZ}}": quiz_block,
        "{{SOURCES}}": "<p>Generated scaffold. Replace with verified sources or assumptions.</p>",
    }
    html_doc = TEMPLATE.read_text(encoding="utf-8")
    for key, value in replacements.items():
        html_doc = html_doc.replace(key, value)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
