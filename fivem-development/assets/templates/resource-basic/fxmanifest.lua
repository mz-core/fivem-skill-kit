fx_version 'cerulean'
game 'gta5'

name '{{RESOURCE_NAME}}'
description 'Server-authoritative interaction example (framework-neutral)'
version '0.1.0'

-- The server reads the player ped/coords (GetPlayerPed/GetEntityCoords), which needs OneSync.
dependency '/onesync'

shared_scripts { 'shared/config.lua' }
client_scripts { 'client/main.lua' }
server_scripts { 'server/config.lua', 'server/main.lua' }
