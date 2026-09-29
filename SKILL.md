---
name: response-format
description: How to end a response to the user — the Targets / Threads / Work done / Open questions / Actions register, its identifiers, the file that carries them, and the clarification gate. Read before composing any substantive reply; a `UserPromptSubmit` hook can point every turn at this file (see `hooks/response-format-reminder.sh`).
---

# How to report

BLUF: the answer comes first, in prose, in plain words. The tables are a **register**, not the
message. They exist so a standing item is a row with an age, not a fresh-looking ask repeated every
turn.

## The clarification gate — runs BEFORE anything else

When the user answers, re-read their answers before executing. If any of them is unclear, ambiguous,
or leaves a decision you would have to guess at: **halt. Change nothing. Ask.**

A clarification carries three things: the **identifier** of the item, the **concern** (why you cannot
act on it as written — what two readings exist, what breaks under each), and the **questions**. They
reply with the identifier. Do not soften the halt by starting work "in the meantime" on the thing
being clarified; unrelated in-flight work continues normally and is reported as usual.

Guessing costs more than asking. A wrong guess executed is work to undo plus trust to rebuild; a
question costs one round.

## Render order

Prose answer, then **Targets → Threads → Work done → Open questions → Actions → Background**, in
that order every time. **Targets renders first and every round while any Target is active — not
only on the round it was stated, not only when the reply happens to be about it** (a Target has been
seen to drop silently the round after intake, precisely the failure the table exists to catch).
Background sits last, under Actions: it is status, not something the user acts on, so it must never
push their to-do list further down the screen.

## Targets — what the session is aiming at

A **Target** is the session's own aim, stated by the user, not detected by you the way Threads are.
One or two active at a time — more than that stops being a guardrail and becomes a second to-do
list. Where a Thread is "a line of thought that outlives one exchange," a Target is bigger and
flatter: it is *why* the threads underneath it exist, and it is written so it can be **hit or
missed**, not just discussed.

**The user paints the target; you evaluate it before it goes in the table.** When they state one,
weigh in — plainly, before rendering it as accepted:

- **Actionable** — is there a concrete next step, or is it a wish?
- **Hittable** — can this plausibly close within the session, not an open-ended aspiration that
  never resolves?
- **Falsifiable** — is there a condition that clearly says "hit" versus "not yet," or could
  everything and its opposite both be argued to satisfy it?
- **Concerns** — anything that gives you pause: too broad, conflicts with an already-active
  Target, hides a decision they haven't actually made yet.

Say this once, briefly, when the Target is stated — not as a table, as prose, the same register a
clarification gets. They can revise it in response; only render it into the Targets table once it
is in a shape you would be willing to be held to.

**If a session gets underway with no Target stated, remind them once** — a short line, not a block
— rather than silently proceeding without one. Ongoing work continues normally; this is a nudge,
not a gate.

**Table shape**, above Threads, rendered EVERY ROUND while any Target is active — including a
round that is entirely about something else, a trivial round, a round that only answers a Thread
question. The table costs three lines and answers "are we still aimed at the thing" without the
user having to ask. Omit it only once no Target is active at all.

| X# | 🙂 | Target | Hit when | Status |
| --- | --- | --- | --- | --- |
| X1 | 😎 | Close the export job's retry gap | Retry logic built, verified, and merged | Active |

- The ID prefix is `X`, so it never collides with `T` (Threads), `W`/`Q`/`A` (the register rows),
  or `AW` (answers). Assigned once, never reused — the same rule every other identifier in this
  file follows.
- The glyph is a **smiley**, one per Target, chosen to be visually distinct from any other Target
  active this session — this is deliberately a different family than the Threads glyphs (🔎, 🩹,
  📜, ...), so a face means "which aim" and the other glyph means "what kind of thread," and the
  two are never confused for each other. Pick from a varied, legible rotation (😎 🤓 🧐 🥳 😌 🤠
  🥸 😏 and similar) rather than reusing the same one or two faces every session.
- `Hit when` is the falsifiable condition agreed at intake — not restated prose, the actual test.

### Tagging Threads with a Target

