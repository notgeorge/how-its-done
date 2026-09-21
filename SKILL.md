---
name: response-format
description: How to end a response to George — the Work done / Open questions / Actions register, its identifiers, the file that carries them, and the clarification gate. Read before composing any substantive reply; the UserPromptSubmit hook points every turn at this file.
---

# How to report to George

BLUF: the answer comes first, in prose, in plain words. The tables are a **register**, not the
message. They exist so a standing item is a row with an age, not a fresh-looking ask repeated every
turn.

## The clarification gate — runs BEFORE anything else

When George answers, re-read his answers before executing. If any of them is unclear, ambiguous, or
leaves a decision you would have to guess at: **halt. Change nothing. Ask.**

A clarification carries three things: the **identifier** of the item, the **concern** (why you cannot
act on it as written — what two readings exist, what breaks under each), and the **questions**. He
replies with the identifier. Do not soften the halt by starting work "in the meantime" on the thing
being clarified; unrelated in-flight work continues normally and is reported as usual.

Guessing costs more than asking. A wrong guess executed is work to undo plus trust to rebuild; a
question costs one round.

## Render order

Prose answer, then **Work done → Open questions → Actions → Background**, in that order every time.
Background sits last, under Actions (George, r30): it is status, not something he acts on, so it
must never push his to-do list further down the screen.

## The three tables

Every entry has a **short title** and an **identifier**. Identifiers are `W`/`Q`/`A` plus a number,
allocated in order, **never reused, never renumbered**.

### Work done

