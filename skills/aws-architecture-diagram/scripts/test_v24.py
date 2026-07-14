#!/usr/bin/env python3
"""Deterministic MVP proof for v2.4 accessibility and clearance contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as StdET
from pathlib import Path

from clearance_lint import lint_clearance

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(*args: object, expect: int = 0) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, *(str(arg) for arg in args)]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != expect:
        raise AssertionError(
            f"command returned {completed.returncode}, expected {expect}: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def write_spec(path: Path, *, alt_text: object = "valid") -> None:
    spec = {
        "id": "v24-mvp",
        "name": "v2.4 MVP",
        "title": "Accessible Architecture MVP",
        "architecture_type": "overview",
        "audience": "Skill maintainers",
        "source_evidence": ["Deterministic v2.4 fixture"],
        "page": {"width": 1200, "height": 700, "background": "#FFFFFF"},
        "icon_mode": "none",
        "nodes": [
            {
                "id": "service",
                "provider": "external",
                "label": "Service under test",
                "variant": "label-only",
                "geometry": [400, 260, 400, 140],
                "icon_mode": "none",
            }
        ],
        "edges": [],
        "legend": False,
    }
    if alt_text == "valid":
        spec["alt_text"] = (
            "A single service card demonstrating accessible metadata and deterministic layout validation."
        )
        spec["long_description"] = (
            "The fixture contains one centered service with no external relationships so metadata flow can be tested in isolation."
        )
    elif alt_text is not None:
        spec["alt_text"] = alt_text
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def vertex(root: StdET.Element, cell_id: str, kind: str, rect: tuple[float, float, float, float], **attrs: str) -> None:
    cell = StdET.SubElement(
        root,
        "mxCell",
        {"id": cell_id, "data-kind": kind, "vertex": "1", "parent": "1", **attrs},
    )
    StdET.SubElement(
        cell,
        "mxGeometry",
        dict(zip(("x", "y", "width", "height"), map(str, rect))) | {"as": "geometry"},
    )


def clearance_root() -> tuple[StdET.Element, StdET.Element]:
    mxfile = StdET.Element("mxfile")
    diagram = StdET.SubElement(mxfile, "diagram")
    model = StdET.SubElement(diagram, "mxGraphModel")
    root = StdET.SubElement(model, "root")
    StdET.SubElement(root, "mxCell", {"id": "0"})
    StdET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    return mxfile, root


def test_clearance() -> None:
    for gap, expected_errors, expected_warnings in ((0, 1, 0), (4, 0, 1), (8, 0, 0)):
        mxfile, root = clearance_root()
        vertex(root, "card-a", "resource-card", (10, 10, 100, 80), **{"data-resource-id": "a"})
        vertex(root, "text-b", "annotation", (110 + gap, 10, 80, 30))
        before = hashlib.sha256(StdET.tostring(mxfile)).hexdigest()
        errors, warnings = lint_clearance(mxfile)
        after = hashlib.sha256(StdET.tostring(mxfile)).hexdigest()
        assert before == after, "clearance lint mutated XML"
        assert len(errors) == expected_errors, (gap, errors, warnings)
        assert len(warnings) == expected_warnings, (gap, errors, warnings)
        diagnostics = errors + warnings
        if diagnostics:
            assert "card-a" in diagnostics[0] and "text-b" in diagnostics[0]
            assert f"gap={gap:.2f}px" in diagnostics[0]

    def connector_fixture(
        *,
        source_label: tuple[float, float, float, float] | None = None,
        source_icon: tuple[float, float, float, float] | None = None,
        target_label: tuple[float, float, float, float] | None = None,
        target_icon: tuple[float, float, float, float] | None = None,
        caption: tuple[float, float, float, float] | None = None,
        points: tuple[tuple[float, float], ...] = (),
    ) -> StdET.Element:
        mxfile, root = clearance_root()
        vertex(root, "a", "resource-card", (10, 10, 100, 80), **{"data-resource-id": "a"})
        vertex(root, "b", "resource-card", (260, 10, 100, 80), **{"data-resource-id": "b"})
        for cell_id, kind, rect, resource_id in (
            ("a-label", "resource-label", source_label, "a"),
            ("a-icon", "resource-icon", source_icon, "a"),
            ("b-label", "resource-label", target_label, "b"),
            ("b-icon", "resource-icon", target_icon, "b"),
        ):
            if rect:
                vertex(root, cell_id, kind, rect, **{"data-resource-id": resource_id})
        if caption:
            vertex(root, "edge-a-b-caption", "relationship-caption", caption, **{"data-edge-id": "edge-a-b"})
        edge = StdET.SubElement(
            root,
            "mxCell",
            {
                "id": "edge-a-b",
                "data-kind": "relationship",
                "edge": "1",
                "parent": "1",
                "source": "a",
                "target": "b",
                "style": "exitX=1;exitY=0.5;entryX=0;entryY=0.5;",
            },
        )
        geometry = StdET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})
        if points:
            array = StdET.SubElement(geometry, "Array", {"as": "points"})
            for x, y in points:
                StdET.SubElement(array, "mxPoint", {"x": str(x), "y": str(y)})
        return mxfile

    valid = connector_fixture()
    before = hashlib.sha256(StdET.tostring(valid)).hexdigest()
    errors, warnings = lint_clearance(valid)
    after = hashlib.sha256(StdET.tostring(valid)).hexdigest()
    assert before == after, "connector clearance lint mutated XML"
    assert not errors and not warnings, (errors, warnings)

    cases = (
        ("source label", connector_fixture(source_label=(95, 35, 30, 30)), "a-label"),
        ("source icon", connector_fixture(source_icon=(95, 35, 30, 30)), "a-icon"),
        ("target label", connector_fixture(target_label=(245, 35, 30, 30)), "b-label"),
        ("target icon", connector_fixture(target_icon=(245, 35, 30, 30)), "b-icon"),
        ("own caption", connector_fixture(caption=(150, 40, 60, 20)), "edge-a-b-caption"),
        ("inward endpoint", connector_fixture(points=((90, 50),)), "a"),
    )
    for description, fixture, protected_id in cases:
        before = hashlib.sha256(StdET.tostring(fixture)).hexdigest()
        errors, warnings = lint_clearance(fixture)
        after = hashlib.sha256(StdET.tostring(fixture)).hexdigest()
        assert before == after, f"{description} fixture mutated"
        assert any(f"edge-a-b vs {protected_id} gap=0.00px" in error for error in errors), (
            description,
            errors,
            warnings,
        )


def add_annotation(source: Path, output: Path, *, gap: float) -> None:
    tree = StdET.parse(source)
    root = tree.getroot().find(".//root")
    assert root is not None
    vertex(root, "probe-text", "annotation", (800 + gap, 260, 40, 30))
    tree.write(output, encoding="utf-8", xml_declaration=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="aws-arch-v24-") as temp_name:
        temp = Path(temp_name)
        valid = temp / "valid.json"
        write_spec(valid)
        run(SCRIPTS / "validate_spec.py", valid)
        review_dir = temp / "review"
        run(
            SCRIPTS / "build_and_review.py",
            valid,
            review_dir,
            "--name",
            "v24-mvp",
            "--pass-number",
            "1",
            "--renderer",
            "preview",
        )
        drawio = StdET.parse(review_dir / "v24-mvp.pass-01.drawio").getroot()
        metadata = drawio.find(".//mxCell[@data-kind='diagram-metadata']")
        assert metadata is not None and metadata.get("data-alt-text")
        review = json.loads((review_dir / "v24-mvp.pass-01.review.json").read_text(encoding="utf-8"))
        assert review["accessibility"]["alt_text"] == metadata.get("data-alt-text")
        assert review["accessibility"]["raw_svg_sha256"] != review["accessibility"]["accessible_svg_sha256"]
        accessible_svg = (review_dir / "v24-mvp.pass-01.svg").read_text(encoding="utf-8")
        assert '<title id="diagram-title">' in accessible_svg and '<desc id="diagram-description">' in accessible_svg

        canonical_drawio = review_dir / "v24-mvp.pass-01.drawio"
        touching = temp / "touching.drawio"
        add_annotation(canonical_drawio, touching, gap=0)
        touching_result = run(SCRIPTS / "validate_drawio.py", touching, expect=1)
        assert "gap=0.00px" in touching_result.stdout and "service" in touching_result.stdout

        four_pixel = temp / "four-pixel.drawio"
        add_annotation(canonical_drawio, four_pixel, gap=4)
        four_normal = run(SCRIPTS / "validate_drawio.py", four_pixel)
        assert "WARN clearance service vs probe-text gap=4.00px" in four_normal.stdout
        four_strict = run(SCRIPTS / "validate_drawio.py", four_pixel, "--strict", expect=1)
        assert "FAIL warnings present in strict mode" in four_strict.stderr + four_strict.stdout

        eight_pixel = temp / "eight-pixel.drawio"
        add_annotation(canonical_drawio, eight_pixel, gap=8)
        eight_result = run(SCRIPTS / "validate_drawio.py", eight_pixel)
        assert "clearance service vs probe-text" not in eight_result.stdout

        legacy = temp / "legacy.json"
        write_spec(legacy, alt_text=None)
        normal = run(SCRIPTS / "validate_spec.py", legacy)
        assert "WARN legacy spec has no alt_text" in normal.stdout
        strict = run(SCRIPTS / "validate_spec.py", legacy, "--strict", expect=1)
        assert "FAIL warnings present in strict mode" in strict.stderr + strict.stdout

        placeholder = temp / "placeholder.json"
        write_spec(placeholder, alt_text="TBD")
        invalid = run(SCRIPTS / "validate_spec.py", placeholder, expect=1)
        assert "FAIL alt_text is placeholder text" in invalid.stdout

        native = json.loads(valid.read_text(encoding="utf-8"))
        native["icon_mode"] = "native"
        native["nodes"][0].update(
            {"provider": "aws", "variant": "icon-left", "icon_mode": "native", "icon_key": "amazon-ec2"}
        )
        native_path = temp / "native.json"
        native_path.write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
        native_drawio = temp / "native.drawio"
        run(SCRIPTS / "generate_drawio.py", native_path, native_drawio)
        invented = temp / "invented.drawio"
        invented.write_text(
            native_drawio.read_text(encoding="utf-8").replace(
                "resIcon=mxgraph.aws4.ec2", "resIcon=mxgraph.aws4.invented_aws2026_shape", 1
            ),
            encoding="utf-8",
        )
        invented_result = run(SCRIPTS / "validate_drawio.py", invented, expect=1)
        assert "invalid AWS4 shape references" in invented_result.stdout

    test_clearance()
    print("PASS v2.4 MVP accessibility-clearance tests")


if __name__ == "__main__":
    main()