Every Thread that serves an active Target carries that Target's smiley **alongside** its own
glyph: `T9 🔎😎` — still legible as "an investigation," now also legible as "the 😎 target's."

**A Thread with no Target's smiley is the drift signal, made visible instead of narrated.** Don't
invent a mapping to avoid the gap — if a Thread doesn't trace to a stated Target, it wears `⚠️`
instead of a face:

| T# | | Title | Description |
| --- | --- | --- | --- |
| T9 | 🔎😎 | Scheduled-task timeout gap | serves X1 |
| T12 | 🩹⚠️ | (unrelated one-off fix) | not mapped to any active Target |

Seeing `⚠️` on a row is the cue to say so out loud — either the Target should expand to cover it
on purpose, or it should not be happening without a check-in. Never quietly pick a Target to pin
it to just to clear the warning.

### Closing a Target

When a Target is hit, missed, or abandoned, say which — plainly, in prose, the same way a Thread
closure gets a status box — before it drops from the live table. A Target does not just fade out;
it resolves.

| X# | Verdict |
| --- | --- |
| X1 | Hit — the retry primitive built, verified two ways, merged into the downstream service, both PRs open |

Closed Targets move to a short reference list under the live table, the same pattern Threads use,
so a later session can see what this one was actually aimed at without re-reading the transcript.

## The three tables

Every entry has a **short title** and an **identifier**. Identifiers are `W`/`Q`/`A` plus a number,
allocated in order, **never reused, never renumbered**.

### Work done

**Open with a one-line summary** in bold: what, overall, just happened. It is the context line —
the user reads it before the rows and should know the shape of the work from it alone
("Response-format contract built and installed; PR #42 bookkeeping cleared"). One line, no
preamble, and it names the gap's through-line rather than the first row.

Then the rows: everything done **since the user last spoke** — cumulative across the whole gap,
not just since the last thing you said. They may answer, a PR watcher may fire twenty minutes
later, and you may work for another hour; all of it belongs in the next Work table. This replaces
"lessons learned", which drifted into navel-gazing.

**Three columns** (the Evidence column is folded into the cell — four columns of long prose was
still too wide, and evidence reads better as the closing line of the thing it evidences):

| Column | Contains |
| --- | --- |
| ID | `W12` |
| Thread | The thread emoji (see Threads below) |
| Title | 4-8 words — enough to carry the substance, not a label |
| What I did | **Several sentences**. What was done, what it changed, why it was done that way, and what it means for the work. This is where you earn your keep. **Close with the evidence on its own line**, prefixed `Evidence:` — the sha, the count, the command's result, the link. |

**Do not compress meaning out of the `What I did` cell.** Terse rows read fine in the moment and
become untrackable a day later, because the reasoning that made them make sense was never written
down. The user is tracking this work over time and across sessions — write for the version of them
reading it cold next week.

A row says what happened, how you know, and why it mattered. "Verified the guard" is not a row.
"Ran the test suite against the staging environment — its first real execution against live data,
since the earlier check only ran against fixtures. 340 tests pass. Then seeded a defect (removed a
required field, pointed a validation rule at a renamed column) and confirmed it fails naming both,
so the pass is not vacuous" is.

### Open questions

Questions **for the user**. Leave the table out entirely when there are none — write nothing, not a
placeholder, and never invent a question to fill the section. An invented question costs them a
decision they did not need to make.

| Column | Contains |
| --- | --- |
| ID | `Q7 · r14` — identifier and the round it was raised; the age is the signal |
| Thread | The thread emoji (see Threads below) |
| `?` | The question's title, 4-8 words. Plain text — no bold |
| `??` | The question itself: what you need decided, in full sentences |
| Why it matters | What it blocks, or what goes wrong if it is decided the other way |

The title and the question are separate columns so the titles form a scannable left edge instead
of being buried at the head of a paragraph.

**Sub-questions get their own lines, lettered.** When one entry asks several things, write each as
its own line inside the `??` cell — `Q23a …`, `Q23b …` — so the user can answer line by line
(`Q23c - yes`). In the draft, separate them with ` ¶ `; the renderer starts each segment on a new
line in its column (a table cell cannot hold a newline, and `<br>` does not render in a terminal).
The same break works in any cell whose content has parts worth separating. A cell that must show a
literal pilcrow cannot — `¶` is reserved for the break.

