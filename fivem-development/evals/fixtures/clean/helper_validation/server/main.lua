-- CLEAN fixture (must produce no HIGH/MEDIUM): validation through a helper, cleanup in another file.
local Items = { water = { price = 5 }, bread = { price = 8 } }
state = state or {}

local function validatePayload(item, qty)
    return type(item) == 'string' and Items[item] ~= nil and type(qty) == 'number' and qty >= 1 and qty <= 5
end

RegisterNetEvent('shop:buy', function(item, qty)
    local src = source
    if not validatePayload(item, qty) then return end
    Wait(10)
    state[src] = os.time()
    local rows = MySQL.query.await(
        'SELECT stock FROM shop_items ' ..
        'WHERE name = ? AND stock >= ?', { item, qty })
    if rows and rows[1] then Deliver(src, item, qty) end
end)

CreateThread(function() ExecuteCommand('refresh') end)
