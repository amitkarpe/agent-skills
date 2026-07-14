#!/usr/bin/env python3
"""Bounded, entity-safe XML loading for draw.io and SVG artefacts."""

from __future__ import annotations

import io
import re
from pathlib import Path

import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException

MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_XML_DEPTH = 100
MAX_XML_ELEMENTS = 100_000


class XmlSafetyError(ValueError):
    """Raised when XML input is unsafe, malformed, or outside bounded limits."""


def safe_text(value: object, max_length: int = 100) -> str:
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(value))
    clean = re.sub(r"\s+", " ", clean).strip()
    clean = re.sub(r"[^\w\-.:# ]", "_", clean)
    return clean if len(clean) <= max_length else clean[:max_length] + "..."


def load_xml_root(path: Path) -> ET.Element:
    try:
        size = path.stat().st_size
        data = path.read_bytes()
    except OSError as exc:
        raise XmlSafetyError(f"cannot read XML: {safe_text(exc)}") from exc
    if size > MAX_FILE_SIZE:
        raise XmlSafetyError(f"XML exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB safety limit")

    depth = 0
    elements = 0
    try:
        for event, _ in ET.iterparse(io.BytesIO(data), events=("start", "end")):
            if event == "start":
                depth += 1
                elements += 1
                if depth > MAX_XML_DEPTH:
                    raise XmlSafetyError(f"XML nesting exceeds {MAX_XML_DEPTH} levels")
                if elements > MAX_XML_ELEMENTS:
                    raise XmlSafetyError(f"XML element count exceeds {MAX_XML_ELEMENTS}")
            else:
                depth -= 1
        return ET.fromstring(data)
    except XmlSafetyError:
        raise
    except (ET.ParseError, DefusedXmlException) as exc:
        raise XmlSafetyError(f"XML parse failed: {safe_text(exc)}") from exc
