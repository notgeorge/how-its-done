#!/usr/bin/env python3
"""Check a drafted response against the response-format contract.

    python3 ~/.claude/skills/response-format/check-response.py draft.md
    python3 ~/.claude/skills/response-format/check-response.py draft.md --register <path>

Reads a drafted reply (markdown), parses its tables, and reports every way it
departs from SKILL.md. Exit 0 = clean, 1 = findings.

Why this exists: the contract is deterministic, so conformance is checkable, and
every rule below was added because it was BROKEN in a real round — r18 (compressed
cells), r19 (Evidence folded in), r30 (Background last), r34 (no bold in cells),
r38 (AW is one sentence), r40 (Targets dropped after intake), r41 (terseness in
Actions), r42 (Why and Recommendation fused). A rule with no round number behind it
is a guess and does not belong here.

The word bands are FLOORS AND CEILINGS, not targets. A cell inside its band is not
thereby good; a cell outside it is reliably bad. They are calibrated against the
worked examples in SKILL.md itself — the "Ran the guard on the 8020 stack…" row is
~55 words, the "Merge it — the spec change is…" recommendation is ~20.

Stdlib only, host-runnable: this checks the reply before it is sent, so it must not
need a container. (The container rule governs TAP's own scripts and tests, not this.)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- the contract, as data -------------------------------------------------

#: Section heading -> its position in the required render order.
ORDER = ["Targets", "Threads", "Answers", "Work done", "Open questions", "Actions", "Background"]

#: Per-cell word bands: (column index or name, low, high). Below low = compressed
#: past the point George can track it next week (r18). Above high = the wall of text
#: that trains him to skip the table.
BANDS = {
    "work.what": (40, 200),
    "actions.why": (35, 160),
    "actions.recommendation": (12, 90),
    "threads.description": (8, 70),
    "questions.question": (15, 110),
    "questions.matters": (10, 90),
    "answers.answer": (8, 45),
    "targets.hitwhen": (4, 30),
}

#: Titles are 4-8 words by the contract; allow 3-10 before complaining, since the
#: rule's intent is "enough to carry the substance, not a label", not a word game.
TITLE_BAND = (3, 10)

# "T4🔌" or "T17📐🥳" — number then glyphs, closed up (r58: one object, not a list of
# three tokens). A space is still accepted for older drafts; a bare glyph never is.
THREAD_TAG = re.compile(r"^T\d+\s*\S")
ACTION_ID = re.compile(r"^A\d+\s+·\s+r\d+$")  # "A3 · r7" — Actions carry A, never Q
QUESTION_ID = re.compile(r"^Q\d+\s+·\s+r\d+$")  # "Q7 · r14" — and questions never carry A
PLAIN_ID = re.compile(r"^(W\d+|AW\d+|X\d+|T\d+)$")
BOLD = re.compile(r"\*\*[^*]+\*\*")
PLACEHOLDER = re.compile(r"^\(?\s*(none|n/?a|tbd|-{1,3})\s*\)?\.?$", re.I)
#: The original question, quoted or summarized, as the first line under an Answer's table
#: (George, 2026-09-29: "the answers section should also include the original question I
#: asked — direct quote ideally, but okay to summarize it if it's a bit disjointed"). Shared
#: with render-register.py's `answer_blocks`, which is why it lives here and not there —
#: check-response.py has no reverse dependency on the renderer.
ASKED_RE = re.compile(r"^>\s*Asked:\s*(.+)$", re.I)


@dataclass
class Table:
    heading: str
    header: list[str]
    rows: list[list[str]]
    line: int


@dataclass
class Report:
    findings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def fail(self, where: str, msg: str) -> None:
        self.findings.append(f"{where}: {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)


#: The segment break inside a cell (highbar, r81): ` ¶ ` makes a sub-question start its
#: own line in its column, so George can answer Q23a separately from Q23b. It is a
#: sentinel, not content — it must never be counted as a word or the bands mis-measure
#: every cell that carries one, and a Q row with three sub-questions would read as three
#: words longer than it is.
SEGMENT = "¶"


def words(cell: str) -> int:
    text = cell.replace(SEGMENT, " ")
    text = re.sub(r"`[^`]*`", "x", text)  # a path counts as one word, not its slashes
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # link text, not the url
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def sentences(cell: str) -> int:
    text = re.sub(r"`[^`]*`", "x", cell)
    text = re.sub(r"\b(e\.g|i\.e|etc|vs|Dr|Mr|No)\.", r"\1", text)
    return len([s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()])


# --- parsing ---------------------------------------------------------------


def parse(md: str) -> tuple[list[str], list[Table]]:
    """Return (section headings in order, tables tagged with the heading above them)."""
    headings: list[str] = []
    tables: list[Table] = []
    current = "(preamble)"
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            current = line.lstrip("#").strip()
            headings.append(current)
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = split_row(line)
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            tables.append(Table(current, header, rows, i + 1))
            i = j
            continue
        i += 1
    return headings, tables


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def section_body(md: str, heading: str) -> str:
    """The raw text under `## <heading>`, up to the next `## `. Empty when absent.

    Added for render-artifact.py (2026-09-26). Sections whose content is NOT a well-formed
    table — `## Background` is one headerless row, `## TL;DR` is bare `- ` bullets — are
    invisible to `parse()`, which only registers a table once a `|---|` separator follows
    its first line. Both renderers need those sections, and both were about to grow their
    own `md.split("## ...")` to get them, which is how a second parser starts. The heading
    is matched ANCHORED to the start of a line: a bare substring search lands inside any
    cell that happens to name the section, which is exactly the bug r83's TL;DR block hit.
    """
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", md, re.M)
    if not m:
        return ""
    return re.split(r"^##\s", md[m.end():], maxsplit=1, flags=re.M)[0]


def find(tables: list[Table], name: str) -> Table | None:
    for t in tables:
        if t.heading.lower() == name.lower():
            return t
    return None


# --- checks ----------------------------------------------------------------


def check_tldr(md: str, tables: list[Table], rep: Report) -> None:
    """A substantive response ends with a TL;DR (r83). Silence here was the bug: the section
    lived in the renderer and not in SKILL.md, so drafts that followed the contract correctly
    produced none and nothing said so. Skipped for a trivial turn, which has no prose to
    summarise — judged by whether the draft carries the full register.

    KNOWN LIMIT, stated rather than left to be discovered: this asserts the section EXISTS.
    It cannot tell whether the bullets summarise the prose above them or merely repeat the
    Actions table, which is the whole point of the section and the thing that will decay.
    Presence is not correctness.

    That gap is the pattern this repo hit seven times in two days (demo-dev's framing,
    r89): a check that asserts STABILITY OF AN ARTEFACT where what was wanted is A PROPERTY
    OF THE OUTPUT. A snapshot says the SQL is unchanged, not that it filters retired rows;
    a ratchet says the error count is unchanged, not that it is accurate; this says a
    heading is present, not that what follows it is a summary. Stability is cheap to assert
    and nearly free to satisfy, which is why these accumulate — so when a green check here
    is read as "the TL;DR is good", it is being read for more than it says."""
    if not any(t.heading.lower() in {"work done", "actions"} for t in tables):
        return
    import re as _re

    if not _re.search(r"^## TL;DR\s*$", md, _re.M):
        rep.fail("TL;DR", "no `## TL;DR` section — a substantive response closes with one (r83)")


def check_no_bold_anywhere(tables: list[Table], rep: Report) -> None:
    """Bold is banned in EVERY cell, not just the ones r34 named (r57, George: "NEVER USE
    BOLD TEXT"). Two reasons now, and the second is mechanical: in the NBSP form a bold run
    can render wider than its plain equivalent, which skews the column it sits in and every
    column after it. A rule that was about legibility is now also about alignment."""
    for tb in tables:
        for row in tb.rows:
            for cell in row:
                if BOLD.search(cell):
                    rep.fail(f"{tb.heading}/{row[0]}", f"bold in a cell — never, in any column: {cell[:50]!r}")


def check_order(headings: list[str], rep: Report) -> None:
    present = [h for h in headings if h in ORDER]
    expected = [h for h in ORDER if h in present]
    if present != expected:
        rep.fail("order", f"sections are {present}, contract order is {expected} (r30: Background last)")


def check_band(rep: Report, where: str, key: str, cell: str) -> None:
    low, high = BANDS[key]
    n = words(cell)
    if n < low:
        rep.fail(where, f"{n} words, floor is {low} — compressed past trackable (r18/r41): {cell[:60]!r}")
    elif n > high:
        rep.fail(where, f"{n} words, ceiling is {high} — a wall of text in a terminal cell")


def check_no_bold(rep: Report, where: str, cell: str) -> None:
    if BOLD.search(cell):
        rep.fail(where, "bold inside a register cell (r34) — use plain text, backticks are fine")


def check_thread_tag(rep: Report, where: str, cell: str) -> None:
    if not cell.strip():
        rep.fail(where, "empty thread column — every register row carries T# plus its glyph")
    elif not THREAD_TAG.match(cell) and cell.strip() != "—":
        rep.fail(where, f"thread column is {cell!r} — must be 'T# <glyph>', not a bare emoji (Tagging rows)")


def check_threads(t: Table | None, rep: Report) -> None:
    if t is None:
        rep.fail("Threads", "missing — the Threads table is authoritative and renders EVERY round")
        return
    if len(t.header) != 4:
        rep.fail("Threads", f"{len(t.header)} columns, contract is 4 (T#, glyph, Title, Description)")
    for r in t.rows:
        rid = r[0]
        if not PLAIN_ID.match(rid):
            rep.fail("Threads", f"id {rid!r} is not a bare T#")
        if len(r) >= 4:
            check_band(rep, f"Threads/{rid} description", "threads.description", r[3])
            check_no_bold(rep, f"Threads/{rid}", r[3])


def check_targets(t: Table | None, register: Path | None, rep: Report) -> None:
    active = register_has_active_target(register) if register else None
    if t is None:
        if active:
            rep.fail("Targets", "missing, but the register lists an ACTIVE target — r40, the exact failure")
        elif active is None:
            rep.note("Targets table absent; no register given, so I could not check whether one is active")
        return
    if len(t.header) != 5:
        rep.fail("Targets", f"{len(t.header)} columns, contract is 5 (X#, smiley, Target, Hit when, Status)")
    for r in t.rows:
        if len(r) >= 4:
            check_band(rep, f"Targets/{r[0]} hit-when", "targets.hitwhen", r[3])


def register_has_active_target(register: Path) -> bool | None:
    try:
        text = register.read_text()
    except OSError:
        return None
    block = text.split("## Targets", 1)
    if len(block) < 2:
        return None
    body = block[1].split("\n## ", 1)[0]
    rows = [ln for ln in body.splitlines() if ln.strip().startswith(("|", "- X"))]
    return any("X" in ln and not PLACEHOLDER.match(ln.strip().lstrip("- ")) for ln in rows)


def check_answers(t: Table | None, md: str, rep: Report) -> None:
    if t is None:
        return
    if len(t.rows) > 1:
        rep.fail("Answers", f"{len(t.rows)} rows — one table per answer, never one table with several (r38)")
    for r in t.rows:
        if len(r) >= 3:
            check_band(rep, f"Answers/{r[0]}", "answers.answer", r[2])
            if sentences(r[2]) != 1:
                rep.fail(f"Answers/{r[0]}", f"{sentences(r[2])} sentences — the answer cell is ONE sentence (r38)")
            check_thread_tag(rep, f"Answers/{r[0]}", r[1])
    if t.rows and not find_asked(md, t):
        rep.fail(
            f"Answers/{t.rows[0][0]}",
            "no 'Asked:' line — the first line under the table must quote or summarize "
            "the original question (2026-09-29): `> Asked: \"...\"`",
        )


def find_asked(md: str, t: Table) -> str | None:
    """The `> Asked: ...` line directly under an Answer's table, if present. `t.line` is the
    separator row's index (see `parse`); the table's data rows occupy the `len(t.rows)`
    lines after it, so the first line of the explanation starts right after those."""
    lines = md.splitlines()
    i = t.line + 1 + len(t.rows)
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        m = ASKED_RE.match(lines[i].strip())
        if m:
            return m.group(1).strip()
    return None


def check_work(t: Table | None, md: str, rep: Report) -> None:
    if t is None:
        rep.note("no Work done table — fine only on a trivial turn or when nothing was done")
        return
    if len(t.header) != 4:
        rep.fail("Work done", f"{len(t.header)} columns, contract is 4 (ID, Thread, Title, What I did) — r19")
    # The summary moved BELOW the table at r70 and is written as a `> ` blockquote, which
    # is what render-register.py's summary_line() reads. This check still demanded a BOLD
    # line ABOVE the rows, so a correct r70 draft failed it — the same shape as the stale
    # THREAD_TAG regex, and found the same way: by someone finally running the checker.
    # Found by the highbar session, r79.
    #
    # Accept either placement, because old drafts carry the summary above; fail only when
    # there is no summary at all, which is the thing the rule was ever about.
    block = md.split("## Work done", 1)[1].split("\n## ", 1)[0] if "## Work done" in md else ""
    above = block.split("|", 1)[0]
    below = [ln for ln in block.splitlines() if ln.startswith(">") and ln.lstrip("> ").strip()]
    if not below and not BOLD.search(above):
        rep.fail("Work done", "no one-line summary — a `> ` line under the table (r70), or bold above it")
    for r in t.rows:
        rid = r[0]
        if not PLAIN_ID.match(rid):
            rep.fail("Work done", f"id {rid!r} is not a bare W#")
        if len(r) < 4:
            continue
        check_thread_tag(rep, f"Work done/{rid}", r[1])
        n = words(r[2])
        if not (TITLE_BAND[0] <= n <= TITLE_BAND[1]):
            rep.fail(f"Work done/{rid} title", f"{n} words, contract is 4-8 — not a label, not a sentence")
        check_band(rep, f"Work done/{rid}", "work.what", r[3])
        check_no_bold(rep, f"Work done/{rid}", r[3])
        if "Evidence:" not in r[3]:
            rep.fail(f"Work done/{rid}", "no 'Evidence:' closing line (r19) — say how you know")


def check_questions(t: Table | None, rep: Report) -> None:
    if t is None:
        return
    if not t.rows or all(PLACEHOLDER.match(c) for r in t.rows for c in r):
        rep.fail("Open questions", "empty or placeholder table — omit the section entirely when none")
        return
    if len(t.header) != 5:
        rep.fail("Open questions", f"{len(t.header)} columns, contract is 5 (ID, Thread, ?, ??, Why it matters)")
    for r in t.rows:
        if not QUESTION_ID.match(r[0]):
            rep.fail("Open questions", f"id {r[0]!r} must be a Q with its raised round, e.g. 'Q7 · r14'")
        if len(r) >= 5:
            check_thread_tag(rep, f"Open questions/{r[0]}", r[1])
            check_band(rep, f"Open questions/{r[0]} question", "questions.question", r[3])
            check_band(rep, f"Open questions/{r[0]} why-it-matters", "questions.matters", r[4])


def check_actions(t: Table | None, rep: Report) -> None:
    if t is None:
        rep.note("no Actions table — fine when the user has nothing to do")
        return
    if len(t.header) != 5:
        rep.fail(
            "Actions",
            f"{len(t.header)} columns, contract is 5 (ID, Thread, Action, Why, Recommendation). "
            "Four usually means Why and Recommendation were fused into one cell — r42.",
        )
    for r in t.rows:
        rid = r[0]
        if not ACTION_ID.match(rid):
            # r54, George: a Q row was carried in the Actions table. Different kinds of item —
            # a question asks him to decide, an action asks him to do — so a Q in here is a
            # category error, not a formatting slip, and it hides the question from its own table.
            rep.fail("Actions", f"id {rid!r} is not an A# — a Q belongs in Open questions, not here")
        if len(r) < 5:
            continue
        check_thread_tag(rep, f"Actions/{rid}", r[1])
        check_band(rep, f"Actions/{rid} why", "actions.why", r[3])
        check_band(rep, f"Actions/{rid} recommendation", "actions.recommendation", r[4])
        check_no_bold(rep, f"Actions/{rid}", r[3])
        check_no_bold(rep, f"Actions/{rid}", r[4])
        if sentences(r[4]) < 2 and words(r[4]) < 20:
            rep.fail(f"Actions/{rid} recommendation", "a verdict with no reason — he must be able to argue with it")


def check_background(t: Table | None, rep: Report) -> None:
    if t is None:
        return
    if len(t.rows) > 1:
        rep.fail("Background", f"{len(t.rows)} rows — Background is ONE row, one cell per live wait")
    for r in t.rows:
        for cell in r[1:] if len(r) > 1 else r:
            if not re.search(r"\d|~|when|expire|fire|min|sec|hour", cell, re.I):
                rep.fail("Background", f"no firing time in {cell[:50]!r} — the number is the whole point")
        joined = " ".join(r).lower()
        for idle in ("worktree", "branch", "stack is up", "leftover", "despawn"):
            if idle in joined:
                rep.fail("Background", f"{idle!r} looks like an idle leftover, not a live wait — it belongs in an Action")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="check a drafted response against the response-format contract")
    ap.add_argument("draft", type=Path, help="the drafted reply, as markdown")
    ap.add_argument("--register", type=Path, default=None, help="response-register.md, to cross-check active Targets")
    ap.add_argument("--quiet", action="store_true", help="print findings only")
    ap.add_argument("--render", metavar="SECTION", help="render one section fixed-width instead of checking")
    ap.add_argument("--width", type=int, default=250, help="display columns for --render (default 250)")
    ap.add_argument("--rule", choices=("subtle", "none", "line"), default="none", help="row separator style")
    ap.add_argument("--form", choices=("nbsp", "fence"), default="nbsp", help="nbsp keeps markdown live")
    ap.add_argument("--header", action="store_true", help="emit the column header row (off by default)")
    ap.add_argument("--note", default="", help="text for the green half of the section bar")
    ap.add_argument("--divider", metavar="LABEL", help="print a decorator-grey section rule and exit")
    ap.add_argument("--max-col", type=int, default=0, help="cap any single column, so long cells stack instead of running")
    args = ap.parse_args(argv)

    md = args.draft.read_text()
    headings, tables = parse(md)
    rep = Report()

    if args.divider:
        print(section_bar(args.divider, args.width, note=args.note))
        return 0

    if args.render:
        t = find(tables, args.render)
        if t is None:
            print(f"no section named {args.render!r} in {args.draft}")
            return 1
        if args.form == "nbsp":
            print(render_nbsp(t, args.width, args.max_col, header=args.header))
        else:
            print(render_table(t, args.width, args.rule, args.max_col))
        return 0

    check_order(headings, rep)
    check_no_bold_anywhere(tables, rep)
    check_tldr(md, tables, rep)
    check_targets(find(tables, "Targets"), args.register, rep)
    check_threads(find(tables, "Threads"), rep)
    for t in tables:
        if t.header and t.header[0].startswith("AW"):
            check_answers(t, md, rep)
    check_work(find(tables, "Work done"), md, rep)
    check_questions(find(tables, "Open questions"), rep)
    check_actions(find(tables, "Actions"), rep)
    bg = find(tables, "Background") or next((t for t in tables if t.header and t.header[0] == "Background"), None)
    check_background(bg, rep)

    if rep.findings:
        print(f"{len(rep.findings)} finding(s):\n")
        for f in rep.findings:
            print(f"  ✗ {f}")
    else:
        print("clean — no contract violations found")
    if rep.notes and not args.quiet:
        print("\nnotes (not failures):")
        for n in rep.notes:
            print(f"  · {n}")
    return 1 if rep.findings else 0




# --- fixed-width rendering (r44) -------------------------------------------
#
# Markdown table cells cannot wrap: a long cell becomes one very long line, and every
# rationing of words so far has been fighting that. A preformatted block CAN wrap, so the
# cell holds real line breaks and the column stays narrow. The trade is that nothing
# reflows it — rendered wider than the terminal, it hard-wraps mid-column and reads worse
# than the markdown did. Hence --width, measured rather than guessed.

import textwrap
import unicodedata

ZERO_WIDTH = {"Mn", "Me", "Cf"}


def cell_width(text: str) -> int:
    """Display columns, not characters. Emoji and CJK occupy two; combining marks,
    variation selectors and ZWJ occupy none. Padding by len() misaligns every row that
    carries a glyph, which is every row in this register."""
    total = 0
    for ch in text:
        if unicodedata.category(ch) in ZERO_WIDTH or ch == "‍":
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - cell_width(text))


def strip_markup(text: str) -> str:
    """Drop inline markdown that a fenced block renders literally rather than applying.

    Backticks are the big one, and losing them costs nothing: the whole block is already
    monospace, so a code span was only ever asking for the font the block now guarantees.
    Bold is already banned inside cells (r34). A link keeps its label and loses its URL,
    which is the one real loss — put bare URLs in the prose above, not in a cell.
    """
    text = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    # Collapse the whole ` ¶ ` token, not just the glyph: dropping the character alone
    # leaves both of its spaces behind, so a cell measured one column too wide per
    # sub-question. Caught by asserting display_width is IDENTICAL with and without the
    # sentinel rather than merely close.
    text = re.sub(rf"\s*{re.escape(SEGMENT)}\s*", " ", text)
    return text.replace("`", "")


def wrap_cell(text: str, width: int) -> list[str]:
    text = strip_markup(text)
    if not text.strip():
        return [""]
    out: list[str] = []
    for para in text.split("\n"):
        wrapped = textwrap.wrap(para, width, break_long_words=False, break_on_hyphens=False) or [""]
        # textwrap counts characters; re-measure and split again where glyphs made a line too wide
        for line in wrapped:
            while cell_width(line) > width:
                cut = len(line)
                while cut > 1 and cell_width(line[:cut]) > width:
                    cut -= 1
                out.append(line[:cut])
                line = line[cut:].lstrip()
            out.append(line)
    return out


def allocate(header: list[str], rows: list[list[str]], total: int, gap: int = 3, cap: int = 0) -> list[int]:
    """Give every column what it needs up to its natural width, then share the remainder
    among the columns that still want more, proportional to how much they want."""
    n = len(header)
    budget = total - gap * (n - 1)
    natural = [max(cell_width(header[i]), *(cell_width(r[i]) for r in rows)) if rows else cell_width(header[i]) for i in range(n)]
    # A single column handed 200 columns is a long line wearing a table's clothes. Capping it is
    # what actually buys the line breaks inside a cell — the whole reason for rendering this way.
    if cap:
        natural = [min(nat, cap) for nat in natural]
    floor = [min(nat, 12) for nat in natural]
    if sum(natural) <= budget:
        return natural
    spare = budget - sum(floor)
    want = [nat - f for nat, f in zip(natural, floor)]
    scale = spare / sum(want) if sum(want) > 0 else 0
    return [f + int(w * scale) for f, w in zip(floor, want)]


def section_bar(label: str, total: int, note: str = "", labels: list[str] | None = None,
                widths: list[int] | None = None, gap: int = 2) -> str:
    """The section rule, in TWO colours.

    `@__Label____` lexes as a python decorator (grey in George's theme); everything after
    `#` lexes as a comment (bright green). One line, two colours, which is what breaks the
    rule up instead of leaving a flat bar (r58). The comment half carries either the
    Work-done summary sentence or the column labels that are not self-evident.
    """
    head = f"@__{label.replace(' ', '_')}__"
    if labels and widths:
        # Place each label over the column it names, by padding to that column's offset.
        line = head
        offset = 0
        for i, (lab, w) in enumerate(zip(labels, widths)):
            if not lab:
                offset += w + gap
                continue
            start = offset + (0 if not line.startswith(head) else 0)
            pad_to = max(len(line) + 2, start)
            line = line.ljust(pad_to - 2, "_") + ("  # " if "#" not in line else "  ")
            line += lab
            offset += w + gap
        return line.ljust(total, "_") if "#" not in line else line
    if note:
        bar = head.ljust(max(len(head), total - len(note) - 4), "_")
        return f"{bar}  # {note}"
    return head + "_" * max(0, total - cell_width(head))


def divider(label: str, total: int) -> str:
    """A section rule that lexes as a python decorator.

    George's theme paints comments bright green and decorators grey (probed r48-r49), so the
    grey rule has to BE a decorator: `@` plus an identifier. Underscores are identifier
    characters, so `@__Actions_____` is both a legible label and a valid decorator token.
    """
    head = f"@__{label.replace(' ', '_')}__"
    return head + "_" * max(0, total - cell_width(head))


def render_table(t: Table, total: int, rule: str = "subtle", cap: int = 0) -> str:
    widths = allocate(t.header, t.rows, total, cap=cap)
    gap = "   "
    lines: list[str] = []
    lines.append(gap.join(pad(h.upper(), w) for h, w in zip(t.header, widths)).rstrip())
    if rule != "none":
        lines.append(gap.join("─" * w for w in widths))
    for i, row in enumerate(t.rows):
        if i and rule == "subtle":
            lines.append(gap.join("·" * w for w in widths))
        elif i and rule == "none":
            lines.append("")
        stacks = [wrap_cell(c, w) for c, w in zip(row, widths)]
        for line_no in range(max(len(s) for s in stacks)):
            cells = [s[line_no] if line_no < len(s) else "" for s in stacks]
            lines.append(gap.join(pad(c, w) for c, w in zip(cells, widths)).rstrip())
    return "\n".join(lines)




# --- NBSP rendering: columns AND live markdown (r57) -----------------------
#
# A fenced block holds columns but renders no markdown, so backticks, bold and links
# print as characters. George asked whether the columns could be faked outside a fence
# instead. They can, and all three things it depends on were probed and hold (r57):
# non-breaking spaces survive markdown's whitespace collapsing, two trailing spaces are
# honoured as a hard line break, and inline markdown stays live.
#
# The catch is measurement. A cell's SOURCE is `foo` (7 chars) and its DISPLAY is foo
# (3). Wrapping and padding must both count display width while emitting source, or
# every cell containing a code span pushes its neighbour out of line.

NBSP = " "


def display_width(text: str) -> int:
    """Columns the reader sees: markup is measured at zero because it renders as nothing."""
    return cell_width(strip_markup(text))


def wrap_markdown(text: str, width: int) -> list[str]:
    """Greedy wrap that measures the rendered text and emits the source text."""
    if not text.strip():
        return [""]
    lines: list[str] = []
    current: list[str] = []
    used = 0
    for token in text.split():
        w = display_width(token)
        if current and used + 1 + w > width:
            lines.append(" ".join(current))
            current, used = [token], w
        else:
            used += (1 if current else 0) + w
            current.append(token)
    if current:
        lines.append(" ".join(current))
    return lines


def pad_markdown(text: str, width: int) -> str:
    return text + NBSP * max(0, width - display_width(text))


def nbsp_widths(t: Table, total: int, cap: int = 0, gap: int = 5) -> list[int]:
    n = len(t.header)
    natural = [
        max([display_width(t.header[i])] + [display_width(r[i]) for r in t.rows if i < len(r)])
        for i in range(n)
    ]
    if cap:
        natural = [min(w, cap) for w in natural]
    budget = total - gap * (n - 1)
    if sum(natural) > budget:
        floor = [min(w, 10) for w in natural]
        spare = budget - sum(floor)
        want = [w - f for w, f in zip(natural, floor)]
        scale = spare / sum(want) if sum(want) > 0 else 0
        natural = [f + int(w * scale) for f, w in zip(floor, want)]
    return natural


def render_nbsp(t: Table, total: int, cap: int = 0, gap: int = 5, header: bool = False) -> str:
    """The register as aligned columns with markdown still live. No fence.

    Header row off by default (r58, George: "i built the format, i know what the columns
    mean"). The two columns that are NOT self-evident — Why and Recommendation — get their
    labels on the section bar instead, where they cost no row."""
    natural = nbsp_widths(t, total, cap, gap)
    sep = NBSP * gap
    out: list[str] = []
    if header:
        out.append(sep.join(pad_markdown(h.upper(), w) for h, w in zip(t.header, natural)).rstrip())
    for row in t.rows:
        stacks = [wrap_markdown(c, w) for c, w in zip(row, natural)]
        for i in range(max(len(s) for s in stacks)):
            cells = [s[i] if i < len(s) else "" for s in stacks]
            out.append(sep.join(pad_markdown(c, w) for c, w in zip(cells, natural)).rstrip())
        out.append("")
    return "  \n".join(out).rstrip()


if __name__ == "__main__":
    raise SystemExit(main())
