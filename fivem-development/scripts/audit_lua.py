#!/usr/bin/env python3
"""Static review aid for FiveM Lua resources. It points at places to look; it does not prove anything.

  python scripts/audit_lua.py <resource-dir-or-file> [--side auto|server|client] [--all] [--json]

Every finding is tagged:
  fact       verifiable from the files or the official docs (e.g. a file listed in the manifest does
             not exist; a server-only function used in a file the manifest lists as client)
  heuristic  a text-pattern guess that needs human review. NEVER read it as a proven vulnerability.
Severity (HIGH/MEDIUM/LOW) is review priority, not proof. Exit code 1 if any HIGH (review needed).

Known limits: regex/text analysis only. Validation checks only detect the *presence* of type()/
tonumber()/validator-looking calls, not whether they are correct or complete. Dynamic code, other
languages (JS/C#), cross-resource flows and aliased functions are not followed. A clean run is not
a security approval. Files whose side (client/server) is unknown are reported, not guessed.
Standard library only; read-only.
"""
from __future__ import annotations

import argparse
import bisect
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

DATA = Path(os.environ.get('FIVEM_SKILL_DATA', _HERE.parent / 'data'))
SEV = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
DEFAULT_CAP, PER_CODE_CAP = 15, 3

# Side-specific functions documented on the official Lua runtime pages (server-functions / client-functions).
SERVER_ONLY_DOC = {'GetPlayers', 'GetPlayerIdentifiers', 'TriggerClientEvent'}   # listed on server page only
CLIENT_ONLY_DOC = {'TriggerServerEvent'}                                          # listed on client page only

MONEYISH = re.compile(r'^(price|cost|amount|money|cash|reward|payout|salary|bank|balance|coins?)$', re.I)
ADMINISH = re.compile(r'(admin|give|setjob|setmoney|addmoney|ban|kick|revive|noclip|teleport|setgroup|wipe|spawn)', re.I)
PERM_CHECK = re.compile(r'IsPlayerAceAllowed|ermission|[Aa]dmin')
VALIDATOR_CALL = re.compile(r'\b[A-Za-z_][\w\.:]*(?:[Vv]alid|[Cc]heck|[Ss]anitiz|[Vv]erify|[Aa]ssert|[Ee]nsure)\w*\s*\(')
BASIC_CHECK = re.compile(r'\btype\s*\(|\btonumber\s*\(|\bmath\.(?:type|tointeger)\s*\(')
SENSITIVE_CALL = re.compile(r'\b(?:Give|Add|Remove|Set|Spawn|Create|Delete|Execute|Pay|Charge|Grant|Teleport|Drop)\w*\s*\(')
YIELD = re.compile(r'\b(?:Citizen\.)?Wait\s*\(|\bCitizen\.Await\s*\(|\.await\s*\(')
SECRET = re.compile(r'(password|passwd|secret|api[_-]?key|token)\s*=\s*[\'"][^\'"]{6,}[\'"]', re.I)
WEBHOOK = re.compile(r'discord(app)?\.com/api/webhooks', re.I)
SQL_UPPER = re.compile(r'^\s*(SELECT\b[\s\S]*?\bFROM\b|INSERT\s+INTO\b|UPDATE\s+\S+\s+SET\b|DELETE\s+FROM\b|REPLACE\s+INTO\b)')
SQL_LOWER = re.compile(r'^\s*(select\b[\s\S]*?\bfrom\b|insert\s+into\b|update\s+\S+\s+set\b|delete\s+from\b|replace\s+into\b)'
                       r'[\s\S]*\b(where|values|limit|order\s+by|join|set|into)\b|^\s*select\s+\*\s+from\b', re.I)


