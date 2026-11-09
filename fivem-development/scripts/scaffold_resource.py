#!/usr/bin/env python3
"""Generate a framework-neutral FiveM resource from the bundled templates.

  python scripts/scaffold_resource.py --name my_resource --dest ./resources --dry-run
  python scripts/scaffold_resource.py --name my_resource --dest ./resources --kind nui

kinds: basic (client command + server-authoritative event)  |  nui (basic + minimal HTML/JS UI)
Never overwrites an existing folder. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / 'assets' / 'templates'


def collect(kind: str) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    layers = [TEMPLATES / 'resource-basic'] + ([TEMPLATES / 'nui-overlay'] if kind == 'nui' else [])
    for layer in layers:
        for p in sorted(layer.rglob('*')):
            if p.is_file():
                files[p.relative_to(layer)] = p  # later layers override earlier ones
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--name', required=True)
    ap.add_argument('--dest', required=True, type=Path, help='existing parent folder (e.g. resources/[local])')
    ap.add_argument('--kind', choices=['basic', 'nui'], default='basic')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not re.fullmatch(r'[a-z][a-z0-9_-]{1,63}', args.name):
        ap.error('name: 2-64 chars, lowercase letters, digits, "_" or "-", starting with a letter')
    if not args.dest.is_dir():
        ap.error('--dest must be an existing folder')
    out = args.dest.resolve() / args.name
    if out.exists():
        ap.error(f'already exists, not overwriting: {out}')

    files = collect(args.kind)
    if not files:
        ap.error('templates not found next to this script')
    print(f'Destination: {out}  (kind: {args.kind})')
    for rel in sorted(files):
        print(' -', rel.as_posix())
    if args.dry_run:
        print('Dry run: nothing written.')
        return 0

    out.mkdir()
    try:
        for rel, src in files.items():
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(src.read_text(encoding='utf-8').replace('{{RESOURCE_NAME}}', args.name), encoding='utf-8')
    except Exception:
        shutil.rmtree(out, ignore_errors=True)
        raise
    print('Done. Not yet tested in a live FXServer: follow the resource README and references/10-audit-checklist.md.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
