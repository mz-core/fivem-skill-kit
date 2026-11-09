-- The client only expresses intent and shows the result. The server decides.
RegisterCommand(SharedConfig.Command, function(_, args)
    local pointId = args[1] or SharedConfig.DefaultPoint
    TriggerServerEvent('{{RESOURCE_NAME}}:server:request', pointId)
end, false)

RegisterNetEvent('{{RESOURCE_NAME}}:client:result', function(result)
    if type(result) ~= 'table' then return end
    if result.ok then
        print('[{{RESOURCE_NAME}}] allowed by the server')
    else
        print(('[{{RESOURCE_NAME}}] denied: %s'):format(tostring(result.code or 'unknown')))
    end
end)