# ----------------------------------------------------------------------------- lexing
def scrub(text: str):
    """Return (no_comments, code_only, strings). Offsets are preserved in all three.
    no_comments: comments blanked. code_only: strings blanked too. strings: [(start, end, content)]."""
    nc, code, strings = [], [], []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('--', i):
            lm = re.match(r'--\[(=*)\[', text[i:])
            if lm:
                close = ']' + lm.group(1) + ']'
                j = text.find(close, i + lm.end())
                j = n if j < 0 else j + len(close)
            else:
                j = text.find('\n', i)
                j = n if j < 0 else j
            seg = re.sub(r'[^\n]', ' ', text[i:j])
            nc.append(seg); code.append(seg); i = j
        elif c in '\'"':
            j = i + 1
            while j < n and text[j] != c and text[j] != '\n':
                j += 2 if text[j] == '\\' else 1
            j = min(j + 1, n)
            nc.append(text[i:j])
            code.append(c + ' ' * max(0, j - i - 2) + (c if j - i >= 2 else ''))
            strings.append((i, j, text[i + 1:max(i + 1, j - 1)]))
            i = j
        elif c == '[' and re.match(r'\[=*\[', text[i:]):
            lm = re.match(r'\[(=*)\[', text[i:])
            close = ']' + lm.group(1) + ']'
            j = text.find(close, i + lm.end())
            j = n if j < 0 else j + len(close)
            nc.append(text[i:j]); code.append(re.sub(r'[^\n]', ' ', text[i:j]))
            strings.append((i, j, text[i + lm.end():max(i + lm.end(), j - len(close))]))
            i = j
        else:
            nc.append(c); code.append(c); i += 1
    return ''.join(nc), ''.join(code), strings


def line_of(text: str, pos: int) -> int:
    return text.count('\n', 0, pos) + 1


def block_end(code: str, pos: int) -> int:
    """Index just after the `end` closing a block opened right before `pos` (depth starts at 1)."""
    depth, pending = 1, False
    for m in re.finditer(r'\b(function|if|for|while|do|repeat|until|end)\b', code[pos:]):
        t = m.group(1)
        if t in ('function', 'if', 'repeat'):
            depth += 1
        elif t in ('for', 'while'):
            depth += 1; pending = True
        elif t == 'do':
            if pending: pending = False
            else: depth += 1
        else:
            depth -= 1
            if depth == 0:
                return pos + m.end()
    return len(code)


# ----------------------------------------------------------------------------- manifest / side
def parse_manifest_sides(manifest: Path) -> dict[Path, set]:
    text, _, _ = scrub(manifest.read_text(encoding='utf-8', errors='replace'))
    base = manifest.parent
    sides: dict[Path, set] = {}
    for kind in ('shared', 'client', 'server'):
        for m in re.finditer(r'\b' + kind + r'_scripts?\b\s*(\{[^}]*\}|[\'"][^\'"]+[\'"])', text):
            for ref in re.findall(r'[\'"]([^\'"]+)[\'"]', m.group(1)):
                if ref.startswith(('@', 'http', '!')):
                    continue
                paths = list(base.glob(ref)) if any(ch in ref for ch in '*?[') else [base / ref]
                for p in paths:
                    if p.is_file():
                        sides.setdefault(p.resolve(), set()).add(kind)
    return sides


def path_side(path: Path) -> str:
    parts = [p.lower() for p in path.parts]
    stem = path.stem.lower()
    if 'server' in parts or stem.startswith(('server', 'sv_', 'sv-')) or stem.endswith(('_server', '.server', '_sv')):
        return 'server'
    if 'client' in parts or stem.startswith(('client', 'cl_', 'cl-')) or stem.endswith(('_client', '.client', '_cl')):
        return 'client'
    if 'shared' in parts or stem.startswith('shared'):
        return 'shared'
    return 'unknown'


def manifest_root(path: Path, stop: Path) -> Path:
    for parent in [path.parent, *path.parents]:
        if (parent / 'fxmanifest.lua').exists() or (parent / '__resource.lua').exists():
            return parent
        if parent == stop:
            break
    return stop


# ----------------------------------------------------------------------------- model
class Finding(dict):
    pass