**Answered questions drop off.** Once the user rules, the row disappears from the next response;
the ruling is recorded in the register file, not re-displayed. Unanswered questions **carry forward
unchanged, with their original ID and Raised value**.

### Actions

What **the user** does, never what you are doing.

**Five columns, never more** (see Width below). **Why and Recommendation are SEPARATE columns —
never fused into one cell.** They answer different questions and are read differently: Why is the
situation, checked against what's already known; Recommendation is your opinion, which the user
overrules or accepts. Fused, the opinion hides inside the description of the situation and the user
cannot see where the facts stop and the advice starts — which is the one thing this table exists to
keep visible. The fusion creeps in for the same reason terseness does, to save width, and costs the
same thing.

This does NOT generalise to Work done, which goes the other way: Evidence is folded *into* the
`What I did` cell there, because four columns of long prose was too wide and evidence reads better
as the closing line of the thing it evidences. Actions splits because Why and Recommendation are
different kinds of claim; Work done merges because evidence is the same claim's proof.

| Column | Contains |
| --- | --- |
| ID | `A3 · r7` — the identifier and the round it first appeared, so its age rides along without a column |
| Thread | The thread emoji (see Threads below) |
| Action | 4-8 word title, then the concrete act: approve this PR, run this command, reply to this person. Plain text — no bold |
| Why | **Several sentences**. What it unblocks, what is waiting on it, what happens if it keeps waiting, and any context the user needs to decide. Not a phrase. |
| Recommendation | Your actual opinion **and the reason for it**, stated plainly — enough that the user can disagree with the reasoning, not just the verdict. "Merge it" is a verdict; "Merge it — the spec change is the consequential half and it's already been through four review rounds" is a recommendation. Required — SBAR's discipline: the recommendation is a named field, not an optional flourish. |

**Terseness creeps in over a long session, and the Actions table is where it shows first.** The
Work-done rows tend to stay rich because they are narrating something that just happened; Actions
rows decay into fragments — "Own session", "Cheapest win" — because by then the context feels
obvious *to you*. It is not obvious to the user, and it is much less obvious to them next week. A
cell that only makes sense if you already sat through the session is a cell that failed. When a row
repeats across rounds, carrying it forward verbatim is fine — shrinking it each round is the drift.

Actions persist until done or withdrawn. An action open for many rounds is visible as one aging row
rather than six identical asks — the failure this format exists to fix.

## Background — one row, after Actions

**What it is for:** the live waits that will make this session wake up and jump ahead on its own —
a PR-review watcher, a CI run being polled, a background command still executing, a subagent in
flight, a scheduled wakeup, a peer session whose reply is expected. Seeing a row means **the
session is parked**: the user can walk away and ignore it until the thing fires. Seeing no row
means nothing will move unless they say something.

A single row, after Actions. First cell is the label, then one cell per wait, each saying what it
is and **when it should fire**, because that is the number that tells the user how long to ignore
the session:

| Background | PR #142 checks — CI watcher, ~2 min | full test lane on `feat/x`, ~9 min | a peer session, reply expected |

**Omit the row entirely when nothing is waiting.** No empty strip, no placeholder.

**What does NOT belong here:** idle leftovers — a spawned stack nobody is using, a merged worktree,
a branch awaiting cleanup. Those are not waits and reading them as "the session is busy" is exactly
the wrong signal. They belong in an Action (cleanup the user approves) or a Work row (cleanup
already done). The first version of this section listed them and was wrong for that reason.

## No bold inside register cells

Cell text is plain: bold inside Question and Action cells is hard to look at in the terminal, where
the renderer already separates rows. Bold belongs to the Work-done summary line and to prose above
the register, not to the grid. Backticks for paths, commands and identifiers are fine.

## Threads — named lines of thought

A **thread** is a line of thought that outlives one exchange.

**You detect and number threads, not the user.** Read their message, notice when they have opened a
new line of thought, and give it a number, an emoji, a title and a description in the Threads
table. They type nothing. `>T#` remains available when they want to point at a specific thread — an
existing number references it — but it is a convenience, never a requirement, and its absence never
means "no thread".

