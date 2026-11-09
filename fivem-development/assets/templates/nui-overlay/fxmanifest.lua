fx_version 'cerulean'
game 'gta5'

name '{{RESOURCE_NAME}}'
description 'Server-authoritative interaction with a minimal NUI (framework-neutral)'
version '0.1.0'

-- The server reads the player ped/coords, which needs OneSync.
dependency '/onesync'

-- Other resources cannot call this resource's NUI callbacks (default on Enhanced, opt-in on Legacy).
nui_callback_strict_mode 'true'

ui_page 'web/index.html'
files {
    'web/index.html',
    'web/app.js',
}

shared_scripts { 'shared/config.lua' }
client_scripts { 'client/main.lua' }
server_scripts { 'server/config.lua', 'server/main.lua' }