class FileInfo:
    def __init__(self, path: Path, forced_side: str, manifest_sides: dict):
        self.path = path
        self.text = path.read_text(encoding='utf-8', errors='replace')
        self.nc, self.code, self.strings = scrub(self.text)
        sides = manifest_sides.get(path.resolve())
        if forced_side != 'auto':
            self.side, self.side_src = forced_side, 'forced'
        elif sides:
            self.side = next(iter(sides)) if len(sides) == 1 else 'shared'
            self.side_src = 'manifest'
        else:
            self.side, self.side_src = path_side(path), 'path'
        if self.side == 'unknown':
            self.side_src = 'none'
        self.funcs: dict[str, list] = {}
        for rx in (r'\b(?:local\s+)?function\s+([A-Za-z_][\w\.:]*)\s*\(([^)]*)\)',
                   r'\b(?:local\s+)?([A-Za-z_][\w\.]*)\s*=\s*function\s*\(([^)]*)\)'):
            for m in re.finditer(rx, self.code):
                body_start = m.end()
                entry = (params_of(m.group(2)), body_start, block_end(self.code, body_start))
                name = m.group(1)
                self.funcs.setdefault(name, []).append(entry)
                short = re.split(r'[.:]', name)[-1]
                if short != name:
                    self.funcs.setdefault(short, []).append(entry)

    @property
    def basis_side(self) -> str:  # 'fact' only when the manifest (not a file name) decided the side
        return 'fact' if self.side_src in ('manifest', 'forced') else 'heuristic'


def params_of(raw: str) -> list[str]:
    return [p.strip() for p in raw.split(',') if p.strip()]


REG = re.compile(r'\b(RegisterNetEvent|RegisterServerEvent|AddEventHandler|RegisterNUICallback|RegisterCommand)\s*\(\s*'
                 r'([\'"])([^\'"]+)\2\s*(?:,\s*(?:(function\s*\(([^)]*)\))|([A-Za-z_][\w\.:]*)))?')


class Handler:
    def __init__(self, api, event, reg_file, reg_pos, owner, params, start, end, restricted, is_net):
        self.api, self.event, self.reg_file, self.reg_pos = api, event, reg_file, reg_pos
        self.owner, self.params, self.start, self.end = owner, params, start, end
        self.restricted, self.is_net = restricted, is_net

    @property
    def body(self) -> str:
        return self.owner.code[self.start:self.end]

    @property
    def body_nc(self) -> str:
        return self.owner.nc[self.start:self.end]

    @property
    def reg_line(self) -> int:
        return line_of(self.reg_file.nc, self.reg_pos)


def collect_handlers(files: list[FileInfo]) -> list[Handler]:
    global_funcs: dict[str, list] = {}
    for f in files:
        for name, entries in f.funcs.items():
            for e in entries:
                global_funcs.setdefault(name, []).append((f, e))
    handlers: list[Handler] = []
    for f in files:
        net_names = {m.group(3) for m in REG.finditer(f.nc) if m.group(1) in ('RegisterNetEvent', 'RegisterServerEvent')}
        for m in REG.finditer(f.nc):
            api, event = m.group(1), m.group(3)
            inline_params, ref = m.group(5), m.group(6)
            is_net = api in ('RegisterNetEvent', 'RegisterServerEvent') or event in net_names
            owner = start = end = params = None
            if m.group(4) is not None:                                  # inline function(...)
                owner, params, start = f, params_of(inline_params), m.end()
                end = block_end(f.code, start)
                tail_pos = end
            elif ref and ref not in ('nil', 'true', 'false') and f.nc[m.end():m.end() + 1] != '(':
                tail_pos = m.end()
                local = f.funcs.get(ref) or f.funcs.get(re.split(r'[.:]', ref)[-1])
                if local and len(local) == 1:
                    owner, (params, start, end) = f, local[0]
                else:
                    cands = global_funcs.get(re.split(r'[.:]', ref)[-1], [])
                    if len(cands) == 1:
                        owner, (params, start, end) = cands[0][0], cands[0][1]
            else:
                continue
            if owner is None:
                continue
            restricted = None
            if api == 'RegisterCommand':
                rm = re.match(r'\s*,\s*(true|false)\b', f.nc[tail_pos:tail_pos + 40])
                restricted = (rm.group(1) == 'true') if rm else None
            handlers.append(Handler(api, event, f, m.start(), owner, params, start, end, restricted, is_net))
    return handlers


