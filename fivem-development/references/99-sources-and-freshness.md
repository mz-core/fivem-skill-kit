# Sources and freshness

> Read when: you need the source or freshness of a fact, or are updating this skill.

Last full check: **2026-11-07**. **verified** = read on the official page that day. **partial** = official page confirms part of it. **unverified** = general knowledge or third-party only; check before relying on it, and say so to the user.

| Fact | Used in | Status | Source |
|---|---|---|---|
| `lua54 'yes'` deprecated; Lua 5.3 removed June 2025, Lua runs on 5.4 | 01, 02 | verified | https://docs.fivem.net/docs/scripting-reference/resource-manifest/ |
| `cerulean` current; `adamant` mandatory for RedM | 01 | verified | https://docs-backend.fivem.net/docs/scripting-reference/resource-manifest/resource-manifest |
| `dependency` runtime strings `'/onesync'`, `'/server:4500'`, `'/gameBuild:h4'`, `'/native:0x...'` | 01, templates | verified | same manifest page |
| NUI strict mode defaults (Enhanced on, Legacy off); callback must always answer; cross-resource calls blocked | 04 | verified | https://docs.fivem.net/docs/scripting-manual/nui-development/nui-callbacks/ |
| `AddEventHandler` vs `RegisterNetEvent`; `source ~= 65535` guard; validate server-side; official job sample has bugs; security convars | 03 | verified | https://docs.fivem.net/docs/developers/server-security/ |
| State bag API, replication/write rules, nested writes, `sv_stateBagStrictMode` | 05 | verified | https://docs.fivem.net/docs/scripting-manual/networking/state-bags |
| `AddStateBagChangeHandler` signature and `apiset: shared` | 05 | partial (declaration read on a third-party mirror of `ext/native-decls`; confirm with `lookup.py` after sync) | https://gitea.com/HamidReza/fivem/src/branch/master/ext/native-decls/AddStateBagChangeHandler.md |
| CfxLua: backtick hashes, vectors, exports syntax; `json`, `msgpack`, `promise` libraries | 02 | verified | https://docs.fivem.net/docs/scripting-manual/runtimes/lua/ |
| `Citizen.Await/Wait/CreateThread/SetTimeout`, `AddEventHandler`, `RegisterNetEvent`, `TriggerEvent` on both client and server function pages; `TriggerClientEvent`, `GetPlayers`, `GetPlayerIdentifiers` only on the server page; `TriggerServerEvent`, `RegisterNUICallback`, `SendNUIMessage` only on the client page (lists can be incomplete) | 02, auditor | verified | https://docs-backend.fivem.net/docs/scripting-reference/runtimes/lua/client-functions , .../server-functions |
| Player IDs, net IDs (16-bit, reusable), entity handles local, `GetPlayerFromServerId` may return -1, check `NETWORK_DOES_ENTITY_EXIST_WITH_NETWORK_ID` | 05, 11 | verified | https://docs-backend.fivem.net/docs/scripting-manual/networking/ids |
| `ensure`/`refresh`/`restart`, `add_ace`/`add_principal`, `onesync` legacy mode, `sv_scriptHookAllowed` warning | 05, 08 | verified | https://docs.fivem.net/docs/server-manual/server-commands/ |
| `RegisterCommand` `restricted=true` requires ACE `command.<name>` | 03, 08, auditor | verified (documented) | https://docs.fivem.net/docs/scripting-manual/migrating-from-deprecated/creating-commands/ |
| Reports that the command ACE is granted to `builtin.everyone` regardless of the flag | 03 | unverified (single unresolved forum thread, Mar 2026) - only motivates "test with an unprivileged account" | https://forum.cfx.re/t/is-the-restricted-bool-on-registercommand-supposed-to-not-work/5167272 |
| `resmon true` (developer mode) and other client console commands | 08, 09 | verified | https://docs.fivem.net/docs/client-manual/console-commands/ |
| `profiler record/status/saveJSON/view` (F8 or server console) | 08 | verified | https://docs.fivem.net/docs/scripting-manual/debugging/using-profiler/ |
| CFX natives (with `apiset: server/client/shared`) are declared in `citizenfx/fivem` `ext/native-decls`; GTA natives in `citizenfx/natives` | sync/lookup | verified (maintainer statements) | https://github.com/citizenfx/natives/issues/946 |
| Native docs legend: client / server / shared | lookup | verified | https://docs.fivem.net/docs/scripting-manual/introduction/about-native-functions/ |
| Compound assignment (`+=`) / safe navigation (`?.`) in CfxLua | 02 | unverified: not on the Lua runtime page; avoid unless the project uses them | - |
| oxmysql `mysql_connection_string`, `?` placeholders | 06 | unverified (library docs, not Cfx) | the library's README |
| Exact layout/file names of the real `citizenfx/natives` and `ext/native-decls` folders | sync/lookup | unverified: lookup is layout-agnostic on purpose | run `sync_docs.py`, then `lookup.py status` |

## Data pipeline

`python scripts/sync_docs.py` downloads three sources into `data/` (docs, natives, natives-cfx) and writes `data/manifest.json` (date, commit). `--check` reports age (stale after 30 days). `lookup.py native` answers FOUND / NOT FOUND / UNVERIFIED; only FOUND is a confirmation, and NOT FOUND is never proof that a native does not exist.

Cfx.re publishes no official AI/llms.txt/MCP endpoint as of this check.

## How to update this skill

1. `python scripts/sync_docs.py`, then `python scripts/lookup.py docs "<topic>"` for each changed area.
2. Fix the reference, change the row status/date here (only for rows you actually re-read).
3. `python scripts/validate_skill.py` and `python scripts/selftest.py`.
4. Bump `metadata.version` in `SKILL.md`.
