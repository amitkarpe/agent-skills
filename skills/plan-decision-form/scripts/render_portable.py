#!/usr/bin/env python3
"""Render a self-contained offline Decision Studio from a reviewed JSON specification."""
import argparse
import json
import re
from pathlib import Path

ID = re.compile(r'^[a-z][a-z0-9_-]{0,63}$')
SENSITIVE = re.compile(r'-----BEGIN .*PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bgh[oprsu]_[A-Za-z0-9]{20,}\b|\bsk-[A-Za-z0-9_-]{20,}\b', re.I)


def validate(data):
    if not isinstance(data, dict) or data.get('schema_version') != 'decision-packet/1':
        raise ValueError('schema_version must be decision-packet/1')
    if data.get('confirmation_mode', 'proposal_first') != 'proposal_first':
        raise ValueError('unconfirmed defaults only; pre-agreed requires separate owner opt-in')
    if not isinstance(data.get('source'), str) or not data['source'].strip():
        raise ValueError('source is required')
    if not isinstance(data.get('title'), str) or not data['title'].strip():
        raise ValueError('title is required')
    rows = data.get('decisions')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise ValueError('decisions must contain 1-30 choices')
    seen = set()
    for d in rows:
        if not isinstance(d, dict) or not isinstance(d.get('id'), str) or not ID.fullmatch(d['id']) or d['id'] in seen:
            raise ValueError('each decision needs a unique safe id')
        seen.add(d['id'])
        if not isinstance(d.get('title'), str) or not d['title'].strip():
            raise ValueError('decision title missing')
        if not isinstance(d.get('rationale'), str):
            raise ValueError('decision rationale must be text')
        choices = d.get('choices')
        if not isinstance(choices, list) or not 2 <= len(choices) <= 12 or any(not isinstance(x, str) or not x for x in choices) or len(set(choices)) != len(choices):
            raise ValueError('each decision needs 2-12 distinct choices')
        if d.get('recommended') not in choices:
            raise ValueError('recommended option must be in choices')
        if d.get('selected', d['recommended']) not in choices:
            raise ValueError('selected option must be in choices')
        if d.get('state', 'proposed') != 'proposed' or d.get('frozen', False) is not False:
            raise ValueError('specification cannot preconfirm owner decisions')
        d['selected'] = d.get('selected', d['recommended'])
        d['state'] = 'proposed'
        d['frozen'] = False
    raw = json.dumps(data, ensure_ascii=True)
    if SENSITIVE.search(raw) or len(raw) > 200000:
        raise ValueError('potential secret or oversized data rejected')
    return raw.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def validate_packet(spec, packet):
    if not isinstance(packet, dict) or packet.get('schema_version') != 'decision-packet/1':
        raise ValueError('invalid decision packet schema')
    if packet.get('source') != spec['source'] or packet.get('confirmation_mode') != 'proposal_first':
        raise ValueError('source or confirmation mode mismatch')
    rows = packet.get('decisions')
    if not isinstance(rows, list) or len(rows) != len(spec['decisions']):
        raise ValueError('missing or extra decisions')
    originals = {d['id']: d for d in spec['decisions']}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str):
            raise ValueError('invalid decision')
        base = originals.get(row['id'])
        if base is None or row['id'] in seen:
            raise ValueError('unknown or repeated decision id')
        seen.add(row['id'])
        if row.get('choices') != base['choices'] or row.get('selected') not in base['choices']:
            raise ValueError('invalid choices')
        if row.get('state') not in ('proposed', 'accepted') or type(row.get('frozen')) is not bool or row['frozen'] != (row['state'] == 'accepted'):
            raise ValueError('invalid confirmation')
    if SENSITIVE.search(json.dumps(packet, ensure_ascii=True)):
        raise ValueError('potential secret in exported packet')
    print(f"valid_decisions={len(rows)} accepted={sum(bool(x['frozen']) for x in rows)}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', required=True, type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--check-packet', type=Path, help='validate an exported packet against its source spec')
    a = p.parse_args()
    if not a.spec.is_file() or a.spec.stat().st_size > 256000:
        p.error('spec missing or too large')
    data = json.loads(a.spec.read_text(encoding='utf-8'))
    encoded = validate(data)
    if a.check_packet:
        if not a.check_packet.is_file() or a.check_packet.stat().st_size > 256000:
            p.error('packet missing or too large')
        validate_packet(data, json.loads(a.check_packet.read_text(encoding='utf-8')))
        return
    if not a.out:
        p.error('--out is required for HTML rendering')
    template = (Path(__file__).resolve().parent.parent / 'assets' / 'portable_studio.html').read_text(encoding='utf-8')
    if template.count('__DECISION_PACKET_JSON__') != 1:
        p.error('template placeholder missing or duplicated')
    if a.out.exists() and not a.out.is_file():
        p.error('output path is not a file')
    output = template.replace('__DECISION_PACKET_JSON__', encoded)
    a.out.write_text(output, encoding='utf-8')
    print(f'portable_html={a.out} decisions={len(data["decisions"])}')


if __name__ == '__main__':
    main()