# ----------------------------------------------------------------------------- rules
def add(out: list, file, line, sev, code, basis, msg):
    out.append(Finding(file=str(file), line=line, severity=sev, code=code, basis=basis, message=msg))


def rules_handlers(handlers: list[Handler], out: list) -> None:
    for h in handlers:
        side = h.reg_file.side
        body, body_nc = h.body, h.body_nc
        if side == 'server' and h.api in ('RegisterNetEvent', 'RegisterServerEvent', 'AddEventHandler'):
            y = YIELD.search(body)
            if y:
                s = re.search(r'\bsource\b', body[y.end():])
                if s:
                    add(out, h.owner.path, line_of(h.owner.nc, h.start + y.end() + s.start()), 'HIGH', 'source-after-yield', 'heuristic',
                        f"`source` used after a Wait/await in handler '{h.event}': it may no longer be the original caller; capture `local src = source` first")
            if h.is_net:
                real = [p for p in h.params if p not in ('_', '...') and re.search(r'\b' + re.escape(p) + r'\b', body)]
                if real and not (BASIC_CHECK.search(body) or VALIDATOR_CALL.search(body)):
                    sev = 'MEDIUM' if SENSITIVE_CALL.search(body) else 'LOW'
                    add(out, h.reg_file.path, h.reg_line, sev, 'unvalidated-payload', 'heuristic',
                        f"net event '{h.event}' uses ({', '.join(real)}) with no validation-looking check (type()/tonumber()/validator call). "
                        "Presence of such a call would not prove the validation is correct")
                money = [p for p in h.params if MONEYISH.match(p)]
                if money:
                    add(out, h.reg_file.path, h.reg_line, 'MEDIUM', 'client-controlled-value', 'heuristic',
                        f"net event '{h.event}' receives {', '.join(money)} from the client; prices/amounts/rewards should come from server data")
        if side == 'server' and h.api == 'RegisterCommand' and ADMINISH.search(h.event):
            checked = PERM_CHECK.search(h.body_nc) is not None
            if h.restricted is True:
                if not checked:
                    add(out, h.reg_file.path, h.reg_line, 'LOW', 'sensitive-command-extra-check', 'heuristic',
                        f"command '{h.event}' is restricted via ACE (documented behaviour). For sensitive operations consider also "
                        "validating arguments/target and an explicit permission check in the handler (optional hardening)")
            elif not checked:
                add(out, h.reg_file.path, h.reg_line, 'MEDIUM', 'unrestricted-command', 'heuristic',
                    f"command '{h.event}' looks privileged but the restricted flag is not true and no permission check was found in the handler")
        if h.api == 'RegisterNUICallback':
            cb = h.params[1] if len(h.params) > 1 else 'cb'
            calls = re.search(r'\b' + re.escape(cb) + r'\s*\(', body)
            forwarded = any(body[m.end():m.end() + 6].lstrip()[:1] != '(' for m in re.finditer(r'\b' + re.escape(cb) + r'\b', body))
            if not calls and not forwarded:
                add(out, h.owner.path, line_of(h.owner.nc, h.start), 'MEDIUM', 'nui-callback-no-cb', 'heuristic',
                    f"NUI callback '{h.event}' never calls {cb}(): the request will stall (the docs require an answer on every path)")
            elif calls and not forwarded:
                first = calls.start()
                for r in re.finditer(r'\breturn\b', body):
                    if r.start() < first:
                        add(out, h.owner.path, line_of(h.owner.nc, h.start + r.start()), 'MEDIUM', 'nui-return-before-cb', 'heuristic',
                            f"NUI callback '{h.event}' can return before calling {cb}()")
                        break


