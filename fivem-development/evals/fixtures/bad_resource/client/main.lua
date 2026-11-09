-- INTENTIONALLY BAD: test fixture.
RegisterNUICallback('save', function(data, cb)
    if not data then return end
    cb({ ok = true })
end)

RegisterNUICallback('noreply', function(data, cb)
    print(data)
end)

CreateThread(function()
    while true do
        Wait(0)
        local ped = GetPlayerPed(-1)
    end
end)

local API_KEY = 'sk_live_1234567890'
TriggerClientEvent('bad', -1)
