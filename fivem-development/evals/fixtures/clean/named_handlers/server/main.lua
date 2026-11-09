local Handlers = {}
local lastUse = {}

function Handlers.claim(rewardId)
    local src = source
    local id = math.tointeger(tonumber(rewardId))
    if not id or id < 1 or id > 10 then return end
    lastUse[src] = os.time()
    Grant(src, id)
end

local function onPaid(amount) print(('local bookkeeping %s'):format(tostring(amount))) end

RegisterNetEvent('rewards:claim', Handlers.claim)
AddEventHandler('rewards:paid', onPaid)          -- local event: payload is server-made
AddEventHandler('playerDropped', function() lastUse[source] = nil end)
