# Server operations: server.cfg, ACE, convars, txAdmin, profiling

> Read when: server.cfg, ensure order, ACE/principals, convars, txAdmin, resmon/profiler.

Official: https://docs.fivem.net/docs/server-manual/server-commands/ (verified 2026-11-07)

## Resource commands (server console / txAdmin console)

- `refresh` - rescans `resources/` and loads manifests (run after adding or renaming a resource).
- `ensure <res>` - starts the resource, or restarts it if already started.
- `restart <res>` - restarts a started resource only.
- `start <res>` / `stop <res>` - as named.

## server.cfg essentials

```cfg
set onesync on                       # state awareness mode (see 05)
setr sv_stateBagStrictMode true      # only after auditing client-side state bag writes
set mysql_connection_string "..."    # secret: keep server.cfg private (oxmysql convention)

ensure oxmysql                       # libraries/frameworks first...
ensure my_framework
ensure my_resource                   # ...then resources that depend on them
```

- Start order matters: a resource must start **after** everything it depends on.
- `set` = server-only convar, `setr` = replicated to clients (clients can read it), `sets` = server info (the page marks `sets sv_projectName` deprecated). Never `setr` a secret.
- Read convars in Lua with `GetConvar`, `GetConvarInt`.

## ACE permissions

```cfg
add_ace group.admin command allow                    # example only: broad grants are a risk
add_ace resource.my_resource command.ensure allow    # example shape
add_ace group.admin my_resource.use allow            # custom permission object
add_principal identifier.license:xxxxxxxx group.admin
add_principal group.admin group.moderator            # child (admin) inherits everything granted to parent (moderator)
```

- Syntax (docs): `add_ace <principal> <object> <allow|deny>`; `add_principal <child> <parent>` makes the child inherit from the parent.
- Check in Lua: `IsPlayerAceAllowed(src, 'my_resource.use')`.
- `RegisterCommand(name, fn, true)` restricts the command to principals allowed `command.<name>` (documented). Test it with an unprivileged account (see `03-events-and-security.md`).
- Never ship a wildcard `allow` for everyone; never grant by default from a script.

## txAdmin

txAdmin manages the server process, `server.cfg` editing, restarts and bans. Resource workflow is the same commands as above (use its live console). It does not replace validation inside resources.

## Profiling

- Client console (F8, developer mode on): `resmon true` shows CPU and memory per resource; `resmon false` closes it (client console commands page).
- Profiler (official "Using the profiler" page), from the F8 client console or the server console: `profiler record <frames>`, `profiler status`, `profiler saveJSON <file.json>`, `profiler view`.
- Always measure before and after; do not claim an optimisation from reading code.

## Safe release checklist

`fxmanifest.lua` references only files that exist; no `node_modules`, source maps, tests, `.env` or private data in the package; README lists dependencies, ACE and convars; version bumped.
