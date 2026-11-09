# Performance

> Read when: lag, high CPU/ms, loops, network or database cost.

Measure first (`resmon true`, see `08-server-ops.md`). Do not "optimise" by reading code alone.

## Client loops

```lua
-- Adaptive wait: cheap when nothing is nearby, per-frame only when needed
CreateThread(function()
    local sleep
    while true do
        sleep = 1000
        local ped = PlayerPedId()                       -- cache once per tick
        local dist = #(GetEntityCoords(ped) - point)
        if dist < 25.0 then
            sleep = 0
            -- per-frame work here (draw marker, check key)
        end
        Wait(sleep)
    end
end)
```

- `while true do Wait(0)` needs a reason. Per-frame natives (draw, control checks) justify it; polling does not.
- Prefer events/state-bag change handlers over polling.
- Do the expensive test (pool scans, raycasts) at a low rate; do the cheap distance test first.
- Don't call the same native repeatedly for an unchanging value: cache and invalidate on change.
- `RegisterKeyMapping` + a command beats polling `IsControlJustPressed` every frame for rebindable keys (verify native name).

## Entities

- Avoid scanning all vehicles/peds each frame; use a periodic scan and cache results.
- Delete created entities and release models (`SetModelAsNoLongerNeeded`) when done.

## Network

- Send small, infrequent events; never in a frame loop.
- Large one-off payloads: `TriggerLatentClientEvent` (verify availability/args with `lookup.py`).
- State bags: flat granular keys; do not rewrite a big table on every change.
- Don't broadcast (`-1`) data only some players need.

## Server

- Don't poll a database; cache read-mostly rows with an explicit invalidation rule. Do not cache permissions or balances without invalidation.
- No per-tick loops over all players unless required; if so, 1s+ interval.
- Clean per-player tables on `playerDropped` (memory growth is a common leak).
- Log sparingly.

## NUI

- Update the UI on change, not per frame; avoid huge JSON on every message.
- Unmount listeners and timers.
