# OneSync, entities, state bags, routing buckets

> Read when: entities, net IDs, OneSync, state bags, routing buckets (instances).

Official: https://docs.fivem.net/docs/scripting-manual/networking/state-bags and https://docs.fivem.net/docs/scripting-reference/onesync/

## OneSync

- `onesync` convar picks the state-awareness mode; `legacy` is a compatibility mode "for scripts that expect all players to exist on each client" (docs, server commands page). Most modern code assumes OneSync is on.
- With OneSync, entities are streamed by distance: a ped/vehicle may **not exist on a given client**. Never build logic that assumes every player's ped is locally available.
- Server-side entity natives (`GetPlayerPed`, `GetEntityCoords`, `DoesEntityExist`, `DeleteEntity`, `NetworkGetEntityOwner`, `CreateVehicleServerSetter`, ...) rely on OneSync. Handle `0`/nil returns. Verify each with `lookup.py native`.
- If server code needs OneSync, declare it in the manifest (`dependency` runtime requirement - see `01-manifest-and-structure.md`) so a wrong server fails loudly.

## Entities and ownership

- Entity handles are **local to each runtime**: the same entity can have different handles on different clients, and a recreated entity may get a new one. Pass net IDs instead: `NetworkGetNetworkIdFromEntity(e)` / `NetworkGetEntityFromNetworkId(id)` (aliases like `PedToNet`, `NetToVeh` exist). A net ID is a 16-bit integer, stable during the entity's lifetime but **reusable** afterwards: check `NetworkDoesEntityExistWithNetworkId(id)` before using it, and wait with a timeout on the receiving side. On the server, net IDs are only meaningful with OneSync (state awareness) enabled.
- Ownership can migrate between clients: a net ID or "owner" is not permanent authority.
- Server-side validation of a client-supplied net ID: entity exists, expected type, expected model/whitelist, same routing bucket, within range of the **server-known** player position, not owned by something it should not be.
- Delete what you create (`onResourceStop`), and prefer server-created entities when ownership matters (verify the native for your game/artifact).

## State bags (verified 2026-11-07)

```lua
Entity(vehicle).state:set('myres:fuel', 55, true)     -- key, value, replicated
local fuel = Entity(vehicle).state['myres:fuel']
Player(src).state['myres:duty'] = true                -- server side
LocalPlayer.state:set('myres:flag', 1, true)          -- client side
GlobalState['myres:weather'] = 'rain'                 -- server writes, everyone reads
```

- Written from the **server**: replicated by default. Written from a **client**: **not** replicated unless the 3rd `set` argument says so.
- Who may write: player state - the player and the server; entity state - the owning client and the server; `GlobalState` - server only.
- `setr sv_stateBagStrictMode true` limits writes of replicated player/entity state to the server. It can break resources that write from clients; audit before enabling in production.
- Getters return the whole serialised state; **nested writes do not replicate** (`state.x.y = 1`). Use flat keys: `state['x:y'] = 1`.
- A client-writable bag is a claim, not authority. Decide permissions/ownership from server tables.
- `AddStateBagChangeHandler(keyFilter, bagFilter, handler)` reacts to changes (`keyFilter`/`bagFilter` may be `nil` for no filter; `bagFilter` looks like `entity:65535`). Handler: `function(bagName, key, value, reserved, replicated)`. It cannot reject a change and returns a cookie used to remove it. Source: native declaration `ext/native-decls` as seen on a third-party mirror (apiset shared) - confirm with `lookup.py native AddStateBagChangeHandler` after `sync_docs.py`.
- Never put secrets in replicated bags or `GlobalState`.

## Routing buckets (instances)

`SetPlayerRoutingBucket`, `GetPlayerRoutingBucket`, `SetEntityRoutingBucket`, `SetRoutingBucketPopulationEnabled` (server). Entities and players only see/interact within their bucket. When an interaction involves two players or an entity, check they share a bucket on the server. Verify native names with `lookup.py`.

## Checks that commonly belong in a server handler

`DoesEntityExist`, real entity type, server-side coords/distance, bucket, ownership/persistence record, timing after migration/respawn.
