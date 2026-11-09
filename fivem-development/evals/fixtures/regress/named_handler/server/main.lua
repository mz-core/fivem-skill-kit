local function onBuy(item, qty)
    Wait(50)
    GiveItem(source, item, qty)
end
RegisterNetEvent('shop:buy', onBuy)
