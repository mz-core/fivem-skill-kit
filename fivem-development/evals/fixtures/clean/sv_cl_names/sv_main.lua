RegisterNetEvent('ping:server', function(n)
    local src = source
    if type(n) ~= 'number' then return end
    TriggerClientEvent('ping:client', src, n + 1)
end)
