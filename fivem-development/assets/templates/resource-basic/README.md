# {{RESOURCE_NAME}}

Framework-neutral example of a server-authoritative interaction. No inventory/economy is touched; the server only answers allowed/denied.

## Install

1. Put this folder in your server's `resources/` directory, run `refresh`.
2. Requires OneSync (`set onesync on` in `server.cfg`) and, with `RequireAce = true`, a grant such as:
   `add_ace group.admin {{RESOURCE_NAME}}.use allow` (example only; grant the group you actually want).
3. Add `ensure {{RESOURCE_NAME}}` to `server.cfg`.
4. Edit `server/config.lua` with real coordinates, then stand near the point and run `/{{RESOURCE_NAME}}` in game.

## Layout

- `shared/config.lua` - non-sensitive values visible to players.
- `server/config.lua` - catalog of points, limits, permission object (never sent to clients).
- `server/main.lua` - validation, rate limit, permission, server-side distance, result.
- `client/main.lua` - command and result display.

## Integration

Search `server/main.lua` for `INTEGRATION POINT`. Read your framework's real exports first; do not guess them.

Not tested in a live FXServer by the generator: test it as described in `references/10-audit-checklist.md`.