**The bar for opening one:** a thread is something that will come BACK — a line of work, a standing
question, a system being built. A one-off question answered in the same breath is not a thread; it
is an Answer row on an existing thread, or just prose. Over-threading is the failure to design
against: a table of twenty numbered lines, most of them dead, is noise wearing a schema. If you are
unsure, attach the row to the nearest existing thread and let a second occurrence prove it deserves
its own number.

**When you get it wrong** — split something that was one thread, or merge two that were not — the
user corrects it by ID. Renumbering is forbidden (IDs are permanent), so a wrong split is fixed by
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

### Closing a thread

When the user asks to close one (`close T1`, `close T3 and T4 yourself`), give a **status box**
before it drops off: everything still outstanding on that thread — an unmerged PR, an uncommitted
diff, a follow-up nobody has done — each with your recommendation. A thread with nothing
outstanding says so plainly ("Nothing outstanding — clean close") rather than the box being
silently absent, because absence reads as "I forgot to check," not "there was nothing to report."

One small table per closed thread, right where the closure is reported:

| Item | Recommendation |
| --- | --- |
| PR #48 — open, green, unmerged | Merge when ready |
| `src/models.py` etc. — uncommitted in this worktree | Commit whenever you want it |

Then the thread drops from the Threads table as usual. The box is what makes "closed" mean
something — without it, closed and finished look identical even when a PR is still sitting open or
a diff is still sitting uncommitted, and that gap is exactly what this box exists to close.

### Tagging rows

Every register row's thread column carries `T# 🧵` (e.g. `T4 🔌`), not the bare emoji. The number is
what the user types; the emoji is what they scan for.

### Answers — AW#

When the user asks something inside a thread, answer it in three parts.

**1. A single-row table carrying the answer in ONE sentence:**

| AW# | T# | Answer |
| --- | --- | --- |
| AW2 | T9 🔍 | No — the declaration is mandatory even when the key is absent, and nothing is derived today. |

**2. The original question, quoted or summarized, as its own line directly under that table.**
Written `> Asked: "..."` — the exact words when they stand alone cleanly, a tight summary when the
original message was longer or more disjointed than a single quotable sentence. This is what lets
an answer be read on its own later, without scrolling back to find out what prompted it — the
verdict alone does not carry that.

**3. The explanation as prose directly below the question line** — paragraphs, headings and lists
as the material needs, with blank lines between blocks so it is readable. A long cell in a table is
not readable in a terminal; a paragraph is. The table is the verdict and the durable identifier,
the question is what was asked, the prose is the reasoning.

One table per answer. Two thread questions in a message means two single-row tables, each followed
by its own prose, never one table with two rows.

- `AW#` identifiers are stable and never reused, so the user can refer back to an answer the way
  they refer to a work row.
- The sentence in the table must be able to stand alone. If the one-sentence version needs a
  qualifier to be true, the qualifier goes in the sentence — not in the prose below it.
- The explanation is written in full: this is where the reasoning lives, so the same
  spend-the-words rule as `What I did` applies.
- Answers **drop off** the round after they are given, like answered questions; the register file
  keeps them.
- The table is **omitted entirely** when no thread question was asked. Never invent one.
- The `Asked:` line is **required** whenever the table is present — `check-response.py`'s
  `check_answers` fails an answer with no `> Asked: ...` line as its first line after the table.

**How it renders.** Answers do NOT take the grid's columns — explanation, then the text below it,
width-constrained rather than filling the whole screen, with any call-outs placed Tufte-style in a
column to the right. So `render-register.py` draws each answer as:

- a **headline**: `AW#` at the ID edge, the thread tag, then the one-sentence answer — the round
  trails like every other row;
- the **original question**, italicized, on its own line at the answer's text column — unlabeled in
  the terminal (no column label the format doesn't already carry elsewhere), set on the page with a
  small caps "Asked" tag and a tinted left rule, the same idiom as Hit when and Evidence; the
  renderer adds no quote marks of its own, so write `"..."` in the draft when it is a direct quote;
- the **explanation** as prose underneath, starting at the answer's text column (the ID edge stays
  clean for scanning), wrapped at `ANSWER["text"]` = 80 display columns so it never runs the width
  of the terminal; `- ` lines render as bullets;