def sql_chains(f: FileInfo, out: list) -> None:
    strings = f.strings
    starts = [s[0] for s in strings]
    for i, (s, e, content) in enumerate(strings):
        if f.nc[:s].rstrip().endswith('..'):
            continue                                              # not the beginning of a chain
        parts, nonliteral, pos, j = [content], False, e, i
        while True:
            m = re.compile(r'\s*\.\.\s*').match(f.nc, pos)
            if not m:
                break
            nxt = m.end()
            k = bisect.bisect_left(starts, nxt)
            if k < len(strings) and strings[k][0] == nxt:         # next operand is a string literal
                parts.append(strings[k][2]); pos = strings[k][1]; j = k
                continue
            nonliteral = True
            parts.append('?')
            m2 = re.compile(r'[A-Za-z_][\w\.:]*(?:\([^()]*\))?|\d+|\([^()]*\)').match(f.nc, nxt)
            if not m2:
                break
            pos = m2.end()
        text = ' '.join(parts)
        shape = SQL_UPPER.search(text) or SQL_LOWER.search(text)
        if not shape:
            continue
        formatted = bool(re.search(r'%[sdif]', content)) and (
            re.match(r'\s*\)?\s*:\s*format\s*\(', f.nc[e:e + 24]) or re.search(r'string\.format\s*\(\s*$', f.nc[max(0, s - 20):s]))
        if nonliteral or formatted:
            add(out, f.path, line_of(f.nc, s), 'HIGH', 'sql-concat', 'heuristic',
                'SQL text is built from non-literal values (concatenation/format): use placeholders for values; whitelist names that cannot be parameters (references/06-database.md)')


def rules_file(f: FileInfo, out: list, dropped_roots: set, root_of, natives_idx: dict, local_funcs: set) -> None:
    side = f.side
    # secrets
    for i, raw in enumerate(f.nc.splitlines(), 1):
        if WEBHOOK.search(raw) or SECRET.search(raw):
            if side == 'server':
                add(out, f.path, i, 'LOW', 'hardcoded-secret', 'heuristic', 'hard-coded secret/webhook: prefer a convar read with GetConvar')
            else:
                basis = 'fact' if side in ('client', 'shared') and f.side_src in ('manifest', 'forced') else 'heuristic'
                add(out, f.path, i, 'HIGH', 'secret-in-client-files', basis,
                    'secret/webhook in a file that players can read' + ('' if basis == 'fact' else ' (side not confirmed by the manifest)'))
    sql_chains(f, out)
    for m in re.finditer(r'\b(load|loadstring)\s*\(\s*([^)\n]*)\)', f.code):
        if not re.search(r'\(\s*[\'"][^\'"]*[\'"]\s*\)', f.nc[m.start():m.end()]):
            add(out, f.path, line_of(f.nc, m.start()), 'HIGH' if side == 'server' else 'MEDIUM', 'dynamic-exec', 'heuristic',
                f"{m.group(1)}() on a non-literal value can run attacker-controlled code if the value is player-influenced")
    for m in re.finditer(r'\bExecuteCommand\s*\(([^)\n]*)\)', f.code):  # match on code (strings/comments blanked), read the argument from nc
        if not re.fullmatch(r'\s*[\'"][^\'"]*[\'"]\s*', f.nc[m.start(1):m.end(1)]):
            add(out, f.path, line_of(f.nc, m.start()), 'HIGH' if side == 'server' else 'MEDIUM', 'dynamic-exec', 'heuristic',
                'ExecuteCommand with a non-literal argument: never pass player-controlled text')
    for m in re.finditer(r'\bGetPlayerPed\s*\(\s*-1\s*\)', f.code):
        add(out, f.path, line_of(f.nc, m.start()), 'LOW', 'deprecated-ped', 'heuristic', 'GetPlayerPed(-1) is the old idiom; PlayerPedId() is the client-side form')

    if side == 'server':
        wrong = [(n, 'client-functions page') for n in CLIENT_ONLY_DOC]
        for name, where in wrong:
            m = re.search(r'\b' + name + r'\s*\(', f.code)
            if m:
                add(out, f.path, line_of(f.nc, m.start()), 'MEDIUM', 'wrong-side-api', f.basis_side,
                    f'{name}() appears only on the {where} of the official Lua reference (the lists can be incomplete); this file is a server file')
        if root_of(f.path) not in dropped_roots:  # playerDropped is looked for in the whole resource, not only this file
            for var in re.findall(r'^\s*local\s+([A-Za-z_]\w*)\s*=\s*\{\s*\}', f.code, re.M):
                mm = re.search(r'\b' + re.escape(var) + r'\[\s*(src|source|playerId|player|_source|id)\s*\]\s*=', f.code)
                if mm:
                    add(out, f.path, line_of(f.nc, mm.start()), 'MEDIUM', 'per-player-state-leak', 'heuristic',
                        f"table '{var}' is keyed by player but no playerDropped handler exists in this resource")
    if side == 'client':
        for name in SERVER_ONLY_DOC:
            m = re.search(r'\b' + name + r'\s*\(', f.code)
            if m:
                add(out, f.path, line_of(f.nc, m.start()), 'MEDIUM', 'wrong-side-api', f.basis_side,
                    f'{name}() appears only on the server-functions page of the official Lua reference (the lists can be incomplete); this file is a client file')
        for m in re.finditer(r'\bwhile\s+true\s+do\b', f.code):
            end = block_end(f.code, m.end())
            if re.search(r'\bWait\s*\(\s*0\s*\)', f.code[m.end():end]):
                add(out, f.path, line_of(f.nc, m.start()), 'LOW', 'per-frame-loop', 'heuristic',
                    'loop runs every frame (Wait(0)); use adaptive waits unless a per-frame native needs it')
    # data-driven client/server check (only when synced natives data exists and states an explicit apiset)
    if natives_idx and side in ('server', 'client'):
        for m in re.finditer(r'(?<![\w\.:])([A-Z][A-Za-z0-9]{3,})\s*\(', f.code):
            name = m.group(1)
            if name in local_funcs or name in SERVER_ONLY_DOC | CLIENT_ONLY_DOC:
                continue
            apis = natives_idx.get(nat.to_snake(name))
            if apis and len(apis) == 1:
                api = next(iter(apis))
                if (side == 'server' and api == 'client') or (side == 'client' and api == 'server'):
                    add(out, f.path, line_of(f.nc, m.start()), 'MEDIUM', 'wrong-side-native', f.basis_side,
                        f'{name}() is documented as `apiset: {api}` in the synced natives, but this is a {side} file')


