-- Pattern (client): load a model with a timeout, release it, clean up on stop.
-- Verify each native with scripts/lookup.py before relying on it in a new project.
local created = {} -- add every entity you create: created[#created + 1] = entity

local function loadModel(model, timeoutMs)
    local hash = type(model) == 'string' and GetHashKey(model) or model
    if not IsModelValid(hash) then return nil end
    RequestModel(hash)
    local waited = 0
    while not HasModelLoaded(hash) do
        Wait(10)
        waited = waited + 10
        if waited >= (timeoutMs or 5000) then return nil end -- never wait forever
    end
    return hash
end

-- After creating the entity from the hash:
--   SetModelAsNoLongerNeeded(hash)

AddEventHandler('onResourceStop', function(resourceName)
    if resourceName ~= GetCurrentResourceName() then return end
    for _, entity in ipairs(created) do
        if DoesEntityExist(entity) then DeleteEntity(entity) end
    end
end)
