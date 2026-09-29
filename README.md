# how-its-done

A response-format skill for [Claude Code](https://claude.com/claude-code): a standing contract for
how an agent session reports back — a register of Targets, Threads, Work done, Open questions,
Actions and Background, rendered as fixed-width terminal text and as a local, per-round HTML page,
instead of a wall of prose repeated every turn.

It grew out of one person's long-running, many-session use of Claude Code, refined round by round
against real friction (repetition, terse rows that stopped making sense a week later, a Targets
table that silently disappeared, and so on). `docs/decisions.md` keeps that history — the original
complaints and rulings behind each rule — separate from the rules themselves, which is what makes
`SKILL.md` a contract instead of a diary.

## What's in here

| Path | What it is |
| --- | --- |
| `SKILL.md` | The contract itself — read this first. |
| `check-response.py` | Validates a drafted response against the contract. Stdlib only. |
| `render-register.py` | Renders the fixed-width terminal form; owns `--check`. |
| `render-artifact.py` | Renders the HTML page form (the one actually published each round). |
| `publish-register.py` | Writes the per-round local pages and the live `current.html`. |
| `hooks/response-format-reminder.sh` | A `UserPromptSubmit` hook that points every turn at `SKILL.md`. |
| `support-thread/SKILL.md` | A companion skill for running a read-only Q&A session alongside a primary one, in plain prose instead of the full register. |
| `docs/decisions.md` | The provenance: the quotes and rulings each rule in `SKILL.md` came out of. |

Everything is Python 3, standard library only — no `pip install` required.

## Installing

1. Clone this repo somewhere durable, e.g. `~/code/how-its-done`.
2. Point `~/.claude/skills/response-format` at it — a symlink keeps the checkout as the one copy
   instead of a drifting duplicate:

   ```sh
   mkdir -p ~/.claude/skills
   ln -s ~/code/how-its-done ~/.claude/skills/response-format
   ```

3. Wire the reminder hook into Claude Code's `~/.claude/settings.json`, so the contract is delivered
   every turn instead of depending on the model remembering it across a long or compacted session:

   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         { "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/response-format-reminder.sh", "timeout": 5 }] }
       ]
     }
   }
   ```

   The hook script itself needs to be reachable at that path too — either symlink
   `hooks/response-format-reminder.sh` from this repo into `~/.claude/hooks/`, or copy it there and
   keep the two in sync by hand.

4. Optionally install `support-thread/SKILL.md` the same way, as `~/.claude/skills/support-thread`,
   if you'll ever want a secondary, read-only Q&A session tracking a primary one.

That's the whole install. The first response after that should follow the contract — Targets (if
one is stated), Threads, Work done, Open questions, Actions, Background, TL;DR — and publish a
local page under `~/.claude/projects/<project>/registers/`.

## Requirements

- Python 3, standard library only.
- `jq`, for the hook script to emit its JSON payload.
- A `<dialog>`-capable browser for the new-round modal on the published page (any current
  Chrome, Safari, Firefox or Edge).
- `publish-register.py --open` shells out to the `open` command, which is macOS-specific; omit
  the flag on other platforms and open the printed path yourself.

## License

Apache License 2.0 — see `LICENSE` and `NOTICE`.
