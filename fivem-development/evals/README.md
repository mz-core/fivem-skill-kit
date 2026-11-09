# Evals

`evals.json` holds 14 framework-neutral prompts with `must` / `must_not` criteria: 10 technical, 2 casual Portuguese prompts (what small models will really receive) and 2 negatives with `"should_trigger": false` (the skill must stay out of non-FiveM questions). A skill is only proven useful if answers get better *with* it.

## Manual run (works with any agent)

1. Start a session **without** the skill, paste a prompt, save the answer.
2. Start a session **with** the skill installed, paste the same prompt, save the answer.
3. Grade both against `must` / `must_not` (pass/fail per line). Count passes.
4. The skill is working if the "with" run passes clearly more lines, mainly on: unknown natives, custom frameworks, server authority, stale facts.
5. If a line fails with the skill, fix the reference or SKILL.md instruction that should have prevented it, then rerun that prompt.

Test with a weaker model too: it is the model most likely to invent natives and framework calls.

## Static fixtures (run by `python scripts/selftest.py`)

`fixtures/expected_findings.json` lists what each fixture must (or must not) produce:

- `bad_resource/`: deliberately insecure; every seeded code must be reported (false-negative guard).
- `regress/*`: bugs proven in earlier versions (handler registered by name, side decided only by the manifest, multi-line / `:format` SQL).
- `clean/*`: realistic code that must stay at 0 HIGH / 0 MEDIUM (false-positive guard): helper validation, `cb` forwarded, command with ACE, `sv_`/`cl_` names, and keywords inside comments and strings.

When a real project shows a false positive or a miss, add a small fixture here first, then change the rule.

Natives lookups (FOUND / NOT FOUND / UNVERIFIED, mention-only, several definitions) are tested with fake repositories inside `selftest.py`; the real upstream layout is not contacted.

## Adding an eval

Add a prompt that failed in real use, write 3-6 concrete `must` lines, and keep it framework-neutral.
