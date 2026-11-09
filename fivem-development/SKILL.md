---
name: fivem-development
description: Create, fix and audit FiveM and RedM resources (Lua/CfxLua, also JS/C#) - fxmanifest, client/server events, natives, NUI, OneSync, state bags, ACE permissions, database access, performance and server-side security. Framework-neutral - works standalone or with ESX, QBCore, Qbox, ox_* or a custom framework. Use for any FiveM/RedM scripting task - "criar script FiveM", "resource", "fxmanifest", "native", "NUI", "evento", "anticheat", "revisar/auditar script", "bug no server".
compatibility: Reference files work offline. Helper scripts need Python 3.8+ (standard library only); refreshing docs/natives needs git or internet access.
metadata:
  version: "3.1.0"
  facts-verified: "2026-11-07"
  scope: framework-neutral
---

# FiveM development

Reply in the user's language. Code, identifiers and event names stay in English.

## Minimum path (always)

1. **Detect.** `python scripts/detect_env.py <dir>` (or read `fxmanifest.lua` and `server.cfg`). Never assume a framework; unknown/custom dependencies mean "read their code".
2. **Read only what the task needs** (table below), usually one or two references.
3. **Verify** every native, export or event that is not already used in the project: `python scripts/lookup.py native <Name>`.
   - `FOUND`: confirmed (it shows API set client/server/shared and the source; several definitions may exist).
   - `NOT FOUND`: absent from the synced official sources. **Not proof** it does not exist; do not use it until confirmed on https://docs.fivem.net/natives/.
   - `UNVERIFIED`: no data, a source missing, or only mentioned in text. Run `python scripts/sync_docs.py` (needs git/internet); if impossible, tell the user it is unverified.
4. **Write** from `assets/patterns/` or `assets/templates/` (`scripts/scaffold_resource.py`). The server decides; the client only asks.
5. **Check.** `python scripts/audit_lua.py <dir>` gives review hints (`fact` vs `heuristic`; never proof). If the task touches money, items, permissions or exploits, also use `references/10-audit-checklist.md`.
6. **Report:** what was verified and how, what was tested (static review only unless you ran a FXServer), what remains unverified, and the doc links used.

No shell? Same steps by reading; treat every native as unverified unless it is copied from the project.

## Which reference

| If the task mentions... | Read |
|---|---|
| new resource, fxmanifest, folders, dependency, ui_page, "criar resource" | `references/01-manifest-and-structure.md` |
| Lua syntax, exports, threads, promise, json, hash with backticks | `references/02-cfxlua-and-runtime.md` |
| event, `source`, shop/loja, price/preço, reward, money, item, job, command, permission/ACE, cooldown, exploit | `references/03-events-and-security.md` |
| NUI, UI, HTML, React, callback, SetNuiFocus, cursor | `references/04-nui.md` |
| entity, vehicle, ped, net ID, OneSync, state bag, routing bucket/instance | `references/05-onesync-entities-statebags.md` |
| database, SQL, MySQL, query, save/persist | `references/06-database.md` |
| framework, ESX/QBCore/Qbox/ox, custom core, "compatible with" | `references/07-frameworks-and-integration.md` |
| server.cfg, ensure, convar, ACE setup, txAdmin, resmon, profiler | `references/08-server-ops.md` |
| lag, fps, ms, CPU, loop, optimise | `references/09-performance.md` |
| review, audit, "is it safe", before release | `references/10-audit-checklist.md` |
| script error, nil value, "should work but doesn't", wrong side | `references/11-common-mistakes.md` |
| source or date of a fact, updating the skill | `references/99-sources-and-freshness.md` |

Each reference starts with a "Read when" line. Unsure which one? `grep -il "<keyword>" references/*.md`.

## Defaults (recommendations unless marked as documented)

- **Authority:** event arguments, NUI data and client-written state are requests, not proof. Prices, rewards, amounts, ownership and positions come from server data (`references/03-events-and-security.md`).
- `local src = source` first in a server handler, before any `Wait`/await.
- Validate type, range and catalog ID, then permission, then server-side distance, then cooldown/replay, then commit once (re-check after async steps).
- Documented platform behaviour: `lua54 'yes'` is deprecated; every NUI callback must answer; `RegisterNetEvent` is needed for network events. Everything else here is good practice: say "recommended", not "required".
- Database values go through placeholders; names that cannot be parameters come from a whitelist (`references/06-database.md`).
- No secrets or authority logic in `client/`, `shared/` or `web/`.
- Clean up on `playerDropped` and `onResourceStop`.
- Do not write exploit tooling or anything aimed at servers the user does not own.

## Freshness

Facts in `references/` are dated in `references/99-sources-and-freshness.md` (verified / partial / unverified). When a reference, the project and the live docs disagree, trust the live docs and the installed code, and say which reference is out of date.
