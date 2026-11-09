-- Pattern: parameterised query + atomic "check and change".
-- Syntax below follows oxmysql-style placeholders. Verify the installed library's real API first
-- (references/06-database.md). Do not use this file blindly with another SQL bridge.

-- Read: values only in the parameter list
local function getOwner(plate)
    return MySQL.single.await('SELECT owner FROM vehicles WHERE plate = ?', { plate })
end

-- Atomic debit: no read-modify-write in Lua. Affected rows == 0 means "not enough funds".
local function debit(accountId, amount)
    local affected = MySQL.update.await(
        'UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?',
        { amount, accountId, amount }
    )
    return affected == 1
end

-- WRONG (never do this): string-built SQL
-- MySQL.query.await("SELECT * FROM vehicles WHERE plate = '" .. plate .. "'")
