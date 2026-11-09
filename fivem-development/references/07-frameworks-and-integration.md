# Frameworks and integration (neutral)

> Read when: integrating with a framework or library (ESX/QBCore/Qbox/ox_* or a custom core), or being asked to be 'compatible with' one.

The skill never assumes a framework. Servers run ESX, QBCore, Qbox, Ox Core, a heavily modified fork, a fully **custom** framework, or none.

## Detection protocol

1. Run `python scripts/detect_env.py <project>`: it lists resource names, `ensure` lines, manifest dependencies and code patterns.
2. Common resource names (hints, not proof):

| Resource name seen | Likely |
|---|---|
| `es_extended` | ESX |
| `qb-core` | QBCore |
| `qbx_core` | Qbox |
| `ox_core` | Ox Core |
| `ox_lib`, `oxmysql`, `ox_inventory`, `ox_target` | popular libraries (independent of the framework) |
| anything else other resources `dependency` on | **custom/unknown: treat it as a black box and read its code** |

3. A fork or rename of a known framework behaves like an unknown one until you read its exports.

## Rules

- **Never write framework calls from memory.** Export names, argument order and return shapes change between versions and forks. Open the installed resource (`fxmanifest.lua`, `server/`/`shared/` files, README) or grep existing usage in neighbouring resources, then copy that.
- Use `lookup.py docs` only for Cfx platform facts; framework APIs are not in the Cfx docs.
- Do not mix frameworks in one resource and do not add a framework "bridge" the project does not use.
- Respect canonical services: if the project has an inventory/economy/permissions resource, call its API for those domains. Do not create a parallel ledger, inventory table or job system.
- If a required export does not exist in the installed version, say so and propose the smallest adapter. Do not fabricate it.

## Standalone-first design with a thin adapter

Write the resource's rules (validation, cooldowns, distance, state machine) with no framework call. Isolate every framework touch point in one file, e.g. `server/bridge.lua`, with a tiny interface:

```lua
Bridge = {}
function Bridge.getIdentifier(src)  end   -- stable player id the project uses
function Bridge.hasPermission(src, perm) end
function Bridge.grant(src, kind, id, amount) end    -- via the project's inventory/economy
```

Implement it by reading the real framework code (see `assets/patterns/bridge-adapter.lua`). Select the implementation with `GetResourceState('<resource>') == 'started'` and fail closed if none matches. The rest of the code stays portable.

## Calling other resources safely

```lua
local function callExport(resource, fn, ...)
    if GetResourceState(resource) ~= 'started' then return false, 'resource_not_started' end
    local ok, a, b = pcall(function(...) return exports[resource][fn](exports[resource], ...) end, ...)
    if not ok then return false, 'export_error' end
    return true, a, b
end
```
(Verify the call syntax against `02-cfxlua-and-runtime.md` if your project uses a different style.)

- Declare `dependency` for resources you truly need and order `ensure` lines accordingly (`08-server-ops.md`).
- Exports are not player authorisation: pass the player identity and let the owning resource check permission.
- Optional integrations (target libraries, notification libraries, UI libraries): detect with `GetResourceState`, fall back to plain natives/`SendNUIMessage`/`print` when absent.

## Permissions

Prefer the Cfx-native mechanism for admin gates (`IsPlayerAceAllowed` + `add_ace`/`add_principal`) unless the project routes permissions through its framework. Match the project, check on the server, check on every call.
