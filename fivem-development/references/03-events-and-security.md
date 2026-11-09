# Events and server-side security

> Read when: any client->server request: events, `source`, shops/prices/rewards/items/money, commands, permissions (ACE), cooldowns, exploit review.

Official: https://docs.fivem.net/docs/developers/server-security/ (verified 2026-11-07)

## What the official guide says

- Use `AddEventHandler` for events that stay on one side (not reachable from the other side). Use `RegisterNetEvent` only when the event must cross client<->server.
- Net events a client registers that should only come from the server can be guarded by checking `source ~= 65535` (the server's id as seen by clients). That check can be bypassed by a modified client: it protects logic, not security.
- On the server, validate every networked event: money, state bags, inventory, position, level/XP, permissions/roles. **Read these values with server-side functions**; never from event arguments.
- Never add items or money straight from client input.
- Its job example (server-side `activeJobs[source]`, range check, capped counter, clear on turn-in and `playerDropped`) shows the right *shape*, but the page itself notes the sample has bugs (`GetPlayerPed(source)` inside a loop, undefined `ped`). Copy the structure, not the code.

## Trust boundaries

| Input | Treat as | Do |
|---|---|---|
| Event arguments, NUI data, client commands | untrusted request | validate everything |
| `source` in a server net-event handler | identity of the connection that fired it | capture immediately; still authorise |
| Client-reported coordinates / entity / net ID | claim | recompute from server data (`GetEntityCoords(GetPlayerPed(src))`) |
| State bag written by a client | observable claim | never the only proof of anything |
| Server-side table / database row | authority (if the server wrote it) | read it, don't ask the client |
| Another resource's export | local API, not player authorisation | pass identity, verify permission in the owner |

## The request pattern

```text
client/NUI  --request(intent, catalogId)-->  server handler
                                              1. src = source
                                              2. shape check (types, lengths)
                                              3. whitelist the ID against a server catalog
                                              4. rate limit + in-flight lock
                                              5. permission (ACE / framework check)
                                              6. server-side state (distance, ownership, balance, stock)
                                              7. commit once (idempotent), then reply
client/NUI  <--result(ok, code)--  server
```

Skeleton (also in `assets/patterns/validated-server-event.lua` and the template):

```lua
RegisterNetEvent('res:server:buy', function(productId)
    local src = source                                   -- before any Wait/await
    if type(productId) ~= 'string' or #productId > 32 then return end
    local product = ServerCatalog[productId]             -- price/stock live on the server
    if not product then return end
    -- rate limit, permission, distance from server coords, funds, stock ...
    -- one commit through the owning service; re-check state after any async call
end)
```

## Validation helpers (copy as needed)

```lua
local function isInt(n, min, max)
    return type(n) == 'number' and n == n and n % 1 == 0 and n >= min and n <= max
end
local function isStr(s, maxLen) return type(s) == 'string' and #s > 0 and #s <= maxLen end
```
Reject `nil`, NaN, infinity, negative values, huge tables and unexpected keys. Never pass client strings to `load`, `ExecuteCommand`, file paths or SQL concatenation.

## Rate limiting, replay and races

- Cooldown per `src` for every sensitive event; apply it **before** the permission check so unauthorised spam is throttled too.
- Use an in-flight flag per player for operations that yield; clear it with `pcall` so an error cannot leave it stuck.
- Two parallel requests can both pass a balance/stock check before either commits. Use one atomic operation (single SQL statement/transaction, or the framework's atomic API) instead of check-then-write.
- One reward per completed server-tracked step: store the active step in a server table, consume it on completion, clear on `playerDropped`.

## Randomised "event tokens" and obfuscation

A token the client must send back is **not** authorisation: a modified client can read and replay it. Tokens can add cost for attackers, but the checks above must hold without them.

## Admin and privileged actions

- Gate with ACE (`IsPlayerAceAllowed(src, 'myres.admin')`) or the framework's permission API, checked on the server for each call.
- Validate the target (player id exists, is not the caller unless intended) and log who did what.
- `RegisterCommand(name, fn, true)` restricts the command to principals allowed `command.<name>` (documented behaviour). For sensitive operations, defence in depth is a recommendation, not a platform requirement: validate arguments and target, and optionally check an explicit permission object (`IsPlayerAceAllowed(src, 'myres.admin')`) inside the handler. One unresolved forum report claims the command ACE may be granted to everyone on some setups, so test the command with an unprivileged account on your own server.

## Server-owner convars mentioned by the guide (FXServer 8450+)

`sv_kick_players_cnl_timeout_sec`, `sv_kick_players_cnl_update_rate_sec`, `sv_kick_players_cnl_consecutive_failures`, `sv_pure_verify_client_settings`, `sv_authMaxVariance`, `sv_authMinTrust`, `sv_filterRequestControl`, `sv_disableClientReplays`. Change only if the owner understands them; a kick from these is not a global ban. `sv_scriptHookAllowed true` is documented as not recommended (makes the server vulnerable).

## Anticheat

Anticheat resources are extra telemetry; they never replace server-side validation inside each resource.
