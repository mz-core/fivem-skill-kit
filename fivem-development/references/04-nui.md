# NUI (CEF browser UI)

> Read when: building or fixing an NUI/HTML/React UI: callbacks, focus, messages, strict mode.

Official: https://docs.fivem.net/docs/scripting-manual/nui-development/nui-callbacks/ and `.../full-screen-nui/`

## Data path

```text
HTML/JS/React  --POST https://<resource>/<callback>-->  RegisterNUICallback (client Lua)
                                                         --> TriggerServerEvent (if authority needed)
server validates --> client event --> SendNUIMessage --> UI renders
```

## Verified facts (2026-11-07)

- The callback **must always answer**: "return the callback at all times - even if containing just an empty object, or `{"ok":true}`". Otherwise the request stalls.
- **Strict mode** is set with `nui_callback_strict_mode` in the manifest. Default depends on platform: **FiveM Enhanced: enabled by default** (opt out with `'false'`); **FiveM Legacy: disabled by default** (opt in with `'true'`).
- Strict mode blocks other resources from calling your NUI callbacks. A consumer that used to POST to `https://other_resource/cb` must instead expose the logic through an **export** in the provider and register its own proxy callback. (Events also work but are broadcast, so other resources can hear them.)
- The page file must be declared: `ui_page 'web/index.html'` plus `files { 'web/index.html', ... }`.

## Lua side

```lua
local open = false

local function setOpen(state)
    open = state
    SetNuiFocus(state, state)
    SendNUIMessage({ action = state and 'open' or 'close' })
end

RegisterNUICallback('close', function(_, cb)
    setOpen(false)
    cb({ ok = true })                       -- every path answers
end)

RegisterNUICallback('submit', function(data, cb)
    if type(data) ~= 'table' or type(data.pointId) ~= 'string' then
        cb({ ok = false, code = 'bad_payload' }); return
    end
    TriggerServerEvent('res:server:request', data.pointId)   -- authority lives on the server
    cb({ ok = true })                                         -- ack now; result arrives later as a message
end)

AddEventHandler('onResourceStop', function(res)
    if res == GetCurrentResourceName() then SetNuiFocus(false, false) end
end)
```

Rules:
- Open with `SetNuiFocus(true, true)`; close with `(false, false)` on close, ESC, error and resource stop.
- Slow results: ack immediately and push the result with `SendNUIMessage`, or correlate by request id with a timeout.
- Messages: `{ action = 'name', payload = {...} }`; keep payloads small and send only on change.
- NUI is untrusted: the server re-validates everything the UI "already validated".
- No secrets, tokens or privilege flags in JS.

## Frontend

- Helper: `assets/patterns/fetchNui.ts` (POST JSON, timeout, handles non-OK / empty bodies, e.g. strict-mode 403/404).
- `GetParentResourceName()` exists in the NUI JS context and gives the resource name for the URL.
- React/Vite: keep sources in `frontend/` and ship only the built `web/`; never ship `node_modules`. List real build output in `files` (usually `web/assets/**` plus `web/index.html`; confirm against the actual build).
- Remove `message` listeners on unmount.
- Local browser dev: stub `GetParentResourceName` and `fetch` so the UI can run outside the game.

## Gotchas

- Loading screens (`loadscreen`) are a different mechanism with their own limits.
- With strict mode on, "callback worked yesterday from another resource" is the usual cause of new 403/404s.
- Do not draw to NUI every frame from Lua; push on change.