**Open with a one-line summary** in bold: what, overall, just happened. It is the context line —
George reads it before the rows and should know the shape of the work from it alone ("Response-format
contract built and installed; PR# 720 bookkeeping cleared"). One line, no preamble, and it names the
gap's through-line rather than the first row.

Then the rows: everything done **since George last spoke** — cumulative across the whole gap, not
just since the last thing you said. He may answer, a PR watcher may fire twenty minutes later, and you may work for
another hour; all of it belongs in the next Work table. This replaces "lessons learned", which
drifted into navel-gazing.

**Three columns** (r19: the Evidence column was folded into the cell — four columns of long prose
was still too wide, and evidence reads better as the closing line of the thing it evidences):

| Column | Contains |
| --- | --- |
| ID | `W12` |
| Thread | The thread emoji (see Threads below) |
| Title | 4-8 words — enough to carry the substance, not a label |
| What I did | **Several sentences**. What was done, what it changed, why it was done that way, and what it means for the work. This is where you earn your keep. **Close with the evidence on its own line**, prefixed `Evidence:` — the sha, the count, the command's result, the link. |

**Do not compress meaning out of the `What I did` cell.** The failure George named (r18): terse
rows read fine in the moment and become untrackable a day later, because the reasoning that made
them make sense was never written down. He is tracking this work over time and across sessions —
write for the version of him reading it cold next week.

A row says what happened, how you know, and why it mattered. "Verified the guard" is not a row.
"Ran the guard on the 8020 stack — its first real execution, since the earlier host-side check
could not see runtime-appended apps. 186 guards pass. Then seeded a defect (deleted the tap_health
row, pointed a citation at a missing file) and confirmed it fails naming both, so the pass is not
vacuous" is.

### Open questions

Questions **for George**. Leave the table out entirely when there are none — write nothing, not a
placeholder, and never invent a question to fill the section. An invented question costs him a
decision he did not need to make.

| Column | Contains |
| --- | --- |
| ID | `Q7 · r14` — identifier and the round it was raised; the age is the signal |
| Thread | The thread emoji (see Threads below) |
| `?` | The question's title, 4-8 words. Plain text — no bold |
| `??` | The question itself: what you need decided, in full sentences |
| Why it matters | What it blocks, or what goes wrong if it is decided the other way |

The title and the question are separate columns (George, r34) so the titles form a scannable left
edge instead of being buried at the head of a paragraph.

**Answered questions drop off.** Once he rules, the row disappears from the next response; the
ruling is recorded in the register file, not re-displayed. Unanswered questions **carry forward
unchanged, with their original ID and Raised value**.

### Actions

What **George** does, never what you are doing.

**Four columns, never more** (see Width below):

| Column | Contains |
| --- | --- |
| ID | `A3 · r7` — the identifier and the round it first appeared, so its age rides along without a column |
| Thread | The thread emoji (see Threads below) |
| Action | 4-8 word title, then the concrete act: approve this PR, run this command, reply to this person. Plain text — no bold |
| Why | **Several sentences**. What it unblocks, what is waiting on it, what happens if it keeps waiting, and any context he needs to decide. Not a phrase. |
| Recommendation | Your actual opinion, stated plainly. Required — SBAR's discipline: the recommendation is a named field, not an optional flourish. |

Actions persist until done or withdrawn. An action open for many rounds is visible as one aging row
rather than six identical asks — the failure this format exists to fix.

## Background — one row, after Actions

**What it is for (George, r31):** the live waits that will make this session wake up and jump ahead
on its own — a PR-review watcher, a CI run being polled, a background command still executing, a
subagent in flight, a scheduled wakeup, a peer session whose reply is expected. Seeing a row means
**the session is parked**: he can walk away and ignore it until the thing fires. Seeing no row means
nothing will move unless he says something.

A single row, after Actions. First cell is the label, then one cell per wait, each saying what it is
and **when it should fire**, because that is the number that tells him how long to ignore the session:

| Background | PR# 733 seats — triage watcher, ~2 min | full lane on `feat/x`, ~9 min | gc-phase3 session, reply expected |

**Omit the row entirely when nothing is waiting.** No empty strip, no placeholder.

**What does NOT belong here:** idle leftovers — a spawned stack nobody is using, a merged worktree, a
branch awaiting cleanup. Those are not waits and reading them as "the session is busy" is exactly the
wrong signal. They belong in an Action (cleanup he approves) or a Work row (cleanup already done).
The first version of this section listed them and was wrong for that reason.

## No bold inside register cells

Cell text is plain (George, r34): bold inside Question and Action cells is hard to look at in the
terminal, where the renderer already separates rows. Bold belongs to the Work-done summary line and
to prose above the register, not to the grid. Backticks for paths, commands and identifiers are fine.

## Threads — named lines of thought

A **thread** is a line of thought that outlives one exchange.

**You detect and number threads, not George** (ruled r36). Read his message, notice when he has
opened a new line of thought, and give it a number, an emoji, a title and a description in the
Threads table. He types nothing. `>T#` remains available when he wants to point at a specific
thread — an existing number references it — but it is a convenience, never a requirement, and its
absence never means "no thread".

**The bar for opening one:** a thread is something that will come BACK — a line of work, a standing
question, a system being built. A one-off question answered in the same breath is not a thread; it
is an Answer row on an existing thread, or just prose. Over-threading is the failure to design
against: a table of twenty numbered lines, most of them dead, is noise wearing a schema. If you are
unsure, attach the row to the nearest existing thread and let a second occurrence prove it deserves
its own number.

**When you get it wrong** — split something that was one thread, or merge two that were not — George
corrects it by ID. Renumbering is forbidden (IDs are permanent), so a wrong split is fixed by
retiring one number with a description saying where it went, never by reusing it.

**The Threads table is authoritative and renders every round**, before the other tables:

| T# | 🧵 | Title | Description |
| --- | --- | --- | --- |
| T1 | 📐 | Response format | The register contract itself: shape, columns, rendering, this skill |

- The number and the emoji are **assigned once and never reused**, exactly like a row ID. The emoji
  is the same glyph the register rows carry, so a reader can trace a thread either way.
- A `>T#` that already exists **references** that thread. A `>T#` that does not exist **opens** one:
  give it a title, a description and the next free emoji.
- A thread stays in the table while it is live. When it is finished, say so in its description and
  drop it the following round — the same rule as an answered question.

### Tagging rows

Every register row's thread column carries `T# 🧵` (e.g. `T4 🔌`), not the bare emoji. The number is
what George types; the emoji is what he scans for.

### Answers — AW#

When George asks something inside a thread, answer it in two parts (ruled r38).

**1. A single-row table carrying the answer in ONE sentence:**

| AW# | T# | Answer |
| --- | --- | --- |
| AW2 | T9 🔍 | No — the declaration is mandatory even when the key is absent, and nothing is derived today. |

**2. The explanation as prose directly below that table** — paragraphs, headings and lists as the
material needs, with blank lines between blocks so it is readable. A long cell in a table is not
readable in a terminal; a paragraph is. The table is the verdict and the durable identifier, the
prose is the reasoning.

One table per answer. Two thread questions in a message means two single-row tables, each followed
by its own prose, never one table with two rows.

- `AW#` identifiers are stable and never reused, so he can refer back to an answer the way he refers
  to a work row.
- The sentence in the table must be able to stand alone. If the one-sentence version needs a
  qualifier to be true, the qualifier goes in the sentence — not in the prose below it.
- The explanation is written in full: this is where the reasoning lives, so the same
  spend-the-words rule as `What I did` applies.
- Answers **drop off** the round after they are given, like answered questions; the register file
  keeps them.
- The table is **omitted entirely** when no thread question was asked. Never invent one.

Order with the rest of the register: **Threads → Answers → Work done → Open questions → Actions →
Background.** Threads and answers come first because they are what he asked about; work and actions
are what happened around them.

## Width — these are terminal tables

**One consolidated table per section. Three or four columns, prefer three. Cells are as long as the
meaning requires.**

No padding tricks inside the register. `<br>` does not render in George's terminal (r19), and the
two alternatives tried at r20 — blank spacer rows, and a separate mini-table per entry — both
FAILED on his ruling: "too much cognitive load". A reader scanning a register wants one aligned
grid, not entries to reassemble. The table's own row borders are the separation; that is enough. A six-column Actions table
stopped rendering as a table at all in George's terminal (observed r16) — it degraded into a run-on
list. The cure is fewer columns, NOT shorter cells: a narrow table with rich cells renders fine, and
r18 established that thin cells are the worse failure, because they compress meaning past the point
where he can track the work over time. Few columns, full sentences.

## Trivial turns

For an acknowledgement, a status check, or a one-line answer, **drop the three tables**. Give a
single net-net table instead:

| Title | Description |
| --- | --- |
| Guard green | Lane settled on 545f15c2; all seats clean |

## The register file

The tables are rendered from a file, never from memory — IDs must survive compaction, and a
carried-forward age is a lie if the numbering restarts.

- Location: `<session scratchpad>/response-register.md` (the scratchpad directory named in the
  session's environment).
- Contents: the three tables plus a **Rulings** section — one line per answered question and closed
  action, with the ruling and the round. That is what makes an interrupted or compacted session
  resumable, and what keeps a dropped row recoverable.
- Update it **before** composing the response: append new rows, mark answered ones, bump the round.
  Then render the open rows.

## What kills this format

Each of these was observed, not imagined:

- **Repetition.** The same ask, reworded, every turn. One row, one ID, an ageing `Since`.
- **Manufactured items.** A block that exists wants filling. Empty is a legitimate state.
- **Reflection in the Work table.** "This taught me to be careful" is not work. Evidence is.
- **Actions that are yours.** "I'll confirm the lane is green" belongs in prose, not in his list.
- **Tables on a one-line answer.** Overhead trains him to skip the tables entirely.
- **Compression.** A row so terse it is untrackable next week. The register is a record he reads
  over time, not a status line — spend the words.
- **Layout fiddling.** Spacer rows, per-entry tables, HTML padding. Tried and rejected at r20: each
  one trades a scannable grid for reassembly work. One table per section, full stop.
