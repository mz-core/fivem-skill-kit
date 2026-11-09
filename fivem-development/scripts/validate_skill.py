#!/usr/bin/env python3
"""Validate the skill package (structure, frontmatter, links, neutrality). Exit 1 on any error.

  python scripts/validate_skill.py            # offline checks
  python scripts/validate_skill.py --links    # also check that URLs in references/ respond

Token budgets (SKILL.md, each reference, all references) are TARGETS: exceeding them prints a WARN and
never fails the run, so a good technical reference is never cut just to fit a number.

Checks follow the Agent Skills specification rules for SKILL.md (name/description limits) plus
project rules: every referenced file exists, every reference is routed from SKILL.md, scripts
compile, no framework-specific leftovers, evals.json is valid.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
errors: list[str] = []
warnings: list[str] = []

# built from pieces so this file does not match its own rule
LEFTOVERS = re.compile('|'.join(['m' + 'z_', 'M' + 'Z Core', 'm' + 'z-core']), re.I)


def err(msg: str) -> None:
    errors.append(msg)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', text, re.S)
    if not m:
        err('SKILL.md: missing YAML frontmatter')
        return {}, text
    fm: dict = {}
    current = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if line.startswith((' ', '\t')) and current:
            k, _, v = line.strip().partition(':')
            fm.setdefault(current, {})[k.strip()] = v.strip().strip('"\'')
        else:
            k, _, v = line.partition(':')
            current = k.strip()
            fm[current] = v.strip() if v.strip() else {}
    return fm, m.group(2)


def check_skill_md() -> str:
    path = SKILL / 'SKILL.md'
    if not path.is_file():
        err('SKILL.md not found')
        return ''
    fm, body = parse_frontmatter(path.read_text(encoding='utf-8'))
    name = fm.get('name', '')
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', str(name)) or len(str(name)) > 64:
        err(f'name invalid: {name!r} (lowercase letters/digits/single hyphens, max 64)')
    if name != SKILL.name:
        err(f'name {name!r} must equal the folder name {SKILL.name!r}')
    desc = str(fm.get('description', ''))
    if not desc:
        err('description is empty')
    if len(desc) > 1024:
        err(f'description is {len(desc)} chars (max 1024)')
    if len(str(fm.get('compatibility', ''))) > 500:
        err('compatibility longer than 500 chars')
    lines = body.count('\n') + 1
    if lines > 500:
        err(f'SKILL.md body has {lines} lines (keep under 500; move detail to references/)')
    return body


def check_links(body: str) -> None:
    referenced = set()
    for m in re.finditer(r'`((?:references|scripts|assets|evals)/[^`\s]+)`', body):
        rel = m.group(1).rstrip('.,;:')
        referenced.add(rel)
        if not (SKILL / rel).exists():
            err(f'SKILL.md references a missing path: {rel}')
    for ref in sorted((SKILL / 'references').glob('*.md')):
        if f'references/{ref.name}' not in referenced:
            err(f'references/{ref.name} is not routed from SKILL.md')


def check_scripts() -> None:
    for py in sorted((SKILL / 'scripts').glob('*.py')):
        try:
            compile(py.read_text(encoding='utf-8'), str(py), 'exec')  # syntax check only, writes nothing
        except SyntaxError as exc:
            err(f'script does not compile: {py.name}: {exc}')


def check_neutrality() -> None:
    for p in SKILL.rglob('*'):
        if not p.is_file() or 'data' in p.relative_to(SKILL).parts[:1] or p.suffix in ('.zip', '.pyc'):
            continue
        try:
            text = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        m = LEFTOVERS.search(text)
        if m:
            err(f'framework-specific leftover {m.group(0)!r} in {p.relative_to(SKILL)}')


def check_evals() -> None:
    path = SKILL / 'evals' / 'evals.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        ids = [e['id'] for e in data['evals']]
        if len(ids) != len(set(ids)):
            err('evals.json: duplicate ids')
        for e in data['evals']:
            if not e.get('prompt') or not e.get('must'):
                err(f"evals.json: {e.get('id')} needs prompt and must")
    except Exception as exc:  # noqa: BLE001
        err(f'evals/evals.json invalid: {exc}')


def check_size() -> None:
    total = 0
    for p in SKILL.rglob('*'):
        if p.is_file() and p.relative_to(SKILL).parts[0] != 'data':
            total += p.stat().st_size
    if total > 1_500_000:
        warnings.append(f'package is {total // 1024} KiB (excluding data/)')


BUDGET = {'skill': 2000, 'reference': 1600, 'references_total': 12000}   # estimated tokens, warnings only


def est_tokens(text: str) -> int:
    return round(len(text) / 4)   # rough: ~4 characters per token (varies by model and language)


def check_budget() -> None:
    skill = est_tokens((SKILL / 'SKILL.md').read_text(encoding='utf-8'))
    if skill > BUDGET['skill']:
        warnings.append(f"budget: SKILL.md ~{skill} tokens (target {BUDGET['skill']})")
    total = 0
    for ref in sorted((SKILL / 'references').glob('*.md')):
        n = est_tokens(ref.read_text(encoding='utf-8'))
        total += n
        if n > BUDGET['reference']:
            warnings.append(f"budget: references/{ref.name} ~{n} tokens (target {BUDGET['reference']}); split or trim only if it is not valuable technical content")
    if total > BUDGET['references_total']:
        warnings.append(f"budget: references total ~{total} tokens (target {BUDGET['references_total']})")
    print(f"tokens (estimate): SKILL.md ~{skill}, references ~{total}")


def check_read_when() -> None:
    for ref in sorted((SKILL / 'references').glob('*.md')):
        if not any(l.startswith('> Read when:') for l in ref.read_text(encoding='utf-8').splitlines()[:6]):
            err(f'references/{ref.name} has no "> Read when:" line near the top')


def check_urls() -> None:
    urls = set()
    for p in (SKILL / 'references').glob('*.md'):
        urls.update(u.rstrip('.,);') for u in re.findall(r'https?://[^\s`|)]+', p.read_text(encoding='utf-8')))
    for u in sorted(urls):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'fivem-skill-validate'})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status >= 400:
                    warnings.append(f'URL status {r.status}: {u}')
        except Exception as exc:  # noqa: BLE001
            warnings.append(f'URL not reachable ({exc.__class__.__name__}): {u}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--links', action='store_true', help='also fetch URLs found in references/ (needs internet)')
    args = ap.parse_args()
    body = check_skill_md()
    check_links(body)
    check_scripts()
    check_neutrality()
    check_evals()
    check_size()
    check_read_when()
    check_budget()
    if args.links:
        check_urls()
    for w in warnings:
        print('WARN ', w)
    for e in errors:
        print('ERROR', e)
    print(f'\n{"FAILED" if errors else "OK"}: {len(errors)} error(s), {len(warnings)} warning(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
