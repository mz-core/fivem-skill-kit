#!/usr/bin/env python3
"""Download the official Cfx.re documentation and natives into <skill>/data/ for offline lookup.

  python scripts/sync_docs.py                    # refresh all three sources
  python scripts/sync_docs.py --only natives_cfx
  python scripts/sync_docs.py --check            # report age, exit 3 if stale, 2 if missing

Sources:
  docs         https://github.com/citizenfx/fivem-docs  (only content/docs is kept)  -> data/docs
  natives      https://github.com/citizenfx/natives     (GTA V natives)               -> data/natives
  natives_cfx  https://github.com/citizenfx/fivem       (only ext/native-decls: CFX natives
               with their `apiset`, e.g. GetPlayerPed on the server)                  -> data/natives-cfx
git is tried first; a GitHub zip is the fallback for docs/natives. natives_cfx needs git (sparse
clone) because the whole-repository zip is very large.
Standard library only. A failed download never damages existing data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path(os.environ.get('FIVEM_SKILL_DATA', SKILL_DIR / 'data'))
SOURCES = {
    'docs': {'url': 'https://github.com/citizenfx/fivem-docs', 'subdir': 'content/docs', 'dir': 'docs'},
    'natives': {'url': 'https://github.com/citizenfx/natives', 'subdir': '', 'dir': 'natives'},
    'natives_cfx': {'url': 'https://github.com/citizenfx/fivem', 'subdir': 'ext/native-decls', 'dir': 'natives-cfx',
                    'sparse': True, 'zip_ok': False},
}
KEEP_EXT = {'.md', '.json', '.lua', '.txt', '.yml', '.yaml'}
SKIP_DIRS = {'.git', 'node_modules', '.github'}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def run_git(args: list[str], cwd: Path | None = None) -> str:
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    out = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=1800)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f'git {args[0]} failed')
    return out.stdout.strip()


def fetch_git(url: str, dest: Path, sparse_subdir: str | None = None) -> tuple[Path, str]:
    if sparse_subdir:
        try:  # blobless sparse clone: downloads only the needed folder
            run_git(['clone', '--depth', '1', '--filter=blob:none', '--sparse', '--quiet', url, str(dest)])
        except RuntimeError:  # server without partial-clone support: slower but works
            shutil.rmtree(dest, ignore_errors=True)
            run_git(['clone', '--depth', '1', '--sparse', '--quiet', url, str(dest)])
        run_git(['sparse-checkout', 'set', sparse_subdir], cwd=dest)
    else:
        run_git(['clone', '--depth', '1', '--quiet', url, str(dest)])
    return dest, run_git(['rev-parse', 'HEAD'], cwd=dest)


def fetch_zip(url: str, dest: Path) -> tuple[Path, str]:
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / 'src.zip'
    with urllib.request.urlopen(url, timeout=300) as resp, open(archive, 'wb') as fh:
        shutil.copyfileobj(resp, fh)
    root = dest / 'unzipped'
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(root)
    entries = list(root.iterdir())
    top = entries[0] if len(entries) == 1 and entries[0].is_dir() else root
    return top, 'unknown (zip download)'


def copy_subset(src_root: Path, subdir: str, dst: Path) -> int:
    base = src_root / subdir if subdir else src_root
    if not base.is_dir():
        raise RuntimeError(f'expected folder not found in download: {subdir or "."}')
    count = 0
    for path in base.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(base)
        if any(part in SKIP_DIRS for part in rel.parts) or path.suffix.lower() not in KEEP_EXT:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
    return count


def sync_one(key: str, url: str, zip_url: str | None, method: str, data_dir: Path) -> dict:
    spec = SOURCES[key]
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f'sync_{key}_', dir=data_dir))
    try:
        errors: list[str] = []
        fetched = None
        used = None
        commit = ''
        if method in ('auto', 'git') and shutil.which('git'):
            try:
                fetched, commit = fetch_git(url, tmp / 'git', spec['subdir'] if spec.get('sparse') else None)
                used = 'git'
            except Exception as exc:  # noqa: BLE001 - report and fall back
                errors.append(f'git: {exc}')
        elif method == 'git':
            errors.append('git: not installed')
        if fetched is None and method in ('auto', 'zip'):
            candidate = zip_url
            if not candidate and spec.get('zip_ok', True) and url.startswith('https://github.com/'):
                candidate = url.rstrip('/') + '/archive/HEAD.zip'
            if candidate:
                try:
                    fetched, commit = fetch_zip(candidate, tmp / 'zip')
                    used = 'zip'
                except Exception as exc:  # noqa: BLE001
                    errors.append(f'zip: {exc}')
            elif not spec.get('zip_ok', True):
                errors.append(f"{key} needs git (sparse clone); the full-repository zip is too large. "
                              f"Install git, or copy {spec['subdir']} manually into {data_dir / spec['dir']}")
            else:
                errors.append('zip: no zip URL available for this source')
        if fetched is None:
            raise RuntimeError('; '.join(errors) or 'no download method available')

        staged = tmp / 'out'
        count = copy_subset(fetched, spec['subdir'], staged)
        if count == 0:
            raise RuntimeError('download contained no usable files')
        final = data_dir / spec['dir']
        backup = data_dir / f".{spec['dir']}.old"
        if backup.exists():
            shutil.rmtree(backup)
        if final.exists():
            final.rename(backup)
        shutil.move(str(staged), str(final))
        if backup.exists():
            shutil.rmtree(backup)
        return {'source': url, 'method': used, 'commit': commit, 'fetched_at': now_iso(), 'files': count}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_manifest(data_dir: Path) -> dict:
    path = data_dir / 'manifest.json'
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return {}
    return {}


def check(data_dir: Path, max_age_days: int) -> int:
    manifest = load_manifest(data_dir)
    if not manifest:
        print(f'No data in {data_dir}. Run: python scripts/sync_docs.py')
        return 2
    code = 0
    for key in SOURCES:
        info = manifest.get(key)
        if not info:
            print(f'{key}: missing (native lookups stay UNVERIFIED until it is synced)')
            code = max(code, 2)
            continue
        fetched = dt.datetime.strptime(info['fetched_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
        age = (dt.datetime.now(dt.timezone.utc) - fetched).days
        flag = 'STALE' if age > max_age_days else 'ok'
        print(f"{key}: {flag} - {age} day(s) old, {info.get('files')} files, via {info.get('method')}, commit {str(info.get('commit'))[:12]}")
        if age > max_age_days:
            code = max(code, 3)
    return code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data-dir', type=Path, default=DEFAULT_DATA)
    ap.add_argument('--only', choices=sorted(SOURCES))
    ap.add_argument('--method', choices=['auto', 'git', 'zip'], default='auto')
    ap.add_argument('--docs-url', default=SOURCES['docs']['url'])
    ap.add_argument('--natives-url', default=SOURCES['natives']['url'])
    ap.add_argument('--natives-cfx-url', default=SOURCES['natives_cfx']['url'])
    ap.add_argument('--docs-zip', help='override zip URL (also file:// for tests)')
    ap.add_argument('--natives-zip', help='override zip URL (also file:// for tests)')
    ap.add_argument('--natives-cfx-zip', help='override zip URL (also file:// for tests)')
    ap.add_argument('--check', action='store_true', help='report data age instead of downloading')
    ap.add_argument('--max-age-days', type=int, default=30)
    args = ap.parse_args()

    if args.check:
        return check(args.data_dir, args.max_age_days)

    urls = {'docs': (args.docs_url, args.docs_zip), 'natives': (args.natives_url, args.natives_zip),
            'natives_cfx': (args.natives_cfx_url, args.natives_cfx_zip)}
    manifest = load_manifest(args.data_dir)
    failed = False
    for key in ([args.only] if args.only else list(SOURCES)):
        url, zip_url = urls[key]
        print(f'[{key}] downloading {url} ...')
        try:
            manifest[key] = sync_one(key, url, zip_url, args.method, args.data_dir)
            info = manifest[key]
            print(f"[{key}] ok: {info['files']} files via {info['method']} (commit {str(info['commit'])[:12]})")
        except Exception as exc:  # noqa: BLE001
            failed = True
            print(f'[{key}] FAILED: {exc}', file=sys.stderr)
            print(f'[{key}] existing data (if any) was left untouched.', file=sys.stderr)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    (args.data_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if failed:
        print('\nIf the network blocks GitHub, copy the repositories manually into '
              f'{args.data_dir}/docs, {args.data_dir}/natives and {args.data_dir}/natives-cfx, '
              'or verify APIs on https://docs.fivem.net/natives/. Until then native lookups are UNVERIFIED.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