def scan_manifest(path: Path, out: list) -> None:
    nc, _, _ = scrub(path.read_text(encoding='utf-8', errors='replace'))
    base = path.parent
    m = re.search(r'lua54\s+[\'"]yes', nc)
    if m:
        add(out, path, line_of(nc, m.start()), 'LOW', 'lua54-deprecated', 'fact', "lua54 'yes' is deprecated; all Lua already runs on 5.4 (official manifest docs)")
    if re.search(r'\bui_page\b', nc) and 'nui_callback_strict_mode' not in nc:
        add(out, path, 1, 'LOW', 'nui-no-strict-mode', 'fact', 'NUI resource without nui_callback_strict_mode (default differs: on in Enhanced, off in Legacy)')
    for kw in ('shared_scripts?', 'client_scripts?', 'server_scripts?', 'files?', 'ui_page'):
        for mm in re.finditer(r'\b' + kw + r'\b\s*(\{[^}]*\}|[\'"][^\'"]+[\'"])', nc):
            for ref in re.findall(r'[\'"]([^\'"]+)[\'"]', mm.group(1)):
                if ref.startswith(('@', 'http', 'nui://', '!')):
                    continue
                if any(ch in ref for ch in '*?['):
                    if not list(base.glob(ref)):
                        add(out, path, line_of(nc, mm.start()), 'MEDIUM', 'manifest-missing-file', 'fact', f'pattern matches no file: {ref}')
                elif not (base / ref).exists():
                    add(out, path, line_of(nc, mm.start()), 'MEDIUM', 'manifest-missing-file', 'fact', f'listed file does not exist: {ref}')