- **sidenotes**, Tufte-style, in a right-hand column (`ANSWER["side"]` = 46) level with the
  paragraph they annotate. Use them for the call-out a reader should see without reading the
  paragraph — a caveat, the evidence, the one number — not for a second explanation.

Draft source: under `## Answers`, the single-row `| AW# | T# | Answer |` table per answer (so
`check-response.py`'s `check_answers` still finds it by the `AW` header), then a `> Asked: "..."`
line quoting or summarizing what prompted it, then the explanation as plain paragraphs separated by
blank lines, with a `> ` line directly under a paragraph for that paragraph's sidenote — the same
`>` prefix, but only the line immediately after the table is ever read as `Asked:`; every later
`> ` line is a sidenote. The old instruction "the explanation as prose directly below that table"
still holds — this is its rendered form, not a replacement.

Order with the rest of the register: **Targets → Threads → Answers → Work done → Open questions →
Actions → Background.** Targets and Threads come first because they frame what was asked about;
work and actions are what happened around them.

## The rendered layout

The register is no longer markdown tables. It is fixed-width columns emitted as plain text,
which buys wrapped cells, controlled line breaks and a readable measure — while keeping inline
markdown live, which a fenced block does not. `check-response.py` in this directory renders it
and checks it against the rules below, sharing one parser so the two cannot drift.

**How it holds together.** Padding is non-breaking spaces (U+00A0), which markdown does not
collapse the way it collapses ordinary runs. Every line ends with two trailing spaces, a GFM
hard break, so hand-wrapped lines are not reflowed into one paragraph. `<br>` is NOT an option
— it renders as literal text in most terminals.

**Measure the render, not the source.** A cell whose source is `` `#767` `` is seven characters
and displays as four. Wrapping and padding both count display width and emit source text;
getting this wrong pushes every column after a code span out of line.

**The settled geometry:**

| Thing | Value |
| --- | --- |
| Total width | 200 columns |
| Body cell cap | ~66-72 columns, so prose wraps at a readable measure |
| Gutter | 5 non-breaking spaces between every column |
| Column order | ID, thread tag, title, body (and Recommendation in Actions), round trailing |
| Row order | Oldest first, by the round raised — staleness becomes position, which costs no ink |
| Between tables | Two blank lines (held open by NBSP lines; genuinely empty ones collapse) |
| Between rows | One blank line; in Open questions, also a `╌` divider line under every question but the last (sub-question blanks made the boundary between questions invisible otherwise) |
| Heading | `SECTION ┈┈┈┈…` — the hairline trails the name and runs the width; in Actions it runs to the `Recommendation` label |
| Work-done summary | A `WDS:` row BELOW the work table, not above it — it is what the user glances back to, so it sits where the eye lands after reading the rows |
| Header row | None, except `Recommendation` on the Actions heading line |

**Why each of those, briefly, so a later session does not "improve" them back:**

- **ID stays leftmost** even though Tufte says the left edge belongs to meaning — people type an
  identifier like `A48` back constantly, and hunting the right margin for it is worse than the
  problem it solves.
- **The thread tag sits second**, not trailing. It reads as administrative metadata and is not: it
  answers "which of my goals does this serve", which is exactly what gets scanned for. An earlier
  version moved it to the trailing edge on Tufte grounds and that was wrong.
- **One grid across all three tables**, not per-table widths, so the eye stops re-acquiring the
  column boundary at every section. A narrow table carrying a wider gutter than it needs is the
  price, and it is the right one.
- **Glyphs are measured at two columns** (`unicodedata.east_asian_width`), combining marks and
  ZWJ at zero. Pad by `len()` and every row with an emoji goes ragged.
- **Bold is banned in every cell, not just some.** Beyond legibility it is now mechanical: a bold
  run can render wider than its plain equivalent and skew its own column and all after it.
- **The hairline is `┈`, not `-`.** A run of hyphens is markdown: it becomes a horizontal rule, or
  turns the line above it into a setext heading. Box-drawing characters have no markdown meaning
  and cannot break the hard-break scheme.

## TL;DR — the closing summary

**Last section, after Background.** A short list of bullets under the same hairline as every
other section, rendered from a `## TL;DR` section of `- ` lines in the draft.

**What it covers: the PROSE at the top of the response, and nothing else.** Threads, Open
questions, Actions and Targets all render their own rows; summarising them again here is the
"repetition" failure this whole format exists to remove. The prose answer is the only part of a
response with no row of its own, and therefore the only part with no other way to be found
again — the point of this section is knowing whether it's worth scrolling back up to reread it.

**Format:** bullets at a fixed width so nothing wraps off the page at any terminal width, with a
blank line between each so they breathe. `render-register.py` does all of that; write the draft
section as plain `- ` bullets and let it render.

**This section is here because it was missing at first.** The TL;DR was built into the renderer
before it was written down here, so sessions following this file — correctly — never produced one,
and it kept silently disappearing until that gap was closed. That is the third time the contract
and its tooling drifted apart in one stretch of work (`THREAD_TAG`, the Work-done summary
placement, this). The lesson is not "document better", it is that **a rule that lives only in code
is not part of the contract**, and the person who adds a feature to the renderer owns writing it
here in the same change.

## Publishing: local register pages

**Every session, every round.** Publish consistently so every session uses the same live page
pattern.

**History, so nobody goes back.** The register once moved from fixed-width terminal text to HTML,
because HTML has rows and cells and the width arithmetic above stops being load-bearing. It was
first published as a hosted-artifact page republished in place. That lost the history, because each
republish replaced the last round and there was no way to look back. So the pages are LOCAL files,
one kept per round, plus a live page that follows the newest round. Do not publish the register to
a third-party hosted-artifact service — the per-round history is the point.

**The round, end to end:**

    # 1. update the register, write the draft, validate (unchanged)
    python3 ~/.claude/skills/response-format/render-register.py --check --register <register> <draft-rN.md>
    # 2. publish the pages (run from the session's working directory)
    python3 ~/.claude/skills/response-format/publish-register.py <draft-rN.md>
    # 3. the terminal block
    python3 ~/.claude/skills/response-format/render-artifact.py <draft-rN.md> --terminal

`publish-register.py` takes the session name from the working directory's basename (override
with `--session NAME`). It writes to `~/.claude/projects/<cwd slug>/registers/`, the project's own
Claude directory, so each session keeps its own history:

