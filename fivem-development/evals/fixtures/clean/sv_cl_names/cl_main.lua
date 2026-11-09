RegisterNetEvent('ping:client', function(n) print(n) end)
RegisterCommand('ping', function() TriggerServerEvent('ping:server', 1) end, false)
