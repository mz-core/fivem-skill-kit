-- Client: opens the UI, forwards intent to the server, shows the server's result.
local uiOpen = false

local function setUi(state)
    uiOpen = state
    SetNuiFocus(state, state)
    SendNUIMessage({ action = state and 'open' or 'close', payload = { defaultPoint = SharedConfig.DefaultPoint } })
end

RegisterCommand(SharedConfig.Command, function()
    setUi(not uiOpen)
end, false)

-- Every callback answers on every path (an unanswered callback stalls the request).
RegisterNUICallback('close', function(_, cb)
    setUi(false)
    cb({ ok = true })
end)

RegisterNUICallback('submit', function(data, cb)
    if type(data) ~= 'table' or type(data.pointId) ~= 'string' then
        cb({ ok = false, code = 'bad_payload' })
        return
    end
    TriggerServerEvent('{{RESOURCE_NAME}}:server:request', data.pointId)
    cb({ ok = true }) -- acknowledged; the real result arrives as a client event
end)

RegisterNetEvent('{{RESOURCE_NAME}}:client:result', function(result)
    if type(result) ~= 'table' then return end
    SendNUIMessage({ action = 'result', payload = { ok = result.ok == true, code = tostring(result.code or 'unknown') } })
end)

AddEventHandler('onResourceStop', function(resourceName)
    if resourceName == GetCurrentResourceName() then
        SetNuiFocus(false, false)
    end
end)