| File | What it is |
| --- | --- |
| `rN.html` | This round, kept forever. Header: session · round · timestamp, prev/next, all rounds, latest |
| `rN.draft.md`, `rN.time` | The source draft and the first-publish time, so a re-stitch never moves the stamp |
| `current.html` | The live page. It polls `latest.js` every 5s; a newer round pops a modal naming the round and its TL;DR, with one autofocused button — Enter reloads |
| `latest.js`, `index.html` | The newest round number, and every round newest-first with its TL;DR headline |

The draft's file name carries the round (`draft-r125.md` becomes r125). The header colours come
from the renderer's theme tokens, so it follows light and dark with the rest of the page.

**What goes where:**

| Surface | Carries |
| --- | --- |
| The page | Everything. The prose answer, then Targets → Threads → Answers → Work done → Open questions → Actions → Background → TL;DR |
| The reply in the terminal | The prose BLUF; then the `--terminal` output VERBATIM in a code fence: `<session> · r<N>`, Targets, TL;DR, and an INDEX of Open questions and Actions (identifier, glyphs, the 4-8 word title); then one line with the live page's path |

The index is a pointer, not a summary. Its job is that the user can type `A48` back without
opening the page, and can see at a glance how many decisions are waiting on them. The code fence
keeps the index's alignment intact in the terminal.

**A trivial turn** (a watcher firing mid-wait, an ack) does not publish a round. It gets the net-net
table in *Trivial turns* below. Publish when the register has changed enough to be worth a page.

**The tooling.** Both renderers import ONE parser from `check-response.py`, which is what stops the
page and the terminal becoming two different truths. `render-register.py` still renders the full
fixed-width form and still owns `--check`, the only contract validator. Use its full render only
where local files cannot be opened.

