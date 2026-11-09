-- Teaching example: the client names a catalog point, the server decides everything else.
-- No framework is assumed. Plug your inventory/economy/permission API in at INTEGRATION POINT.

local lastAttempt = {} -- [src] = os.time() of the last request
local inFlight = {}    -- [src] = true while a request is being processed

local function reply(src, ok, code, data)
    TriggerClientEvent('{{RESOURCE_NAME}}:client:result', src, { ok = ok, code = code, data = data })
end

-- All checks and the commit live here so the pcall wrapper below can always release the lock.
local function process(src, point)
    -- Permission (server-side). Replace with the project's own check if it uses another system.
    if ServerConfig.RequireAce and not IsPlayerAceAllowed(src, ServerConfig.Ace) then
        return false, 'forbidden'
    end

    -- Position from the SERVER's view of the player (OneSync). Never use client-sent coordinates.
    local ped = GetPlayerPed(src)
    if not ped or ped == 0 or not DoesEntityExist(ped) then
        return false, 'ped_unavailable'
    end
    if #(GetEntityCoords(ped) - point.coords) > point.radius then
        return false, 'out_of_range'
    end

    -- INTEGRATION POINT: grant/charge/record through the project's own service here.
    -- If you yield (database, export with callback), re-check that `src` is still connected
    -- (GetPlayerName(src) ~= nil) and that the preconditions above still hold before committing.
    -- Use one atomic operation for "check then change" (see references/06-database.md).

    return true, 'allowed'
end

RegisterNetEvent('{{RESOURCE_NAME}}:server:request', function(pointId)
    local src = source -- first line, before anything that can yield
    if type(src) ~= 'number' or src <= 0 then return end

    -- 1. Shape of the payload
    if type(pointId) ~= 'string' or #pointId > 32 then
        reply(src, false, 'bad_payload')
        return
    end

    -- 2. Whitelist against the server catalog (client cannot invent points)
    local point = ServerConfig.Points[pointId]
    if not point then
        reply(src, false, 'unknown_point')
        return
    end

    -- 3. Rate limit and in-flight lock (before the permission check, so spam is throttled too)
    local now = os.time()
    if inFlight[src] or (lastAttempt[src] and now - lastAttempt[src] < ServerConfig.CooldownSeconds) then
        reply(src, false, 'cooldown')
        return
    end
    lastAttempt[src] = now
    inFlight[src] = true

    local called, ok, code = pcall(process, src, point)
    inFlight[src] = nil -- always released, even if process() raised an error
    if not called then
        print(('[{{RESOURCE_NAME}}] error while processing request from %s: %s'):format(src, tostring(ok)))
        reply(src, false, 'server_error')
        return
    end
    reply(src, ok, code)
end)

-- Per-player state must not outlive the player
AddEventHandler('playerDropped', function()
    local src = source
    lastAttempt[src] = nil
    inFlight[src] = nil
end)
