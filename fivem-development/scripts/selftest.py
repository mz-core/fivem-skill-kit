#!/usr/bin/env python3
"""Functional self-test for the skill's scripts (offline; uses local git fixtures).

  python scripts/selftest.py

Verifies: auditor false negatives (seeded/regression fixtures) and false positives (clean fixtures),
shipped templates stay clean, scaffold and detect_env work, lookup statuses (FOUND / NOT FOUND /
UNVERIFIED, mention-only, CFX apiset, multiple definitions) and sync_docs for the three sources
(git and zip paths, failure keeps old data) against fake repos.
It cannot test Lua at runtime or the real upstream repositories' layout (GitHub is not contacted).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
S = SKILL / 'scripts'
failures: list[str] = []
passed = 0


def run(*args, env=None, cwd=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run([sys.executable, '-I', *map(str, args)], capture_output=True, text=True, env=e, cwd=cwd)


def check(name: str, cond: bool, detail: str = '') -> None:
    global passed
    if cond:
        passed += 1
        print(f'  ok   {name}')
    else:
        failures.append(name)
        print(f'  FAIL {name} {detail}')


def audit(path, *extra):
    r = run(S / 'audit_lua.py', path, '--all', '--json', *extra)
    try:
        return r, json.loads(r.stdout)
    except json.JSONDecodeError:
        return r, {'findings': [], 'summary': {}, 'notes': []}


def test_auditor(tmp: Path) -> None:
    print('auditor: fixtures (false negatives and false positives)')
    fx = SKILL / 'evals/fixtures'
    expected = json.loads((fx / 'expected_findings.json').read_text())
    for name, exp in expected.items():
        if name.startswith('_'):
            continue
        r, data = audit(fx / name)
        items = data['findings']
        codes = {i['code'] for i in items}
        for code in exp.get('must_include', []):
            check(f'{name}: reports {code}', code in codes)
        for code, basis in exp.get('must_include_basis', {}).items():
            check(f'{name}: {code} is {basis}', any(i['code'] == code and i['basis'] == basis for i in items))
        for code, n in exp.get('min_findings', {}).items():
            check(f'{name}: at least {n} x {code}', sum(i['code'] == code for i in items) >= n)
        count = lambda sev: sum(i['severity'] == sev for i in items)  # noqa: E731
        for sev in ('high', 'medium', 'low'):
            if f'max_{sev}' in exp:
                check(f'{name}: no more than {exp["max_" + sev]} {sev.upper()}', count(sev.upper()) <= exp['max_' + sev], str([(i['code'], i['line']) for i in items]))
        if 'min_high' in exp:
            check(f'{name}: exit code 1 (HIGH present)', r.returncode == 1 and count('HIGH') >= exp['min_high'])
        if name.startswith('clean/'):
            check(f'{name}: exit code 0', r.returncode == 0)

    print('auditor: output contract')
    r, data = audit(fx / 'bad_resource')
    check('json has summary/findings/notes', set(data) >= {'summary', 'findings', 'notes'})
    check('every finding has basis fact|heuristic', all(i['basis'] in ('fact', 'heuristic') for i in data['findings']))
    check('paths are relative', all(not os.path.isabs(i['file']) for i in data['findings']))
    check('side facts cite the manifest', any(i['code'] == 'secret-in-client-files' and i['basis'] == 'fact' for i in data['findings']))
    r2 = run(S / 'audit_lua.py', fx / 'bad_resource')
    check('text output has SUMMARY and LEGEND', 'SUMMARY:' in r2.stdout and 'LEGEND' in r2.stdout)
    check('ACE-restricted command is never called a vulnerability', not any(i['code'] == 'unrestricted-command' for i in audit(fx / 'clean/command_checked')[1]['findings']))
    check('restricted command gets only an optional-hardening hint', any(i['code'] == 'sensitive-command-extra-check' and i['severity'] == 'LOW' for i in audit(fx / 'clean/command_checked')[1]['findings']))

    print('auditor: wrong-side-native uses synced data only')
    nat = tmp / 'aud_data'
    (nat / 'natives-cfx').mkdir(parents=True)
    (nat / 'natives').mkdir()
    (nat / 'natives-cfx/GetPlayerPed.md').write_text('---\nns: CFX\napiset: server\n---\n## GET_PLAYER_PED\n', encoding='utf-8')
    (nat / 'natives/GET_ENTITY_COORDS.md').write_text('## GET_ENTITY_COORDS\n', encoding='utf-8')
    res = tmp / 'native_side'
    (res / 'client').mkdir(parents=True)
    (res / 'fxmanifest.lua').write_text("fx_version 'cerulean'\ngame 'gta5'\nclient_script 'client/c.lua'\n", encoding='utf-8')
    (res / 'client/c.lua').write_text("local ped = GetPlayerPed(source)\nlocal c = GetEntityCoords(ped)\n", encoding='utf-8')
    r = run(S / 'audit_lua.py', res, '--all', '--json', env={'FIVEM_SKILL_DATA': str(nat)})
    codes = [(i['code'], i['line']) for i in json.loads(r.stdout)['findings']]
    check('server-only native in a client file is reported (apiset from data)', ('wrong-side-native', 1) in codes, str(codes))
    check('native without apiset is not accused', not any(c == 'wrong-side-native' and l == 2 for c, l in codes))
    r = run(S / 'audit_lua.py', res, '--all', '--json', env={'FIVEM_SKILL_DATA': str(tmp / 'nothing')})
    check('without data there is no wrong-side-native guess', not any(i['code'] == 'wrong-side-native' for i in json.loads(r.stdout)['findings']))

    print('auditor: templates, scaffold, detect_env')
    for kind in ('basic', 'nui'):
        out = tmp / f'scaf_{kind}'
        out.mkdir()
        r = run(S / 'scaffold_resource.py', '--name', 'demo_res', '--dest', out, '--kind', kind)
        check(f'scaffold {kind} runs', r.returncode == 0, r.stderr)
        res = out / 'demo_res'
        text = '\n'.join(p.read_text() for p in res.rglob('*') if p.is_file())
        check(f'scaffold {kind} replaced placeholders', '{{' not in text)
        _, data = audit(res)
        bad = [i for i in data['findings'] if i['severity'] in ('HIGH', 'MEDIUM')]
        check(f'template {kind} has no HIGH/MEDIUM findings', not bad, str(bad))
        d = run(S / 'detect_env.py', res, '--json')
        info = json.loads(d.stdout)
        check(f'detect_env sees the {kind} resource', info['resources'] == 1 and ('demo_res' in info['nui_resources']) == (kind == 'nui'))
    r = run(S / 'scaffold_resource.py', '--name', 'Bad Name', '--dest', tmp)
    check('scaffold rejects a bad name', r.returncode != 0)
    r = run(S / 'scaffold_resource.py', '--name', 'demo_res', '--dest', tmp / 'scaf_basic')
    check('scaffold refuses to overwrite', r.returncode != 0)
    info = json.loads(run(S / 'detect_env.py', fx / 'bad_resource', '--json').stdout)
    check('detect_env flags lua54 yes and NUI without strict mode', 'bad_resource' in info['lua54_yes_deprecated'] and 'bad_resource' in info['nui_without_strict_mode'])
    check('detect_env assumes no framework', info['frameworks_detected'] == {})


def git(*a, cwd):
    subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *a], cwd=cwd, check=True, capture_output=True)


def make_repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
    git('init', '-q', cwd=root)
    git('add', '.', cwd=root)
    git('commit', '-q', '-m', 'init', cwd=root)
    return root


DOCS = {'content/docs/scripting-manual/networking/state-bags.md': '---\ntitle: State bags\n---\nState bags replicate entity state. Use flat keys.\n',
        'content/docs/scripting-manual/runtimes/lua.md': '---\ntitle: Lua\n---\nExample: local ped = GetPlayerPed(src) -- only an example in prose\nAlso mentions DO_SOMETHING_ELSE() in a snippet.\n',
        'other/ignored.md': 'not under content/docs'}
GTA = {'ENTITY/GET_ENTITY_COORDS.md': '## GET_ENTITY_COORDS\n\n```c\n// 0x3FEF770D40960D5A\nVector3 GET_ENTITY_COORDS(Entity entity, BOOL alive);\n```\nSee also DO_SOMETHING_ELSE() in the example below (prose only).\n',
       'PED/GET_PLAYER_PED.md': '## GET_PLAYER_PED\n\n```c\n// 0x43A66C31C68491C0\nPed GET_PLAYER_PED(Player player);\n```\nGTA V version (client).\n'}
CFX = {'ext/native-decls/GetPlayerPed.md': '---\nns: CFX\napiset: server\n---\n## GET_PLAYER_PED\n\n```c\nPed GET_PLAYER_PED(char* playerSrc);\n```\nServer-side ped.\n',
       'ext/native-decls/GetPlayers.md': '---\nns: CFX\napiset: server\n---\n## GET_PLAYERS\n\n```c\nchar* GET_PLAYERS();\n```\n',
       'ext/native-decls/Unrelated.md': '---\nns: CFX\napiset: shared\n---\n## UNRELATED\n',
       'code/ignored.cpp': 'int main(){}'}


def test_sync_lookup(tmp: Path) -> None:
    print('sync: three sources (fake repos, no network)')
    docs = make_repo(tmp / 'docs_repo', DOCS)
    gta = make_repo(tmp / 'gta_repo', GTA)
    cfx = make_repo(tmp / 'cfx_repo', CFX)
    data = tmp / 'data'
    env = {'FIVEM_SKILL_DATA': str(data)}

    r = run(S / 'lookup.py', 'native', 'GetPlayerPed', env=env)
    check('lookup without any data -> UNVERIFIED, exit 3', r.returncode == 3 and 'UNVERIFIED' in r.stdout and 'sync_docs' in r.stdout, r.stdout)
    r = run(S / 'lookup.py', 'docs', 'state', env=env)
    check('docs without data -> exit 3', r.returncode == 3)
    r = run(S / 'lookup.py', 'status', env=env)
    check('status without data -> exit 3', r.returncode == 3 and 'MISSING' in r.stdout)

    base = ['--data-dir', data, '--method', 'git', '--docs-url', docs.as_uri(), '--natives-url', gta.as_uri(), '--natives-cfx-url', cfx.as_uri()]
    # only GTA natives present: "not found" must degrade to UNVERIFIED
    r = run(S / 'sync_docs.py', *base, '--only', 'natives')
    check('sync natives only', r.returncode == 0, r.stdout + r.stderr)
    r = run(S / 'lookup.py', 'native', 'GetPlayerNameByServerId', env=env)
    check('missing CFX source -> UNVERIFIED (never NOT FOUND)', r.returncode == 3 and 'NOT FOUND' not in r.stdout and 'CFX' in r.stdout, r.stdout)

    r = run(S / 'sync_docs.py', *base)
    check('sync all three via git', r.returncode == 0, r.stdout + r.stderr)
    check('docs limited to content/docs', (data / 'docs/scripting-manual/networking/state-bags.md').is_file() and not (data / 'docs/other').exists())
    check('cfx limited to ext/native-decls', (data / 'natives-cfx/GetPlayerPed.md').is_file() and not (data / 'natives-cfx/code').exists())
    manifest = json.loads((data / 'manifest.json').read_text())
    check('manifest records docs, natives, natives_cfx', set(manifest) >= {'docs', 'natives', 'natives_cfx'})
    r = run(S / 'sync_docs.py', '--data-dir', data, '--check')
    check('--check ok on fresh data', r.returncode == 0, r.stdout)
    r = run(S / 'sync_docs.py', '--data-dir', data, '--check', '--max-age-days', '-1')
    check('--check flags stale data (exit 3)', r.returncode == 3)
    r = run(S / 'sync_docs.py', '--data-dir', tmp / 'empty', '--check')
    check('--check on empty folder (exit 2)', r.returncode == 2)
    check('status ok when all synced', run(S / 'lookup.py', 'status', env=env).returncode == 0)

    print('lookup: statuses')
    r = run(S / 'lookup.py', 'native', 'GetPlayers', env=env)
    check('CFX native FOUND with API set server', r.returncode == 0 and 'STATUS: FOUND' in r.stdout and 'API set: server' in r.stdout, r.stdout)
    r = run(S / 'lookup.py', 'native', 'GET_ENTITY_COORDS', env=env)
    check('GTA native FOUND (UPPER_SNAKE)', r.returncode == 0 and 'GTA V natives' in r.stdout)
    r = run(S / 'lookup.py', 'native', '0x3FEF770D40960D5A', env=env)
    check('FOUND by hash', r.returncode == 0 and 'GET_ENTITY_COORDS' in r.stdout, r.stdout)
    r = run(S / 'lookup.py', 'native', 'GetPlayerPed', env=env)
    check('same name in both sources -> two definitions listed', r.returncode == 0 and 'Definitions: 2' in r.stdout and 'several definitions' in r.stdout, r.stdout)
    check('definitions show their own API set / source', 'API set: server' in r.stdout and 'not stated in source' in r.stdout and 'CFX natives' in r.stdout)
    r = run(S / 'lookup.py', 'native', 'DoSomethingElse', env=env)
    check('name only mentioned in prose is NOT FOUND, never FOUND', r.returncode == 1 and 'STATUS: NOT FOUND' in r.stdout and 'only in text' in r.stdout, r.stdout)
    r = run(S / 'lookup.py', 'native', 'DoSomethingElse', env={'FIVEM_SKILL_DATA': str(tmp / 'data_gta_only')})
    check('mention-only with an incomplete cache -> UNVERIFIED', r.returncode == 3)
    r = run(S / 'lookup.py', 'native', 'GetPlayerNameByServerId', env=env)
    check('invented native -> NOT FOUND exit 1, "NOT proof"', r.returncode == 1 and 'NOT proof' in r.stdout and 'Do NOT use' not in r.stdout, r.stdout)
    r = run(S / 'lookup.py', 'native', 'GetPlayerPedd', env=env)
    check('typo suggests the real name', r.returncode == 1 and 'GET_PLAYER_PED' in r.stdout, r.stdout)
    r = run(S / 'lookup.py', 'docs', 'state', 'bags', env=env)
    check('docs search finds page + URL', r.returncode == 0 and 'docs.fivem.net/docs/scripting-manual/networking/state-bags/' in r.stdout, r.stdout)

    print('sync: failure and zip')
    before = (data / 'docs/scripting-manual/networking/state-bags.md').read_text()
    r = run(S / 'sync_docs.py', '--data-dir', data, '--only', 'docs', '--method', 'git', '--docs-url', (tmp / 'nope').as_uri())
    check('failed sync exits 1', r.returncode == 1)
    check('failed sync leaves old data intact', (data / 'docs/scripting-manual/networking/state-bags.md').read_text() == before)
    check('failed sync keeps manifest entry', 'docs' in json.loads((data / 'manifest.json').read_text()))

    z = tmp / 'natives.zip'
    with zipfile.ZipFile(z, 'w') as zf:
        for rel, content in GTA.items():
            zf.writestr(f'natives-master/{rel}', content)
        zf.writestr('natives-master/ENTITY/DOES_ENTITY_EXIST.md', '## DOES_ENTITY_EXIST\n')
    data2 = tmp / 'data2'
    r = run(S / 'sync_docs.py', '--data-dir', data2, '--only', 'natives', '--method', 'zip', '--natives-zip', z.as_uri())
    check('natives via zip', r.returncode == 0 and (data2 / 'natives/ENTITY/DOES_ENTITY_EXIST.md').is_file(), r.stdout + r.stderr)
    r = run(S / 'sync_docs.py', '--data-dir', data2, '--only', 'natives_cfx', '--method', 'zip', '--natives-cfx-url', 'https://example.invalid/x')
    check('natives_cfx refuses the whole-repo zip', r.returncode == 1 and 'needs git' in r.stderr, r.stderr)
    zc = tmp / 'cfx.zip'
    with zipfile.ZipFile(zc, 'w') as zf:
        zf.writestr('fivem-master/ext/native-decls/GetPlayers.md', CFX['ext/native-decls/GetPlayers.md'])
    r = run(S / 'sync_docs.py', '--data-dir', data2, '--only', 'natives_cfx', '--method', 'zip', '--natives-cfx-zip', zc.as_uri())
    check('natives_cfx via explicit zip override', r.returncode == 0 and (data2 / 'natives-cfx/GetPlayers.md').is_file(), r.stdout + r.stderr)
    r = run(S / 'lookup.py', 'native', 'GetPlayers', env={'FIVEM_SKILL_DATA': str(data2)})
    check('lookup works on zip-synced data', r.returncode == 0 and 'API set: server' in r.stdout)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix='fivem_selftest_'))
    try:
        test_auditor(tmp)
        if shutil.which('git'):
            test_sync_lookup(tmp)
        else:
            print('git not installed: skipping sync tests')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'\n{passed} passed, {len(failures)} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