**What did NOT move.** `¶` is still the reserved sub-question break, because the sentinel lives in
the DRAFT format, upstream of both renderers — a cell still cannot show a literal pilcrow. The
`--check` rules on cell length, bold-in-cells and Evidence lines still apply: they are about
whether the writing carries meaning, not about whether the terminal can paint it.

**Targets stays in the terminal too.** It prints FIRST, above the TL;DR, one compact line per
Target with its status; `Hit when` is page-only. The reason it survived the move to HTML is the
reason it exists: it is the every-round guardrail that answers "are we still aimed at the thing"
without the user asking, and the failure it was built to catch was it silently vanishing. A
guardrail behind a click does not guard — if the user has not opened the page, the thing the table
exists to catch is exactly what has happened. Background did not get the same treatment and is
page-only.

**Evidence gets its own column on the page — and this is not a reversal of the terminal-form rule
above.** The terminal folds Evidence INTO the `What I did` cell because four columns of long prose
is too wide *in a fixed-width terminal*. That constraint does not exist in HTML. So the page sets
Evidence in a column to the right of the description, and the text renderer keeps the folded form.
Both are correct for their surface; the rule was never about where evidence belongs, it was about
what a terminal can paint.

**Each section carries one muted hue on the page**, so headers, sub-headers and tables use colour
gently rather than reading as one monotone block. Targets plum, Threads dusty blue, Answers violet,
Work done teal, Open questions ochre, Actions terracotta, Background slate, TL;DR sage. The hue is
spent in five places only: the section heading and its faint band, the ID column, the hairline
between rows, the Evidence bar and the Work-done summary row. Body text, glyphs and links stay
neutral, so colour says where you are on the page and never what a row means. Tokens are `--hue-*`
in `render-artifact.py`, redefined for dark, and every hue clears 4.4:1 against the page in both
themes. The terminal cannot do this — custom terminal theme colours have been observed not to reach
assistant-generated output — so the terminal block's only colour is emoji.

## Width — these are terminal tables

**One consolidated table per section. Three or four columns, prefer three. Cells are as long as the
meaning requires.**

No padding tricks inside the register. `<br>` does not render in most terminals, and the two
alternatives tried — blank spacer rows, and a separate mini-table per entry — both failed: one
aligned grid scans far better than entries that must be reassembled by eye. The table's own row
borders are the separation; that is enough. A six-column Actions table has been observed to stop
rendering as a table at all in some terminals — it degrades into a run-on list. The cure is fewer
columns, NOT shorter cells: a narrow table with rich cells renders fine, and thin cells are the
worse failure, because they compress meaning past the point where the reader can track the work
over time. Few columns, full sentences.

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
- Contents: Targets, Threads, and the three register tables, plus a **Rulings** section — one line
  per answered question and closed action, with the ruling and the round. That is what makes an
  interrupted or compacted session resumable, and what keeps a dropped row recoverable.
- Update it **before** composing the response: append new rows, mark answered ones, bump the round.
  Then render the open rows.

## What kills this format

Each of these was observed, not imagined:

- **Repetition.** The same ask, reworded, every turn. One row, one ID, an ageing `Since`.
- **Manufactured items.** A block that exists wants filling. Empty is a legitimate state.
- **Reflection in the Work table.** "This taught me to be careful" is not work. Evidence is.
- **Actions that are yours.** "I'll confirm the lane is green" belongs in prose, not in the user's
  list.
- **Tables on a one-line answer.** Overhead trains the user to skip the tables entirely.
- **Compression.** A row so terse it is untrackable next week. The register is a record read
  over time, not a status line — spend the words.
- **Layout fiddling.** Spacer rows, per-entry tables, HTML padding. Both were tried and rejected:
  each one trades a scannable grid for reassembly work. One table per section, full stop.
- **The Targets table dropped after intake.** Rendered the round a Target was accepted, then
  silently gone the next round because that round's content wasn't "about" it. This is the exact
  failure the table exists to surface — it must render every round a Target is active, full stop,
  not just when convenient.
