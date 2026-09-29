# Decisions

`SKILL.md` is written for anyone using this format; it states the rules without saying who asked
for them or when. This file is the provenance those rules came out of — the original quotes and
the rulings that shaped them, in the order they happened. Round numbers (`rNN`) refer to a specific
session's own response count and won't mean anything to a fresh install; they're kept here only
because they're how each ruling was originally cited.

This project grew out of one person's (referred to below by name, since that's how the rulings
actually happened) long-running use of Claude Code across many sessions. If you're adopting this
format for your own use, none of the specifics below are binding on you — they're the reasoning
trail, not more rules.

## The register format itself

- **Lessons learned retired, replaced by Work done.** George: the old lessons-learned block
  "devolved into navel gazing." Replaced by cumulative, evidenced rows of what was actually done.
- **The clarification gate.** Guessing costs more than asking — a wrong guess executed is work to
  undo plus trust to rebuild; a question costs one round.
- **Background renders last, under Actions (r30).** It's status, not something to act on, so it
  must never push the to-do list further down the screen.
- **Targets dropped silently after intake once (r40).** Caught the same session the mechanism was
  built: rendered the round it was accepted, then silently gone the next round because that round's
  content wasn't "about" it. Fixed by requiring the table every round a Target is active.

## Work done

- **Terseness (r18).** George named the failure directly: terse rows read fine in the moment and
  become untrackable a day later, because the reasoning that made them make sense was never written
  down.
- **Evidence folded into the cell (r19).** Four columns of long prose was still too wide in a
  fixed-width terminal.

## Open questions

- **Title and question split into separate columns (r34).** George: so the titles form a scannable
  left edge instead of being buried at the head of a paragraph.
- **Sub-questions get lettered sub-lines (highbar session, r14).** George: "if there are
  sub-questions inside an entry put them on their own line, we can use carriage returns inside the
  columns ... then i can respond with lines specific to the question ala Q23c."
- **`<br>` doesn't render (r19).** Proved dead in the terminal actually being used; the `¶`
  sentinel and per-segment lines were the fix.

## Actions

- **Why and Recommendation split (r42).** George: "you're now merging why + recommendation? those
  should be two." They're different kinds of claim — situation versus opinion — and fusing them
  hides where the facts stop and the advice starts.
- **Terseness in Actions specifically (r41).** George: "you're now killing me with conciseness."
  Actions rows decay into fragments faster than Work-done rows because the context feels obvious
  to the model mid-session and isn't obvious to the reader, especially a week later.

## Background

- **What it's for (r31).** George's framing: the live waits that make a session wake up and jump
  ahead on its own — seeing a row means the session is parked and can be safely ignored until the
  thing fires.
- **Idle leftovers don't belong here.** The first version of this section listed them (a spawned
  stack nobody is using, a merged worktree) and that read as "the session is busy" when it wasn't —
  exactly backwards. They belong in an Action or a Work row instead.

## No bold inside register cells (r34)

George: bold inside Question and Action cells is hard to look at in the terminal, where the
renderer already separates rows well enough on its own.

## Threads

- **The model detects and numbers threads, not the user (r36).** Removes a step from every message
  and keeps numbering consistent.

## Answers — AW#

- **Table + prose shape (r38).**
- **The rendered "wide" shape (highbar session r11, 2026-09-22).** George: "answer: explanation,
  then the text below it. wide format vs columns. but the width of the answer should be constrained
  so it doesn't fill the whole screen. if there are specific sections to call out tufte-style then
  place them in a column to the right."
- **No column label in the terminal (r58).** George: "i built the format, i know what the columns
  mean" — position alone should carry meaning where the format's author already knows the shape.
- **The Asked-line requirement (2026-09-29).** George: "the answers section should also include the
  original question I asked — direct quote ideally, but okay to summarize it if it's a bit
  disjointed." Enforced by `check-response.py`'s `check_answers`, not just documented.

## The rendered layout (r54-r69)

- **Settled through a long design pass**, driven round by round by direct feedback on the rendered
  output.
- **Thread tag placement.** An earlier draft moved the thread tag to the trailing edge on Tufte
  grounds (meaning belongs at the left edge); George corrected it back to sitting second, right
  after the ID — it answers "which of my goals does this serve," which is exactly what gets scanned
  for, so it earns the prominent position.
