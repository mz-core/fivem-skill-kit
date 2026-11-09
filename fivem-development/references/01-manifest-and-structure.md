# Manifest and resource structure

> Read when: creating or editing fxmanifest.lua, choosing folders, dependencies, ui_page/files, game (gta5/rdr3).

Official: https://docs.fivem.net/docs/scripting-reference/resource-manifest/

## Minimal manifest

```lua
fx_version 'cerulean'
game 'gta5'

name 'my_resource'
description 'What it does'
version '0.1.0'

shared_scripts { 'shared/*.lua' }
client_scripts { 'client/*.lua' }
server_scripts { 'server/*.lua' }
```

## Verified facts (docs, checked 2026-11-07)

- `fx_version`: `cerulean` is the current FXv2 version. `bodacious` implies `clr_disable_task_scheduler`. `adamant` requires a game to be specified and is **mandatory for RedM**.
- `lua54 'yes'` is **deprecated**; since June 2025 Lua 5.3 is gone and every Lua script runs on 5.4. Do not add it.
- `dependency 'name'` requires that resource to load first. The same entry expresses runtime requirements with a leading slash (examples from the manifest docs): `dependency '/server:4500'` (minimum server build), `dependency '/onesync'` (OneSync/state awareness required), `dependency '/gameBuild:h4'`, `dependency '/native:0x...'`.
- `provide 'name'` marks the resource as a replacement for another.
- `ui_page` sets the NUI page; a local HTML file must also be listed with `file`/`files`.
- `this_is_a_map` marks a GTA map resource.
- Explicit exports: `export 'Fn'` (client) / `server_export 'Fn'` (server); functions must be global and become available after the first scheduler tick. Exports defined in code use `exports('Name', fn)`.
- `nui_callback_strict_mode 'true'|'false'` is documented on the NUI callbacks page (see `04-nui.md`).

## Layout (a convention, not a rule - follow the project's own)

```text
my_resource/
  fxmanifest.lua
  README.md
  shared/   non-secret constants/contracts (visible to players)
  client/   input, rendering, NUI bridge
  server/   authority, validation, persistence, secrets/config that matters
  web/      built NUI assets only (no node_modules, no sources)
```

- Put anything that decides outcomes (prices, points, permissions, limits) in `server/`, even if it is "not secret": it keeps cheat surface and mistakes smaller.
- Event names prefixed by the resource: `resource:server:action`, `resource:client:update`.
- Globs in script lists are fine (`'client/*.lua'`). For NUI `files`, list what the **real** build output contains; do not invent paths.
- Declare real dependencies only; do not add `dependencies` for libraries the code does not call.
- Legacy `__resource.lua` manifests exist in old resources. Upgrade to `fxmanifest.lua` when asked; do not mix.

## README of a resource should state

Install steps, dependencies and start order, ACE permissions it expects, convars, commands, events/exports it exposes, data flow.

## Game selection

```lua
game 'gta5'                    -- FiveM
games { 'gta5', 'rdr3' }       -- multi-game (natives differ per game: verify each)
fx_version 'adamant'           -- RedM requires this
```
