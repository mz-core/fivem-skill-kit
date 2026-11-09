#!/usr/bin/env python3
"""Look up natives and documentation in the local cache created by sync_docs.py.

  python scripts/lookup.py native GetPlayerPed        # PascalCase, UPPER_SNAKE or 0xHASH
  python scripts/lookup.py docs "state bags"
  python scripts/lookup.py status

`native` prints one of three statuses (exit code):
  FOUND       (0)  a definition exists in the synced official sources; API set and source are shown
  NOT FOUND   (1)  both official sources are synced and none defines it. NOT proof it does not exist
  UNVERIFIED  (3)  cannot tell: no data, a source is missing, or the name is only mentioned in text
A name that merely appears in prose or in an example never counts as FOUND.
Standard library only.
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('_natives', _HERE / '_natives.py')
nat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nat)

SKILL_DIR = _HERE.parent
DATA = Path(os.environ.get('FIVEM_SKILL_DATA', SKILL_DIR / 'data'))
DOCS_BASE = 'https://docs.fivem.net/docs/'
NATIVES_SITE = 'https://docs.fivem.net/natives/'


def manifest() -> dict:
    path = DATA / 'manifest.json'
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return {}
    return {}


def fetched(info: dict | None) -> str:
    return (info or {}).get('fetched_at', 'unknown date')


def snippet(lines: list[str], idx: int, before: int = 2, after: int = 14) -> str:
    return '\n'.join(lines[max(0, idx - before): min(len(lines), idx + after)])


def cmd_native(args) -> int:
    raw = args.name
    is_hash = bool(re.fullmatch(r'0[xX][0-9A-Fa-f]{4,16}', raw))
    snake = raw if is_hash else nat.to_snake(raw)
    state = nat.source_state(DATA)
    present = {d: n for d, n in state.items() if n > 0}
    missing = [nat.SOURCE_DIRS[d] for d in nat.SOURCE_DIRS if d not in present]

    defs: list[dict] = []
    mentions: list[Path] = []
    for d in present:
        dd, mm = nat.find_definitions(DATA / d, raw, is_hash)
        for x in dd:
            x['source'] = d
        defs += dd
        mentions += mm

    if defs:
        print(f'STATUS: FOUND   name: {snake}' + ('' if is_hash else f'   (searched: {raw})'))
        print(f'Definitions: {len(defs)}')
        defs.sort(key=lambda x: (x['source'] != 'natives-cfx', str(x['path'])))
        for i, d in enumerate(defs[: args.limit], 1):
            rel = d['path'].relative_to(DATA)
            api = d['apiset'] or 'not stated in source'
            print(f"\n[{i}] API set: {api} | ns: {d['ns'] or '-'} | source: {nat.SOURCE_DIRS[d['source']]}")
            print(f"    file: {rel.as_posix()}:{d['line'] + 1}")
            print(snippet(d['lines'], d['line']))
        apis = {d['apiset'] for d in defs}
        if len(defs) > 1:
            print('\nNote: several definitions share this name. Pick the one that matches your side (client/server) and game.')
        elif not defs[0]['apiset']:
            print('\nNote: this source does not state client/server/shared. Check the native page on ' + NATIVES_SITE + ' before using it server-side.')
        if len(apis) > 1:
            print('Note: definitions disagree on the API set; do not assume it is available on both sides.')
        return 0

    # not found as a definition -> is the cache complete enough to say "not found"?
    reason = None
    if not present:
        reason = f'no natives data in {DATA}. Run: python scripts/sync_docs.py   (needs git/internet)'
    elif missing:
        reason = 'these official sources are not synced: ' + '; '.join(missing) + '. Run: python scripts/sync_docs.py'
    mention_note = ''
    if mentions:
        shown = ', '.join(p.relative_to(DATA).as_posix() for p in mentions[:3])
        mention_note = f'The name appears only in text/examples ({shown}); that is NOT a definition and does not confirm it exists.'

    if reason:
        print(f'STATUS: UNVERIFIED   name: {snake}')
        print(f'Reason: {reason}')
        if mention_note:
            print(mention_note)
        print(f'Do not claim it exists or not: confirm on {NATIVES_SITE} and tell the user it is unverified.')
        return 3

    names: set[str] = set()
    for d in present:
        names |= nat.known_names(DATA / d)
    close = difflib.get_close_matches(snake, sorted(names), n=6, cutoff=0.72)
    m = manifest()
    dates = ', '.join(f"{d}: {fetched(m.get(d.replace('-', '_')))}" for d in present)
    print(f'STATUS: NOT FOUND   name: {snake}   (searched: {raw})')
    print(f'No definition in the synced official sources ({dates}).')
    if mention_note:
        print(mention_note)
    print('This is NOT proof that it does not exist (very new native, other game, outdated cache).')
    print(f'Do not use it until confirmed on {NATIVES_SITE}; do not tell the user it is invalid without that check.')
    if close:
        print('Closest names: ' + ', '.join(close))
    return 1


def title_of(text: str, fallback: str) -> str:
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.M)
    if m:
        return m.group(1)
    m = re.search(r'^#\s+(.+)$', text, re.M)
    return m.group(1) if m else fallback


def doc_url(rel: Path) -> str:
    parts = list(rel.with_suffix('').parts)
    if parts and parts[-1] == '_index':
        parts = parts[:-1]
    return DOCS_BASE + '/'.join(parts) + '/'


def cmd_docs(args) -> int:
    root = DATA / 'docs'
    if not root.is_dir() or not any(root.iterdir()):
        print(f'STATUS: UNVERIFIED\nNo local docs in {DATA}. Run: python scripts/sync_docs.py   (needs git/internet)\n'
              'Without it, say the information is unverified and point to https://docs.fivem.net/', file=sys.stderr)
        return 3
    terms = [t.lower() for t in re.findall(r'\w+', ' '.join(args.query))]
    if not terms:
        print('Give at least one search word.', file=sys.stderr)
        return 1
    scored = []
    for p in nat.iter_files(root):
        text = nat.read(p)
        low = text.lower()
        rel = p.relative_to(root)
        path_low = str(rel).lower()
        counts = [low.count(t) for t in terms]
        if not any(counts):
            continue
        score = sum(min(c, 30) for c in counts) + 8 * sum(t in path_low for t in terms)
        if all(counts):
            score *= 2
        scored.append((score, p, rel, text))
    if not scored:
        print('No matching documentation found locally. Try other words or check https://docs.fivem.net/')
        return 1
    scored.sort(key=lambda s: -s[0])
    for score, p, rel, text in scored[: args.limit]:
        print(f'## {title_of(text, p.stem)}\n{doc_url(rel)}   (local: docs/{rel.as_posix()}, score {score})')
        shown = 0
        for line in text.splitlines():
            if any(t in line.lower() for t in terms) and line.strip():
                print('   ' + line.strip()[:200])
                shown += 1
                if shown >= args.lines:
                    break
        print()
    return 0


def cmd_status(_args) -> int:
    m = manifest()
    state = nat.source_state(DATA)
    docs_n = sum(1 for _ in nat.iter_files(DATA / 'docs')) if (DATA / 'docs').is_dir() else 0
    print(f'Data folder: {DATA}')
    print(f"docs:         {'ok' if docs_n else 'MISSING'} ({docs_n} files, fetched {fetched(m.get('docs'))})")
    for d, label in nat.SOURCE_DIRS.items():
        key = d.replace('-', '_')
        print(f"{d:13s} {'ok' if state[d] else 'MISSING'} ({state[d]} files, fetched {fetched(m.get(key))})  {label}")
    if not (docs_n and all(state.values())):
        print('Some sources are missing: native lookups will be UNVERIFIED. Run: python scripts/sync_docs.py')
        return 3
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    n = sub.add_parser('native', help='check a native: FOUND / NOT FOUND / UNVERIFIED')
    n.add_argument('name')
    n.add_argument('--limit', type=int, default=3, help='max definitions to print')
    n.set_defaults(fn=cmd_native)
    d = sub.add_parser('docs', help='search the documentation')
    d.add_argument('query', nargs='+')
    d.add_argument('--limit', type=int, default=5)
    d.add_argument('--lines', type=int, default=3)
    d.set_defaults(fn=cmd_docs)
    s = sub.add_parser('status', help='show which sources are synced and when')
    s.set_defaults(fn=cmd_status)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    raise SystemExit(main())