- **Bold banned in every cell (r57).** Beyond legibility, a bold run renders wider than its plain
  equivalent and skews its own column and every column after it.

## TL;DR (r83)

- George's reason for wanting it: "that way i know whether or not to scroll back up." It's built to
  cover only the free-text prose at the top of a response — the one part with no row of its own,
  and so the one part with no other way to be found again.
- **Naming.** George introduced it as "a commentary at the bottom of the response of Key Points"
  and then said "in fact call that TL;DR" — the heading is `TL;DR`, but it was described
  conversationally as "Key Points" at least once.
- **It went missing before it was written down.** Built into the renderer at r83, never recorded in
  the contract, so sessions correctly following the written rules never produced one. Third time in
  one stretch of work the contract and its tooling drifted apart. The fix wasn't "document better,"
  it was: a rule that lives only in code is not part of the contract.

## Publishing: local register pages (2026-09-27)

- George, after trialling the pattern in one particular session: "this response format is working
  - do what needs to be done to make it consistent so all future sessions use it."
- **History, so nobody goes back (2026-09-26).** The register first moved from fixed-width terminal
  text to HTML, published as a hosted-artifact page republished in place each round. That lost the
  history — each republish overwrote the last round, so there was no way to look back. Local,
  per-round files fixed it.
- **Targets in the terminal too (Q100, 2026-09-26).** The guardrail that answers "are we still
  aimed at the thing" is worthless behind a click — if the page isn't open, the thing it exists to
  catch is exactly what's happened.
- **Evidence gets its own page column (2026-09-26).** Not a reversal of the r19 terminal rule —
  that rule was about what a fixed-width terminal can paint, and that constraint doesn't exist in
  HTML.
- **Section colour (2026-09-28).** George: "headers and sub-headers and tables should use colors
  gently to break up the text so it's not monotone." Confirmed the result a few rounds later:
  "coloring is good."
- **Custom terminal themes don't reach assistant output.** Tested directly (2026-09-21): theme
  tokens documented as covering table borders and body text changed neither, in the terminal
  actually used. The token reference lists nothing for table borders, header rows or cell text —
  theme tokens appear to cover the harness's own chrome, not rendered transcript content.

## Width (terminal rendering)

- **`<br>` and layout-fiddling alternatives (r19-r20).** Blank spacer rows and a separate mini-table
  per entry were both tried and both failed on the same ruling: "too much cognitive load." One
  aligned grid scans better than entries that must be reassembled by eye.
- **A six-column Actions table stopped rendering as a table at all (r16).** Observed directly, in
  the terminal actually used — it degraded into a run-on list. Fewer columns, not shorter cells,
  was the fix (r18): thin cells compress meaning past the point of being trackable over time.

## The new-round modal (2026-09-29)

The live register page originally reloaded itself silently the moment a newer round was published
— no warning, no at-a-glance signal, just the page changing under you mid-scroll. George: "how
about on refresh popping in a modal that says 'new content available, include the tl;dr' and a
button that's already selected so I can press enter to clear the modal." Built as a native
`<dialog>` with one autofocused button in a `<form method="dialog">`, so Enter submits it the
standard way with no custom keyboard handling needed.

Two follow-up rounds tuned it, both from direct feedback:

- **Spacing and backdrop, twice.** First: "put a bit more space between each tl;dr bullet and make
  the background more dark / transparent overlay — i want to still be able to see the title of the
  screen, but not get distracted by it." Then again: "more space between the tl;dr please, at least
  double."
- **The Escape bug.** George: "i want to be able to press escape and continue looking at the screen
  i was on, it should show that there's new content at the top of the page as before. as of now if
  i hit escape to close the modal it comes back in a few seconds." The cause was a leftover
  `shown = false` in the close handler that re-armed the dialog on every poll after a decline;
  removing it, and unhiding a persistent nav-bar badge instead, fixed both halves of the report.

## Section colour (2026-09-28)

Colours were spent in exactly five places per section (heading band, ID column, row hairline,
Evidence bar, Work-done summary row) rather than throughout, on the reasoning that colour should
mark *where* you are on the page, never *what* a row means.
