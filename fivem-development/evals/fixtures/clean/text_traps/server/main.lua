-- TriggerServerEvent('x') in a comment; Wait(100) then source; MySQL.query("SELECT " .. x)
--[[ GetPlayerPed(-1) and load(code) inside a block comment ]]
local note = "select an item from the list " .. tostring(os.time())
print('Update ' .. 'finished ' .. tostring(1))
local help = [[ use ExecuteCommand(cmd) .. load(x) only on the console ]]
RegisterNetEvent('text:ok', function(kind)
    local src = source
    if type(kind) ~= 'string' then return end
    print(src, kind, note, help)
end)
AddEventHandler('playerDropped', function() end)
