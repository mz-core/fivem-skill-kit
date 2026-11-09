# Database access

> Read when: any database/SQL access or persistence.

FiveM has no built-in SQL API: servers use a MySQL/MariaDB bridge resource (most commonly **oxmysql**, but others exist). Syntax differs per library and version.

## Find out what the project uses

1. `python scripts/detect_env.py <project>` reports DB-library hints (`oxmysql`, `mysql-async`, `ghmattimysql`, ...).
2. Read the installed library's README/`fxmanifest.lua`/lib file. **Do not write DB calls from memory** if the project uses anything other than what you can see in its existing code.
3. Copy the call style already used in neighbouring resources.

## Non-negotiable rules (any library)

- **Parameterised queries only.** Values go in the parameter list, never concatenated or `string.format`-ed into the SQL text.

```lua
-- WRONG: SQL injection and breaks on quotes
MySQL.query.await("SELECT * FROM users WHERE name = '" .. name .. "'")

-- RIGHT (oxmysql-style placeholders; verify the installed version's syntax)
MySQL.query.await('SELECT * FROM users WHERE identifier = ?', { identifier })
```

- Table and column names cannot be parameters. If a name must vary, pick it from a hard-coded whitelist, never from client input.
- Validate type and range of every value first (`03-events-and-security.md`).
- The client never sends identifiers used as SQL keys without the server re-deriving them (use the server's own record of the player).
- Credentials live in `server.cfg`/convars (oxmysql reads `mysql_connection_string`), never in client/shared files.

## Async and races

- Awaited calls yield the thread. Capture `src` before them and **re-validate the player/session after** the call (they may have dropped).
- For "check then write" (balance, stock, one-time reward), use a single atomic statement (`UPDATE ... SET balance = balance - ? WHERE id = ? AND balance >= ?` and check affected rows) or a transaction. Do not read, compute in Lua, then write back.
- Guard with an in-flight flag per player/resource for long operations (see `03`).

## Reliability

- Fail closed: if the DB call errors or returns nil, deny the action and show a safe message; never log credentials or full SQL with player data.
- Add timeouts/retries only with a bound; no infinite retry loops.
- Create/alter tables via an explicit, idempotent migration file (`CREATE TABLE IF NOT EXISTS`) that the user runs deliberately; do not alter a live schema silently from script start.
- Batch writes; do not query per frame or per tick.

## Persistence design tips

- Store the stable identifier the framework/project already uses (license, citizenid, ...); never the temporary server id.
- Keep one owner per table (one resource writes it); others call its export.
