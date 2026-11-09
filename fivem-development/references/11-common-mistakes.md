# Common mistakes (and hallucinations) in FiveM code

> Read when: errors, 'should work but does not', wrong-side API use, or reviewing generated code for typical mistakes.

Check generated code against this list.

## Identity and sides

| Mistake | Correct |
|---|---|
| Using `source` in client code as "me" | On the client, `PlayerId()` is the local player index; server id is `GetPlayerServerId(PlayerId())` |
| Treating `PlayerId()` as the server id | They differ: the server ID is transient (`source` on the server); the client player index does not round-trip to the server. `GetPlayerFromServerId(id)` returns `-1` when that player is not present on your client |
| `TriggerServerEvent` in a server file / `TriggerClientEvent` in a client file | `TriggerServerEvent` is client->server only; `TriggerClientEvent(name, target, ...)` is server->client |
| `TriggerClientEvent('x', data)` (forgot target) | second argument is the player id or `-1` for everyone |
| `GetPlayerPed(-1)` | `PlayerPedId()` on the client |
| Server `GetPlayerPed(src)` without OneSync | needs OneSync; may return `0` |
| Using `source` after a `Wait`/await | capture `local src = source` first |

## Events and data

- Sending functions, entity handles or userdata through events: only msgpack-serialisable data crosses the network. Send net IDs, not handles.
- Mixed or sparse numeric-key tables arrive as maps, not arrays; keep arrays dense.
- `RegisterNetEvent` for purely local events (exposes them to the other side); `AddEventHandler` alone for a net event name that must be reachable (it will not receive network triggers).
- Assuming event handler order across resources.
- `print(table)` instead of `print(json.encode(table))`.

## Natives and entities

- Inventing natives or misspelling them: verify with `scripts/lookup.py native NAME` (it suggests near matches). Same for exports and event names of other resources.
- Using a client-only native on the server (or the reverse). Check the API set.
- `RequestModel(hash)` followed immediately by spawn without waiting for `HasModelLoaded` (add a timeout), or never calling `SetModelAsNoLongerNeeded`.
- Same for `RequestAnimDict`/`HasAnimDictLoaded`, `RequestStreamedTextureDict`, etc.
- Forgetting to delete spawned entities/blips on resource stop.
- Entity handle reuse after the entity was deleted: check `DoesEntityExist` before use.

## Lua / CfxLua

- Adding `lua54 'yes'` (deprecated).
- `Wait` missing in a loop (freezes the game thread) or `Wait(0)` everywhere (CPU).
- Comparing model hashes with strings: use `GetHashKey('name')` or backticks `` `name` ``.
- `#(a - b)` works only on vectors; with tables, compute the distance manually.
- Relying on `io`/`os.execute`/`require`.
- Global variables by accident (missing `local`) leaking state between files of a resource.
- `exports['res']:fn()` when `res` is stopped: error. Guard with `GetResourceState`.

## Manifest

- Files in `client_scripts` that do not exist (resource fails to start).
- Missing `files`/`ui_page` for NUI, or listing source files instead of the build output.
- Wrong or missing `dependency`, so start order breaks.
- Mixing legacy `__resource.lua` and `fxmanifest.lua`.

## Security (the expensive ones)

- Trusting client price/amount/target.
- No cooldown, no double-submit protection.
- SQL by concatenation.
- Admin events guarded only by a hidden event name.
- "Secret" tokens or keys stored in client files.
- A state bag written by a client used as authority.

## NUI

- A callback path that never calls `cb` (stalls requests).
- Forgetting `SetNuiFocus(false, false)` on close/stop (player stuck with a cursor).
- Cross-resource NUI callback calls that break under strict mode.
- Shipping `node_modules` or building with absolute asset paths.

## Process

- Writing framework API calls from memory instead of reading the installed resource.
- Claiming "tested" after only static reading.
- Adding dependencies, build steps or refactors nobody asked for.
