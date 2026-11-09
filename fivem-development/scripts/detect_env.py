#!/usr/bin/env python3
"""Describe what a FiveM/RedM project actually uses, so nothing is assumed.

  python scripts/detect_env.py <project-or-resources-dir> [--json]

Reports: resources found, manifest facts (game, fx_version, NUI, dependencies), server.cfg facts
(ensure order, onesync, state-bag strict mode), known frameworks/libraries, and *unknown*
dependencies (a custom framework shows up here: read its code, never guess its API).
Standard library only; read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS = {'.git', 'node_modules', '.cache', '__pycache__'}
FRAMEWORKS = {'es_extended': 'ESX', 'qb-core': 'QBCore', 'qbx_core': 'Qbox', 'ox_core': 'Ox Core'}
LIBS = {'ox_lib': 'ox_lib', 'oxmysql': 'oxmysql', 'ox_inventory': 'ox_inventory', 'ox_target': 'ox_target',
        'mysql-async': 'mysql-async', 'ghmattimysql': 'ghmattimysql'}
MAX_FILE = 1_000_000
MAX_FILES = 6000


def walk(root: Path):
    count = 0
    for p in root.rglob('*'):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.is_file():
            count += 1
            if count > MAX_FILES:
                return
            yield p


def read(p: Path) -> str:
    try:
        if p.stat().st_size > MAX_FILE:
            return ''
        return p.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def strip_comments(text: str) -> str:
    text = re.sub(r'--\[(=*)\[.*?\]\1\]', '', text, flags=re.S)
    return re.sub(r'--[^\n]*', '', text)


def quoted(s: str) -> list[str]:
    return re.findall(r'[\'"]([^\'"]+)[\'"]', s)


def parse_manifest(path: Path) -> dict:
    text = strip_comments(read(path))
    info: dict = {'name': path.parent.name, 'path': str(path.parent), 'legacy': path.name == '__resource.lua'}
    m = re.search(r'fx_version\s+[\'"]([^\'"]+)', text)
    info['fx_version'] = m.group(1) if m else None
    games = re.search(r'games\s*\{([^}]*)\}', text)
    game = re.search(r'\bgame\s+[\'"]([^\'"]+)', text)
    info['games'] = quoted(games.group(1)) if games else ([game.group(1)] if game else [])
    info['lua54_yes'] = bool(re.search(r'lua54\s+[\'"]yes', text))
    ui = re.search(r'ui_page\s+[\'"]([^\'"]+)', text)
    info['ui_page'] = ui.group(1) if ui else None
    strict = re.search(r'nui_callback_strict_mode\s+[\'"]([^\'"]+)', text)
    info['nui_strict_mode'] = strict.group(1) if strict else None
    deps = [d for d in re.findall(r'\bdependency\s+[\'"]([^\'"]+)', text)]
    for block in re.findall(r'\bdependencies\s*\{([^}]*)\}', text):
        deps += quoted(block)
    info['dependencies'] = sorted(set(deps))
    info['has_client'] = bool(re.search(r'client_scripts?\b', text))
    info['has_server'] = bool(re.search(r'server_scripts?\b', text))
    return info


def parse_cfg(path: Path) -> dict:
    ensures, notes = [], []
    for raw in read(path).splitlines():
        line = raw.split('#', 1)[0].strip()
        m = re.match(r'(ensure|start|restart)\s+(\S+)', line)
        if m:
            ensures.append(m.group(2))
        if re.match(r'(set|setr|sets)\s+onesync\b', line):
            notes.append(line)
        if 'sv_stateBagStrictMode' in line:
            notes.append(line)
    return {'path': str(path), 'ensure': ensures, 'notes': notes}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('path', type=Path)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    root = args.path.resolve()
    if not root.is_dir():
        print(f'Not a directory: {root}', file=sys.stderr)
        return 2

    manifests, cfgs, texts = [], [], []
    for p in walk(root):
        if p.name in ('fxmanifest.lua', '__resource.lua'):
            manifests.append(parse_manifest(p))
        elif p.suffix == '.cfg':
            cfgs.append(parse_cfg(p))
        if p.suffix in ('.lua', '.cfg') or p.name == 'fxmanifest.lua':
            texts.append(read(p))

    resource_names = {m['name'] for m in manifests}
    blob = '\n'.join(texts)
    hits = Counter()
    for name in list(FRAMEWORKS) + list(LIBS):
        n = blob.count(name)
        if n or name in resource_names:
            hits[name] = n
    if re.search(r'\bMySQL\.', blob):
        hits['MySQL.* global (oxmysql-style lib)'] = len(re.findall(r'\bMySQL\.', blob))

    framework_found = {FRAMEWORKS[k]: v for k, v in hits.items() if k in FRAMEWORKS}
    libs_found = {LIBS[k]: v for k, v in hits.items() if k in LIBS}

    dep_users: dict[str, list[str]] = {}
    for m in manifests:
        for d in m['dependencies']:
            if d.startswith('/'):
                continue
            dep_users.setdefault(d, []).append(m['name'])
    known = set(FRAMEWORKS) | set(LIBS)
    unknown = {d: {'used_by': users, 'present_in_folder': d in resource_names}
               for d, users in dep_users.items() if d not in known}

    ensure_names = [e for c in cfgs for e in c['ensure']]
    unknown_ensured = sorted({e for e in ensure_names if e not in known and not e.startswith('[')})

    result = {
        'root': str(root),
        'resources': len(manifests),
        'games': sorted({g for m in manifests for g in m['games']}),
        'legacy_manifests': [m['name'] for m in manifests if m['legacy']],
        'lua54_yes_deprecated': [m['name'] for m in manifests if m['lua54_yes']],
        'nui_resources': [m['name'] for m in manifests if m['ui_page']],
        'nui_without_strict_mode': [m['name'] for m in manifests if m['ui_page'] and not m['nui_strict_mode']],
        'frameworks_detected': framework_found,
        'libraries_detected': libs_found,
        'unknown_dependencies': unknown,
        'server_cfg': [{'path': c['path'], 'ensure_count': len(c['ensure']), 'notes': c['notes']} for c in cfgs],
        'ensured_but_not_in_folder': [e for e in unknown_ensured if e not in resource_names][:40],
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Project: {result['root']}")
    print(f"Resources with a manifest: {result['resources']}   games: {', '.join(result['games']) or 'not stated'}")
    print('Frameworks (hints, not proof): ' + (', '.join(f'{k} ({v} mentions)' for k, v in framework_found.items()) or 'none detected'))
    print('Libraries: ' + (', '.join(f'{k} ({v})' for k, v in libs_found.items()) or 'none detected'))
    if unknown:
        print('\nUnknown dependencies (possible CUSTOM framework/libs - read their code, do not guess their API):')
        for d, info in sorted(unknown.items()):
            where = 'in this folder' if info['present_in_folder'] else 'NOT in this folder'
            print(f"  - {d} ({where}); used by: {', '.join(info['used_by'][:6])}")
    else:
        print('\nNo unknown manifest dependencies.')
    for c in result['server_cfg']:
        print(f"\nserver.cfg: {c['path']}  ({c['ensure_count']} ensure/start lines)")
        for n in c['notes']:
            print('  ' + n)
    if result['ensured_but_not_in_folder']:
        print('\nEnsured in cfg but not found here (external): ' + ', '.join(result['ensured_but_not_in_folder'][:15]))
    flags = []
    if result['legacy_manifests']:
        flags.append('legacy __resource.lua: ' + ', '.join(result['legacy_manifests'][:8]))
    if result['lua54_yes_deprecated']:
        flags.append("lua54 'yes' (deprecated): " + ', '.join(result['lua54_yes_deprecated'][:8]))
    if result['nui_without_strict_mode']:
        flags.append('NUI without nui_callback_strict_mode: ' + ', '.join(result['nui_without_strict_mode'][:8]))
    if flags:
        print('\nFlags:\n  - ' + '\n  - '.join(flags))
    print('\nNext: read the real code/manifest of every framework/unknown dependency before calling it.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
