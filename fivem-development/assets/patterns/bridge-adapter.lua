-- Pattern: isolate every framework touch point behind one tiny interface.
-- The bodies are deliberately EMPTY: fill them by reading the installed framework's real code
-- (fxmanifest, exports, existing resources). Do not copy API names from memory.

Bridge = {}

local function started(name) return GetResourceState(name) == 'started' end

-- Stable identifier the project persists (not the temporary server id).
function Bridge.getIdentifier(src)
    -- if started('<framework resource>') then return <read its real API> end
    return nil
end

function Bridge.hasPermission(src, permission)
    -- Cfx-native fallback when the project uses ACE:
    return IsPlayerAceAllowed(src, permission)
end

-- Grant value through the project's own inventory/economy service. Return ok, code.
function Bridge.grant(src, kind, id, amount)
    -- if started('<inventory resource>') then <call its real export> end
    return false, 'no_adapter'          -- fail closed until implemented
end