# ----------------------------------------------------------------------------- driver
def analyse(target: Path, forced_side: str) -> tuple[list, list, dict]:
    stop = target if target.is_dir() else target.parent
    if target.is_file():
        lua_files = [target]
        manifests = [p for parent in [target.parent, *list(target.parents)[:4]] for p in [parent / 'fxmanifest.lua'] if p.exists()][:1]
    else:
        lua_files = sorted(p for p in target.rglob('*.lua') if 'node_modules' not in p.parts and p.name not in ('fxmanifest.lua', '__resource.lua'))
        manifests = sorted(p for p in target.rglob('fxmanifest.lua') if 'node_modules' not in p.parts)
    msides: dict = {}
    for mf in manifests:
        for k, v in parse_manifest_sides(mf).items():
            msides.setdefault(k, set()).update(v)
    files = [FileInfo(p, forced_side, msides) for p in lua_files]
    out: list = []
    for mf in manifests:
        scan_manifest(mf, out)
    handlers = collect_handlers(files)
    rules_handlers(handlers, out)

    dropped_roots = {manifest_root(f.path, stop) for f in files if 'playerDropped' in f.nc}
    local_funcs = {n for f in files for n in f.funcs}
    wanted = {nat.to_snake(m.group(1)) for f in files for m in re.finditer(r'(?<![\w\.:])([A-Z][A-Za-z0-9]{3,})\s*\(', f.code)
              if m.group(1) not in local_funcs}
    idx = nat.apiset_index(DATA, wanted) if any(nat.source_state(DATA).values()) else {}
    for f in files:
        rules_file(f, out, dropped_roots, lambda p: manifest_root(p, stop), idx, local_funcs)

    notes = []
    unknown = [f for f in files if f.side == 'unknown']
    if unknown:
        notes.append(f'{len(unknown)} file(s) have an unknown side (not in the manifest, no client/server/shared in the name): '
                     'side-specific rules were skipped for them. Re-run with --side server|client to check them.')
    notes.append('natives data: ' + ('used for client/server API-set checks.' if idx else 'not available; only the documented side-specific functions were checked (run scripts/sync_docs.py).'))
    stats = {'files': len(files) + len(manifests)}
    return out, notes, stats


def compact(items: list, show_all: bool) -> tuple[list, int]:
    if show_all:
        return items, 0
    shown, per, hidden = [], {}, 0
    for it in items:
        key = (it['file'], it['code'])
        per[key] = per.get(key, 0) + 1
        if per[key] > PER_CODE_CAP or len(shown) >= DEFAULT_CAP:
            hidden += 1
        else:
            shown.append(it)
    return shown, hidden


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', type=Path)
    ap.add_argument('--side', choices=['auto', 'server', 'client'], default='auto', help='force the side of every file')
    ap.add_argument('--all', action='store_true', help='do not cap the number of printed findings')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    if not args.target.exists():
        print(f'Not found: {args.target}', file=sys.stderr)
        return 2
    target = args.target.resolve()
    items, notes, stats = analyse(target, args.side)
    base = target if target.is_dir() else target.parent
    for it in items:                       # short relative paths: saves tokens for the reader
        try:
            it['file'] = Path(it['file']).resolve().relative_to(base).as_posix()
        except ValueError:
            pass
    items.sort(key=lambda x: (SEV[x['severity']], x['basis'] != 'fact', x['file'], x['line']))
    counts = {s: sum(1 for i in items if i['severity'] == s) for s in SEV}
    facts = sum(1 for i in items if i['basis'] == 'fact')
    if args.json:
        print(json.dumps({'summary': {**counts, 'fact': facts, 'heuristic': len(items) - facts, 'files': stats['files']},
                          'findings': items, 'notes': notes}, indent=2))
    else:
        print(f"SUMMARY: {stats['files']} file(s) | HIGH={counts['HIGH']} MEDIUM={counts['MEDIUM']} LOW={counts['LOW']} | "
              f"fact={facts} heuristic={len(items) - facts}")
        shown, hidden = compact(items, args.all)
        for it in shown:
            print(f"{it['file']}:{it['line']} [{it['severity']}][{it['basis']}] {it['code']}: {it['message']}")
        if hidden:
            print(f'(+{hidden} more not shown; use --all)')
        for n in notes:
            print('NOTE:', n)
        print('LEGEND: fact = verifiable from files/official docs; heuristic = text-pattern guess to review manually, NOT a proven vulnerability.')
        print('LIMITS: validation checks only detect presence of type()/validator-looking calls. A clean run is not a security approval '
              '(see references/10-audit-checklist.md).')
    return 1 if counts['HIGH'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
