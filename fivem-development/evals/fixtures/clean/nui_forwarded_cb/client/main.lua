-- CLEAN fixture: cb forwarded to a helper, every other path answers.
local function finish(ok, cb) cb({ ok = ok }) end

RegisterNUICallback('save', function(data, cb)
    if type(data) ~= 'table' then finish(false, cb) return end
    finish(true, cb)
end)

RegisterNUICallback('close', function(_, cb)
    SetNuiFocus(false, false)
    cb({ ok = true })
end)

AddEventHandler('onResourceStop', function(res)
    if res == GetCurrentResourceName() then SetNuiFocus(false, false) end
end)
