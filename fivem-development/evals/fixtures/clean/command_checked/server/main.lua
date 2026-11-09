RegisterCommand('spawnveh', function(src, args)
    if src ~= 0 and not IsPlayerAceAllowed(src, 'garage.spawn') then return end
    SpawnFor(src, tostring(args[1] or ''))
end, false)
RegisterCommand('banlist', function(src) ShowBans(src) end, true)
