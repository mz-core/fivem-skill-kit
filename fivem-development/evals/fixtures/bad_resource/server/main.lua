-- INTENTIONALLY INSECURE: test fixture for scripts/audit_lua.py. Never use this code.
local cooldowns = {}

RegisterNetEvent('shop:buy', function(item, price, quantity)
    Wait(100)
    local who = source
    cooldowns[source] = true
    GiveItem(who, item, quantity)
end)

RegisterNetEvent('shop:lookup', function(name)
    local rows = MySQL.query.await("SELECT * FROM users WHERE name = '" .. name .. "'")
    return rows
end)

RegisterNetEvent('shop:eval', function(code)
    local fn = load(code)
    fn()
    ExecuteCommand('say ' .. code)
end)

RegisterCommand('givemoney', function(src, args)
    AddMoney(src, tonumber(args[1]))
end, false)

AddEventHandler('x:test', function()
    TriggerServerEvent('wrong:side')
    local ped = PlayerPedId()
end)

local WEBHOOK = 'https://discord.com/api/webhooks/123/abcdef'
