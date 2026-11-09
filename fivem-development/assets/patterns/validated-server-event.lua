-- Pattern: purchase-like request where price, stock and permission are decided by the server.
-- Adapt names. `chargeAndGrant` is YOUR project's atomic service call (do not invent one).

local Catalog = {                      -- server-side data; the client only sends the key
    water = { price = 5,  maxPerRequest = 5 },
    bread = { price = 8,  maxPerRequest = 5 },
}

local lastAttempt, inFlight = {}, {}

local function isInt(n, min, max)
    return type(n) == 'number' and n == n and n % 1 == 0 and n >= min and n <= max
end

RegisterNetEvent('shop:server:buy', function(productId, quantity)
    local src = source                                     -- before any yield
    if type(productId) ~= 'string' or #productId > 32 then return end
    local product = Catalog[productId]
    if not product then return end                         -- whitelist
    if not isInt(quantity, 1, product.maxPerRequest) then return end

    local now = os.time()
    if inFlight[src] or (lastAttempt[src] and now - lastAttempt[src] < 1) then return end
    lastAttempt[src] = now
    inFlight[src] = true

    local ok, err = pcall(function()
        local ped = GetPlayerPed(src)
        if ped == 0 or #(GetEntityCoords(ped) - vector3(0.0, 0.0, 0.0)) > 3.0 then return end -- replace with the real shop coords
        local total = product.price * quantity             -- computed on the server
        -- chargeAndGrant(src, total, productId, quantity) -- one atomic call; re-check the player is still connected after yields
    end)
    inFlight[src] = nil
    if not ok then print('shop:server:buy failed: ' .. tostring(err)) end
end)

AddEventHandler('playerDropped', function()
    local src = source
    lastAttempt[src], inFlight[src] = nil, nil
end)
