# Audit and review checklist

> Read when: reviewing/auditing a resource or deciding if it is safe to release.

Run `python scripts/audit_lua.py <dir>` first. Its findings are tagged `fact` (verifiable from files/docs) or `heuristic` (a pattern guess to review, never a proven vulnerability). Then walk this list by hand.

## Per sensitive endpoint (event, NUI callback, command, export)

Write a row per endpoint: `file:line | side | who can call | payload | where authority comes from | checks present | persistent effect | risk | fix`.

Blockers (any "no" = **NO-GO**):
- [ ] Net events exist only where needed; same-side events use `AddEventHandler`.
- [ ] `local src = source` captured before any yield.
- [ ] Types/ranges/lengths/whitelists checked; NaN/inf/negative/huge table rejected.
- [ ] Price, quantity, reward, target, owner, job come from server data, not arguments.
- [ ] Distance/ownership/state evaluated from server-side coordinates and tables.
- [ ] Permission checked on the server on every call (ACE or the project's own check).
- [ ] Cooldown/rate limit, and double-submit/replay protection for anything that grants value.
- [ ] Check-then-write is atomic or re-validated after async steps.
- [ ] SQL parameterised; no client string reaches `load`, `ExecuteCommand`, file paths.
- [ ] No secrets or authority in client/shared/web.
- [ ] State bags: nothing security-relevant relies on a client-writable bag.
- [ ] NUI: every callback answers on every path; strict mode considered; no cross-resource callback abuse.
- [ ] `playerDropped` / `onResourceStop` clean up tables, entities, focus, handles.

Integration:
- [ ] Natives, exports, events verified (`lookup.py` / docs / the installed resource).
- [ ] Manifest lists existing files and real dependencies; start order documented.
- [ ] No `node_modules`, tests, `.env` or private data in the release package.

## Manual tests (on a development FXServer)

1. Fire the event directly from the F8 console / a test client without permission.
2. With permission but far from the point.
3. Spam it and fire it in parallel (race/double reward).
4. Send nil, strings for numbers, negative, `1e309`, huge/nested tables.
5. Disconnect during an operation; reconnect.
6. `ensure` the resource while the UI is open and an operation is pending.
7. Database down / dependency stopped: action must deny safely.
8. Check console output for errors and sensitive data in logs.

## Attack scenarios to try (own dev server only)

| Area | Attempt | Expected control |
|---|---|---|
| Shop/economy | send price or amount from the client | server catalog decides; request rejected |
| Rewards/jobs | complete a step without doing it, or far away | server-tracked step + server distance |
| Items/inventory | request a non-existent or restricted item/quantity | server whitelist and limits |
| Vehicles/garage | spawn another owner's vehicle/plate | ownership read from server data |
| Admin actions | call with an arbitrary target id | ACE + valid target + audit log |
| Exports | call with a fake permission value | owner resource checks real permission |
| NUI | call a callback from another resource | strict mode + proxy export + server check |
| State bags | flip a duty/flag bag from a client | server ignores client-writable bags |
| Entities | send far/foreign net IDs | exists, type, bucket, range, owner verified |

## Verdicts

- **PASS**: demonstrated by a test you ran.
- **PENDING**: needs FXServer/CEF/database or a regression test you could not run.
- **NO-GO**: a sensitive action can be completed using only values the client controls.

Static review is not homologation. Say which it is.
