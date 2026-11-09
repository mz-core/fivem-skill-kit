local rows = MySQL.query.await(
    "SELECT * FROM users " ..
    "WHERE name = '" .. name .. "'"
)
local q = ("DELETE FROM items WHERE owner = '%s'"):format(owner)
MySQL.update.await(q)
