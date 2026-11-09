-- Pattern: call another resource without crashing if it is stopped or the export is missing.
local function callExport(resource, fn, ...)
    if GetResourceState(resource) ~= 'started' then
        return false, 'resource_not_started'
    end
    local args = { ... }
    local ok, a, b = pcall(function()
        return exports[resource][fn](exports[resource], table.unpack(args))
    end)
    if not ok then return false, 'export_error' end
    return true, a, b
end

-- Usage (names are examples; read the real resource for its exports):
-- local ok, result = callExport('some_resource', 'SomeExport', 1)
-- if not ok then -- fail closed for sensitive actions end
