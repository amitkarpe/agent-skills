#!/usr/bin/env python3
"""Render and validate Agent Web plan decision forms."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
SAFE_QUESTION_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
SENSITIVE_KEY = re.compile(
    r"(^|[_-])(api[_-]?key|auth|cookie|credential|password|private[_-]?key|secret|token)([_-]|$)",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\b(?:gh[oprsu]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b"
)
CHOICE_TYPES = {"radio", "checkbox", "select"}
QUESTION_TYPES = CHOICE_TYPES | {"text", "textarea"}
FORM_KEYS = {
    "title",
    "goal",
    "decision_needed",
    "owner_label",
    "evidence",
    "sections",
    "allow_custom_direction",
}
DECISION_KEYS = {
    "schema_version",
    "status",
    "repo_name",
    "plan_id",
    "title",
    "submitted_by",
    "submitted_at",
    "answers",
}
DEFAULT_WEB_ROOT = Path("/opt/agent-web/web/amit/plans")
DEFAULT_PLANS_ROOT = Path("/opt/agent-share/plans")


def fail(message: str) -> None:
    raise ValueError(message)


def validate_id(value: str, label: str) -> str:
    if not SAFE_ID.fullmatch(value):
        fail(f"invalid {label}: use lowercase path-safe characters, maximum 80")
    return value


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_root(raw: str | None, default: Path, label: str) -> Path:
    root = Path(raw).expanduser().resolve() if raw else default.resolve()
    temp_root = Path(os.environ.get("AGENTS_TEMP_ROOT", str(Path.home() / ".AGENTS-temp"))).resolve()
    if root != default.resolve() and not is_under(root, temp_root):
        fail(f"{label} must be {default} or under {temp_root}")
    return root


def ensure_safe_output_parent(root: Path, components: tuple[str, ...]) -> Path:
    if root.is_symlink() or not root.is_dir():
        fail(f"output root must be an existing non-symlink directory: {root}")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors: list[int] = []
    current = root
    try:
        descriptors.append(os.open(root, flags))
        for component in components:
            try:
                descriptor = os.open(component, flags, dir_fd=descriptors[-1])
            except FileNotFoundError:
                try:
                    os.mkdir(component, mode=0o775, dir_fd=descriptors[-1])
                except FileExistsError:
                    pass
                try:
                    descriptor = os.open(component, flags, dir_fd=descriptors[-1])
                except OSError:
                    fail(f"refusing unsafe output parent: {current / component}")
            except OSError:
                fail(f"refusing unsafe output parent: {current / component}")
            descriptors.append(descriptor)
            current /= component
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    resolved = current.resolve()
    if not is_under(resolved, root):
        fail("resolved output parent escaped the allowed root")
    return resolved


def load_json(path: Path, max_bytes: int = 512 * 1024) -> Any:
    if not path.is_file() or path.is_symlink():
        fail(f"JSON input must be a regular non-symlink file: {path}")
    if path.stat().st_size > max_bytes:
        fail(f"JSON input is too large: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON: {exc}")


def validate_no_secrets(value: Any, location: str = "document") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE_KEY.search(str(key)):
                fail(f"secret-like field is not allowed at {location}")
            validate_no_secrets(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_no_secrets(item, f"{location}[{index}]")
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        fail(f"secret-like value is not allowed at {location}")


def require_text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        fail(f"{label} must be non-empty text, maximum {maximum} characters")
    return value.strip()


def validate_form(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict) or set(spec) - FORM_KEYS:
        fail("form spec has invalid top-level fields")
    require_text(spec.get("title"), "title", 240)
    require_text(spec.get("goal"), "goal")
    require_text(spec.get("decision_needed"), "decision_needed")
    if "owner_label" in spec:
        require_text(spec["owner_label"], "owner_label", 160)
    if "allow_custom_direction" in spec and not isinstance(spec["allow_custom_direction"], bool):
        fail("allow_custom_direction must be boolean")
    evidence = spec.get("evidence", [])
    if not isinstance(evidence, list) or len(evidence) > 12:
        fail("evidence must be a list with at most 12 items")
    for item in evidence:
        require_text(item, "evidence item")

    sections = spec.get("sections")
    if not isinstance(sections, list) or not sections or len(sections) > 7:
        fail("sections must contain 1-7 groups")
    question_count = 0
    seen_ids: set[str] = set()
    for section in sections:
        if not isinstance(section, dict) or set(section) - {"title", "detail", "questions"}:
            fail("section has invalid fields")
        require_text(section.get("title"), "section title", 200)
        if "detail" in section:
            require_text(section["detail"], "section detail")
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            fail("each section must contain questions")
        for question in questions:
            question_count += 1
            validate_question(question, seen_ids)
    if not 1 <= question_count <= 7:
        fail("form must contain 1-7 questions")
    validate_no_secrets(spec, "form")
    return spec


def validate_question(question: Any, seen_ids: set[str]) -> None:
    allowed = {"id", "label", "type", "required", "default", "detail", "placeholder", "options"}
    if not isinstance(question, dict) or set(question) - allowed:
        fail("question has invalid fields")
    question_id = question.get("id")
    if not isinstance(question_id, str) or not SAFE_QUESTION_ID.fullmatch(question_id):
        fail("question id must be lowercase and path-safe")
    if question_id == "additional_direction" or question_id in seen_ids:
        fail(f"duplicate or reserved question id: {question_id}")
    seen_ids.add(question_id)
    require_text(question.get("label"), f"question {question_id} label", 240)
    question_type = question.get("type")
    if question_type not in QUESTION_TYPES:
        fail(f"invalid question type for {question_id}")
    if "required" in question and not isinstance(question["required"], bool):
        fail(f"required must be boolean for {question_id}")
    for field in ("detail", "placeholder"):
        if field in question:
            require_text(question[field], f"question {question_id} {field}")
    if question_type not in CHOICE_TYPES:
        if "options" in question:
            fail(f"text question {question_id} cannot have options")
        if "default" in question and not isinstance(question["default"], str):
            fail(f"text default must be a string for {question_id}")
        return

    options = question.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 12:
        fail(f"choice question {question_id} needs 2-12 options")
    values: set[str] = set()
    for option in options:
        if not isinstance(option, dict) or set(option) - {"value", "label", "detail"}:
            fail(f"invalid option in {question_id}")
        value = require_text(option.get("value"), f"option value in {question_id}", 100)
        if value in values:
            fail(f"duplicate option value in {question_id}")
        values.add(value)
        require_text(option.get("label"), f"option label in {question_id}", 200)
        if "detail" in option:
            require_text(option["detail"], f"option detail in {question_id}")
    default = question.get("default")
    if question_type == "checkbox":
        if not isinstance(default, list) or not default or not all(item in values for item in default):
            fail(f"checkbox {question_id} needs a non-empty valid default list")
    elif not isinstance(default, str) or default not in values:
        fail(f"choice question {question_id} needs one valid default")


def render(args: argparse.Namespace) -> None:
    repo_name = validate_id(args.repo_name, "repository name")
    plan_id = validate_id(args.plan_id, "plan ID")
    spec = validate_form(load_json(Path(args.spec).expanduser().resolve()))
    payload = {"repo_name": repo_name, "plan_id": plan_id, **spec}
    encoded = json.dumps(payload, indent=2, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    output_html = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        f"  <title>{html.escape(spec['title'])}</title>\n"
        "  <link rel=\"stylesheet\" href=\"/amit/plans/assets/plan-form.css\">\n"
        "</head>\n<body>\n<main id=\"planApp\"></main>\n<script>\n"
        f"window.PLAN_FORM = {encoded};\n"
        "</script>\n<script src=\"/amit/plans/assets/plan-form.js\"></script>\n"
        "</body>\n</html>\n"
    )
    output_root = validate_root(args.output_root, DEFAULT_WEB_ROOT, "output root")
    target = ensure_safe_output_parent(output_root, (repo_name, plan_id)) / "index.html"
    if target.is_symlink():
        fail(f"refusing unsafe existing target: {target}")
    target = target.resolve()
    if not is_under(target, output_root):
        fail("resolved output target escaped the allowed root")
    if target.exists():
        if target.is_symlink() or not target.is_file():
            fail(f"refusing unsafe existing target: {target}")
        if target.read_text(encoding="utf-8") != output_html:
            fail(f"refusing to overwrite a different existing form: {target}")
        print(f"unchanged: {target}")
        return
    target.write_text(output_html, encoding="utf-8")
    target.chmod(0o664)
    print(f"created: {target}")
    print(f"url: http://home/amit/plans/{repo_name}/{plan_id}/")


def validate_decision(args: argparse.Namespace) -> None:
    repo_name = validate_id(args.repo_name, "repository name")
    plan_id = validate_id(args.plan_id, "plan ID")
    plans_root = validate_root(args.plans_root, DEFAULT_PLANS_ROOT, "plans root")
    target = (plans_root / repo_name / plan_id / "decision.json").resolve()
    if not is_under(target, plans_root):
        fail("resolved decision target escaped the allowed root")
    document = load_json(target)
    if not isinstance(document, dict) or set(document) != DECISION_KEYS:
        fail("decision must contain exactly the canonical fields")
    if document.get("schema_version") != 1 or document.get("status") != "submitted":
        fail("decision schema or status is invalid")
    if document.get("repo_name") != repo_name or document.get("plan_id") != plan_id:
        fail("decision identifiers do not match the canonical path")
    require_text(document.get("title"), "decision title", 240)
    if document.get("submitted_by") != "amit":
        fail("decision submitter is invalid")
    try:
        datetime.fromisoformat(str(document.get("submitted_at")))
    except ValueError:
        fail("submitted_at is not an ISO timestamp")
    answers = document.get("answers")
    if not isinstance(answers, dict) or len(answers) > 40:
        fail("answers must be an object with at most 40 fields")
    for key, value in answers.items():
        if not isinstance(key, str) or not SAFE_QUESTION_ID.fullmatch(key):
            fail("answer key is not path-safe")
        if isinstance(value, str):
            if len(value) > 16 * 1024:
                fail("answer text is too long")
        elif isinstance(value, list):
            if len(value) > 40 or not all(isinstance(item, str) and len(item) <= 500 for item in value):
                fail("answer list is invalid")
        elif not isinstance(value, bool):
            fail("answer value type is invalid")
    validate_no_secrets(document, "decision")
    print(f"valid: {target}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)
    render_parser = subparsers.add_parser("render", help="render a plan form")
    render_parser.add_argument("--repo-name", required=True)
    render_parser.add_argument("--plan-id", required=True)
    render_parser.add_argument("--spec", required=True)
    render_parser.add_argument("--output-root")
    render_parser.set_defaults(handler=render)
    decision_parser = subparsers.add_parser("validate-decision", help="validate the canonical submitted decision")
    decision_parser.add_argument("--repo-name", required=True)
    decision_parser.add_argument("--plan-id", required=True)
    decision_parser.add_argument("--plans-root")
    decision_parser.set_defaults(handler=validate_decision)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        args.handler(args)
        return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
