"""Private helper shared by lookup.py and audit_lua.py (not a command-line tool).

Finds native *definitions* (not mere mentions) in the synced official sources:
  data/natives      <- https://github.com/citizenfx/natives            (GTA V natives)
  data/natives-cfx  <- https://github.com/citizenfx/fivem ext/native-decls (CFX natives, with `apiset`)

A definition = the file is named after the native, OR it has a heading equal to the name,
OR it has a C-style declaration line (`Type NAME(...)`), OR (hash search) a `// 0xHASH` line.
Everything else is only a *mention* and never confirms that a native exists.
Layout-agnostic on purpose: upstream folder structure may change.
"""
from __future__ import annotations

import re
from pathlib import Path

TEXT_EXT = {'.md', '.json', '.lua', '.txt', '.yml', '.yaml'}
MAX_BYTES = 2_000_000
SOURCE_DIRS = {
    'natives': 'GTA V natives (citizenfx/natives)',
    'natives-cfx': 'CFX natives (citizenfx/fivem, ext/native-decls)',
}


def to_snake(name: str) -> str:
    if re.fullmatch(r'[A-Z0-9_]+', name):
        return name
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', name).upper()


def stem_to_snake(stem: str) -> str:
    return to_snake(stem) if re.fullmatch(r'[A-Za-z0-9_]+', stem) else stem.upper()


def iter_files(root: Path):
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in TEXT_EXT:
            try:
                if p.stat().st_size <= MAX_BYTES:
                    yield p
            except OSError:
                continue


def read(p: Path) -> str:
    return p.read_text(encoding='utf-8', errors='replace')


def front_matter(text: str) -> dict:
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.S)
    out: dict = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(':')
            if k.strip() and v.strip():
                out[k.strip().lower()] = v.strip().strip('"\'')
    return out


def source_state(data_dir: Path) -> dict:
    """{dir_name: number of files} for each natives source that exists locally."""
    state = {}
    for d in SOURCE_DIRS:
        root = data_dir / d
        state[d] = sum(1 for _ in iter_files(root)) if root.is_dir() else 0
    return state


C_WORDS = {'const', 'unsigned', 'signed', 'struct', 'char', 'int', 'float', 'void', 'long', 'short', 'double', 'bool', 'static', 'extern'}


def _decl_line(line: str, name: str) -> bool:
    """`Type NAME(params);` - a C-style declaration, not a sentence that happens to contain NAME(...)."""
    m = re.search(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'\s*\(([^()]*)\)\s*;?\s*$', line)
    if not m:
        return False
    prefix = line[:m.start()].strip()
    if not prefix or '=' in prefix or prefix.startswith(('//', '--', '#', '*', '-')):
        return False
    if re.fullmatch(r'[A-Za-z_][\w\s\*:<>,&]*', prefix) is None:
        return False
    tokens = re.findall(r'[A-Za-z_]\w*', prefix)
    # every word must look like a type (Ped, Vector3, BOOL, char, const...), so "See also X()" is rejected
    return len(tokens) <= 4 and all(t[0].isupper() or t in C_WORDS for t in tokens) and not re.search(r'\b(Call|See|Use|Note|Example|Returns?)\b', prefix)


def _fenced_lines(lines: list[str]) -> set[int]:
    inside, out = False, set()
    for i, line in enumerate(lines):
        if line.lstrip().startswith(('```', '~~~')):
            inside = not inside
            continue
        if inside:
            out.add(i)
    return out


def find_definitions(root: Path, raw: str, is_hash: bool) -> tuple[list[dict], list[Path]]:
    """Return (definitions, mention_only_files) for a native name or 0xHASH inside `root`."""
    snake = raw if is_hash else to_snake(raw)
    word = lambda s: re.compile(r'(?<![A-Za-z0-9_])' + re.escape(s) + r'(?![A-Za-z0-9_])', re.I if is_hash else 0)  # noqa: E731
    forms = [snake] if is_hash else sorted({snake, raw})
    heading = re.compile(r'^#{1,6}\s*`?(' + '|'.join(re.escape(f) for f in forms) + r')`?\s*$', re.M) if not is_hash else None
    hash_line = re.compile(r'//\s*' + re.escape(raw) + r'\b', re.I) if is_hash else None
    defs, mentions = [], []
    for p in iter_files(root):
        text = read(p)
        lines = text.splitlines()
        line_no = None
        if not is_hash and stem_to_snake(p.stem) == snake:
            line_no = 0
            if heading and (m := heading.search(text)):
                line_no = text.count('\n', 0, m.start())
        elif heading and (m := heading.search(text)):
            line_no = text.count('\n', 0, m.start())
        elif hash_line and (m := hash_line.search(text)):
            line_no = text.count('\n', 0, m.start())
        elif not is_hash:
            allowed = _fenced_lines(lines) if p.suffix.lower() == '.md' else None   # prose in .md never defines a native
            for i, line in enumerate(lines):
                if allowed is not None and i not in allowed:
                    continue
                if any(_decl_line(line, f) for f in forms):
                    line_no = i
                    break
        if line_no is not None:
            fm = front_matter(text)
            defs.append({'path': p, 'line': line_no, 'ns': fm.get('ns'), 'apiset': fm.get('apiset'), 'lines': lines})
        elif any(word(f).search(text) for f in forms):
            mentions.append(p)
    return defs, mentions


def apiset_index(data_dir: Path, wanted_snake: set[str]) -> dict[str, set]:
    """Explicit `apiset` values for natives whose FILE NAME matches (cheap; used by the auditor).

    Returns {SNAKE_NAME: {'client'|'server'|'shared'|None, ...}}; None = definition without apiset.
    """
    out: dict[str, set] = {}
    if not wanted_snake:
        return out
    for d in SOURCE_DIRS:
        root = data_dir / d
        if not root.is_dir():
            continue
        for p in iter_files(root):
            s = stem_to_snake(p.stem)
            if s in wanted_snake:
                out.setdefault(s, set()).add(front_matter(read(p)).get('apiset'))
    return out


def known_names(root: Path) -> set[str]:
    """Native-looking names (file stems and headings) for 'did you mean' suggestions."""
    names: set[str] = set()
    head = re.compile(r'^#{1,6}\s*`?([A-Z][A-Z0-9_]+)`?\s*$', re.M)
    for p in iter_files(root):
        if re.fullmatch(r'[A-Za-z0-9_]+', p.stem):
            names.add(stem_to_snake(p.stem))
        if p.suffix.lower() == '.md':
            names.update(head.findall(read(p)))
    return names
