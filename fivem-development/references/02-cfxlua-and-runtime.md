# CfxLua and runtime basics

> Read when: writing Lua for FiveM: CfxLua features, exports, threads/Wait, promises, json, which functions exist on which side.

Official: https://docs.fivem.net/docs/scripting-manual/runtimes/lua/

CfxLua is a modified **Lua 5.4**. Verified features (docs, 2026-11-07):

```lua
-- Compile-time Jenkins hash with backticks
RequestModel(`adder`)
if GetEntityModel(veh) == `buzzard` then end

-- Vectors / quaternions are first-class types (not tables)
local a = vector3(0.0, 0.0, 0.0)
local b = vector3(3.0, 4.0, 0.0)
local dist = #(a - b)            -- length of the difference vector = 5.0

-- Exports
exports('SayHello', function(name) print('Hello ' .. tostring(name)) end)   -- define
exports.otherresource:SayHello('x')                                          -- call (also exports['other-resource']:SayHello)
```

Globals available without `require`: `json` (dkjson), `msgpack`, `promise`.

```lua
print(json.encode({ a = 1 }))                    -- never print(table): it prints an address
local p = promise.new()
SetTimeout(500, function() p:resolve('done') end)
local value = Citizen.Await(p)                   -- yields the current thread
```

## Not documented here - verify before using

Compound assignment (`+=`), safe navigation (`?.`) and other CfxLua syntax sugar are **not** confirmed by the page above. Prefer plain Lua 5.4 unless the project already uses them.

## Threads, timing, events

```lua
CreateThread(function()
    while true do
        Wait(1000)          -- Wait(0) = every frame; avoid unless a per-frame native requires it
    end
end)

SetTimeout(5000, function() end)               -- run once later
AddEventHandler('onResourceStart', function(res) if res ~= GetCurrentResourceName() then return end end)
AddEventHandler('onResourceStop',  function(res) if res ~= GetCurrentResourceName() then return end end)
```

Common lifecycle events: `onResourceStart`, `onResourceStop`, `onClientResourceStart`, `playerConnecting` (server, deferrals), `playerJoining`, `playerDropped` (server, reason arg). Verify names/arguments with `lookup.py docs` before relying on rarer ones.

## Sandbox

Do not rely on `io`, `os.execute` or `require` of arbitrary files; most OS/IO facilities are restricted. `os.time()`, `os.date()`, `os.clock()` are the safe ones. Use `LoadResourceFile(resource, path)` to read files from a resource.

## Resource state and cross-resource calls

```lua
if GetResourceState('other_resource') == 'started' then
    local ok, result = pcall(function() return exports.other_resource:SomeExport(1) end)
end
```
Calling an export of a missing/stopped resource raises an error; guard sensitive paths and fail closed.

## Client vs server natives

Many natives exist only on one side (or behave differently). `lookup.py native NAME` shows the API set when the local natives data records it. When it does not, check https://docs.fivem.net/natives/ before using a native in a file of the other side.

## Runtime functions: shared vs side-specific
From the official Lua *client-functions* and *server-functions* pages (checked 2026-11-07; the lists can be incomplete - e.g. vector types appear only on the client page although the Lua runtime page presents them as language features):
- Listed on **both** pages (shared scheduler/runtime): `AddEventHandler`, `RegisterNetEvent`, `RemoveEventHandler`, `TriggerEvent`, `Citizen.Await`, `Citizen.Wait`, `Citizen.CreateThread`, `Citizen.SetTimeout`, `Citizen.Trace`.
- Only on the **server** page: `TriggerClientEvent`, `GetPlayers`, `GetPlayerIdentifiers`, `PerformHttpRequest`, `PerformHttpRequestAwait`.
- Only on the **client** page: `TriggerServerEvent`, `RegisterNUICallback`, `SendNUIMessage`.
For any native, use `scripts/lookup.py native` (API set client/server/shared) instead of guessing.

## Other runtimes

JavaScript (`client_script 'client.js'`) and C# (`client_script 'Client.net.dll'`) exist. Follow the project's runtime; do not port languages unasked.
