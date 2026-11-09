#!/usr/bin/env python3
"""Install or update the fivem-development skill for several AI coding agents (Windows/macOS/Linux).

  python install.py --project /path/to/project            # copy into the project
  python install.py --project . --tools claude,codex       # only some agents
  python install.py --user                                 # for your user account, all projects
  python install.py --project . --update                   # replace an older install (keeps data/)
  python install.py --project . --mode symlink             # one real copy, links for the others

Where each agent looks for skills:
  claude   -> .claude/skills/        (Claude Code does NOT read .agents/skills)
  codex    -> .agents/skills/
  opencode -> .agents/skills/
  copilot  -> .github/skills/        (path from general documentation, not re-verified here)
Claude.ai (web/desktop): upload fivem-development.zip in the app's Skills settings instead.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

SKILL_NAME = 'fivem-development'
SOURCE = Path(__file__).resolve().parent / SKILL_NAME
TOOL_DIRS = {'claude': '.claude/skills', 'codex': '.agents/skills', 'opencode': '.agents/skills', 'copilot': '.github/skills'}
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store')
STAMP = time.strftime('%Y%m%d-%H%M%S')


def retire(dest: Path) -> Path | None:
    """Remove an old install. Symlinks are just unlinked; real folders are moved to a backup
    folder OUTSIDE skills/ (a backup inside skills/ would be loaded by the agent as a duplicate)."""
    if dest.is_symlink():
        dest.unlink()
        return None
    backup_root = dest.parent.parent / '.skill-backups'
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / f'{dest.name}-{STAMP}'
    n = 1
    while backup.exists():
        backup = backup_root / f'{dest.name}-{STAMP}-{n}'
        n += 1
    shutil.move(str(dest), str(backup))
    return backup


def copy_skill(dest: Path, update: bool) -> None:
    keep_data = None
    if dest.exists() or dest.is_symlink():
        if not update:
            raise SystemExit(f'Already installed at {dest}. Use --update to replace it.')
        old_data = dest / 'data'
        if old_data.is_dir() and not dest.is_symlink():
            keep_data = Path(str(dest) + '.data-keep')
            if keep_data.exists():
                shutil.rmtree(keep_data)
            shutil.move(str(old_data), str(keep_data))
        backup = retire(dest)
        if backup:
            print(f'  previous version moved to {backup}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, dest, ignore=IGNORE)
    if keep_data:
        target = dest / 'data'
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(keep_data), str(target))
        print('  kept your downloaded docs/natives (data/)')


def link_skill(dest: Path, real: Path, update: bool) -> bool:
    if dest.exists() or dest.is_symlink():
        if not update:
            raise SystemExit(f'Already installed at {dest}. Use --update to replace it.')
        backup = retire(dest)
        if backup:
            print(f'  previous version moved to {backup}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.symlink_to(real, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        return False  # e.g. Windows without symlink privilege


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument('--project', type=Path, help='project root to install into')
    where.add_argument('--user', action='store_true', help='install in your home folder')
    ap.add_argument('--tools', default='all', help='comma list: claude,codex,opencode,copilot or all')
    ap.add_argument('--mode', choices=['copy', 'symlink'], default='copy')
    ap.add_argument('--update', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not (SOURCE / 'SKILL.md').is_file():
        print(f'Skill folder not found next to install.py: {SOURCE}', file=sys.stderr)
        return 2
    tools = list(TOOL_DIRS) if args.tools == 'all' else [t.strip() for t in args.tools.split(',') if t.strip()]
    unknown = [t for t in tools if t not in TOOL_DIRS]
    if unknown:
        ap.error(f'unknown tool(s): {", ".join(unknown)}')
    if args.user:
        base = Path.home()
        tools = [t for t in tools if t != 'copilot']  # no per-user location documented here
    else:
        base = args.project.resolve()
        if not base.is_dir():
            ap.error('--project must be an existing folder')
    targets: list[Path] = []
    for t in tools:
        p = base / TOOL_DIRS[t] / SKILL_NAME
        if p not in targets:
            targets.append(p)

    print(f'Installing {SKILL_NAME} ({args.mode}) into:')
    for p in targets:
        print(' -', p)
    if args.dry_run:
        print('Dry run: nothing written.')
        return 0
    copy_skill(targets[0], args.update)
    print(f'[ok] {targets[0]}')
    for p in targets[1:]:
        if args.mode == 'symlink' and link_skill(p, targets[0], args.update):
            print(f'[ok] {p} (symlink)')
        else:
            if args.mode == 'symlink':
                print('  symlink not possible here; copying instead')
            copy_skill(p, args.update)
            print(f'[ok] {p}')
    print('\nNext: python <skill>/scripts/sync_docs.py   (downloads current docs and natives; needs git/internet)')
    if not args.user:
        print('Tip: add the installed skill folders to .gitignore if you do not want them in your repository.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
