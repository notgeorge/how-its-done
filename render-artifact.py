#!/usr/bin/env python3
"""Render a response register as an Artifact page body, plus a terminal pointer into it.

    python3 render-artifact.py draft.md --html out.html   # the artifact body
    python3 render-artifact.py draft.md --terminal        # TL;DR + a one-line index

README — the split, and why there are now two renderers
-------------------------------------------------------
`render-register.py` renders the register for GEORGE'S TERMINAL: fixed-width NBSP
columns, hard breaks, one 200-column grid. That form exists because a terminal has no
layout engine — every affordance has to be bought with spaces.

This renders the SAME PARSE for a published page, where a layout engine is available:
real margin notes, a 65ch measure on the prose cells, a grid that stacks at 400px.
It does not replace the text renderer and does not touch it. `--terminal` here is NOT
the text renderer either — it prints the TL;DR and a bare index (identifier, glyphs,
title) so George can find a row in the page. Bodies, Why and Recommendation live on the
page; the terminal carries the pointer.

ONE PARSER UNDER BOTH. `check-response.py` owns the parse (`parse`, `split_row`,
`section_body`, the width/markup primitives) and `render-register.py` owns the two
register-specific parses that were already written there (`answer_blocks`, `split_tail`,
`round_of`, `summary_line`). Both are imported, neither is reimplemented. Contract
validation stays with `render-register.py --check`; nothing here judges a draft, but
nothing here drops a section either — an unrecognised heading is passed through
visibly, the same rule the text renderer follows.

SKILL.md is the contract this expresses. Section order, column meanings, the ¶ break,
the `Evidence:` closing line, the `> ` sidenote, `⚠️` as the unmapped-Target warning:
all of it is SKILL.md's, and where this page and that file disagree, that file wins.

Stdlib only, host-runnable — this renders a reply before it is sent.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import re
import sys
import unicodedata
from pathlib import Path

_HERE = Path(__file__).parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cr = _load("_cr", "check-response.py")        # the parser and the width primitives
_rr = _load("_rr", "render-register.py")       # answer_blocks, split_tail, round_of, summary_line

SEGMENT = _cr.SEGMENT

#: Contract order (SKILL.md § Render order), with TL;DR last (r83).
ORDER = ["Targets", "Threads", "Answers", "Work done", "Open questions", "Actions", "Background", "TL;DR"]

#: The one column label that survives into the render (r58). It rides the section rule,
#: not a header row, exactly as it does in the terminal form.
TRAILING_LABEL = {"actions": "Recommendation"}

#: `⚠️` in a thread's glyph cell means the thread traces to NO active Target (SKILL.md
#: § Tagging Threads with a Target). It is a deliberate signal, so the page has to make it
#: legible as one — hence a class and a hover title rather than just an emoji in a cell.
UNMAPPED = "⚠"
UNMAPPED_NOTE = "not mapped to any active Target"


# --- inline markdown -------------------------------------------------------
#
# Escape FIRST, then mark up: the draft carries backticks, angle brackets, ampersands and
# quotes as content, and a converter that marks up before escaping will eat its own tags.
# Code spans are cut out before bold/italic run, so `**` inside a path stays a path.

_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_WIKI = re.compile(r"\[\[([^\]]+)\]\]")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITAL = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    """Draft markdown to HTML, code spans protected from the rest."""
    parts: list[str] = []
    pos = 0
    for m in _CODE.finditer(text):
        parts.append(_inline_plain(text[pos:m.start()]))
        parts.append(f"<code>{esc(m.group(1))}</code>")
        pos = m.end()
    parts.append(_inline_plain(text[pos:]))
    return "".join(parts)


def _inline_plain(text: str) -> str:
    out = esc(text)
    out = _WIKI.sub(lambda m: f'<span class="wiki">{m.group(1)}</span>', out)
    out = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    out = _ITAL.sub(r"<em>\1</em>", out)
    return out


def segments(cell: str) -> list[str]:
    """` ¶ ` is a hard break between sub-parts of a cell (r81) — a real break here, not the
    blank-line approximation a terminal has to use.

    The split SKIPS any pilcrow inside a code span, and that is a bug fix, not a licence.
    The contract reserves `¶` as the break and says a cell needing a literal pilcrow cannot
    have one; a draft that WRITES ABOUT the sentinel (`` `¶` stays reserved ``) is quoting it,
    not using it. Splitting blind cut that code span in half, so the opening backtick closed
    the Evidence paragraph and the remaining half of the sentence escaped the box entirely —
    which is what George saw. The cause was ordering: the split ran before inline-markdown
    conversion, so by the time `inline()` looked for a closing backtick it was in another
    block. Fixing the symptom would have meant re-joining HTML; fixing the cause means the
    splitter respects the one construct that can contain the sentinel harmlessly.

    NOTE a deliberate divergence: `render-register.py` splits unconditionally, so the same
    cell grows one spurious blank line in the terminal. I did not change it — its output is
    frozen by this task — and it is worth knowing the two forms differ here.
    """
    out: list[str] = []
    buf: list[str] = []
    in_code = False
    for ch in cell:
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == SEGMENT and not in_code:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


#: A lettered sub-question opening a segment — `Q99c`, `Q90b-bis`, `Q23a`. George answers
#: these line by line, so the label is the thing his eye lands on and gets the utility face.
#
# The lookahead is load-bearing: `Q99b's direction is implemented` OPENS with an identifier
# and is not a label, it is a possessive. Without it the apostrophe-s was left stranded at
# the head of the paragraph. A label is the identifier and then a break — never the
# identifier glued to more word.
_SUBID = re.compile(r"^((?:AW|Q|A|W|X)\d+[a-z](?:-[a-z]+)?)[.:]?(?=\s|$)\s*")


def body_html(cell: str, *, subids: bool = False) -> str:
    """A long register cell as prose blocks, one per ` ¶ ` segment."""
    return "".join(b for b in (_para(seg, subids) for seg in segments(cell) or [""]) if b)


def split_evidence(cell: str) -> tuple[str, str]:
    """Return (the description, the Evidence line) as separate HTML — Evidence gets its own
    COLUMN in Work done, right of the description.

    This diverges from SKILL.md's r19, which folded Evidence into the cell, and the reason
    the divergence is legitimate is in r19's own reasoning: four columns of long prose was
    too wide IN A FIXED-WIDTH TERMINAL. That constraint is the whole argument, and it does
    not exist on a page — there is room, and a column of proof beside the claim is easier to
    check than a footing buried at the end of a paragraph. So the text renderer keeps the
    folded form and this one splits, deliberately (ruled by George after reading the page).
    """
    segs = segments(cell) or [""]
    body: list[str] = []
    ev = ""
    for seg in segs:
        if "Evidence:" in seg:
            head, _, tail = seg.rpartition("Evidence:")
            if head.strip():
                body.append(_para(head.strip(), False))
            ev = inline(tail.strip())
            continue
        body.append(_para(seg, False))
    return "".join(b for b in body if b), ev


def _para(seg: str, subids: bool) -> str:
    if not seg:
        return ""
    if subids:
        m = _SUBID.match(seg)
        if m:
            rest = seg[m.end():]
            return f'<p><span class="subid">{esc(m.group(1))}</span>{inline(rest)}</p>'
    return f"<p>{inline(seg)}</p>"


def cell(row: list[str], i: int) -> str:
    return row[i].strip() if i < len(row) else ""


# --- the glyph legend: every glyph is a link to the row that defines it -----
#
# The glyphs were already DATA (which line of work, which aim). Making each one an anchor to
# its defining row is the cheapest possible upgrade of that: `T3 🌙😎` on a Work row now
# answers "which thread" and "which target" by going there, with no extra ink on the page.
#
# UNFORMATTED, George's word and the constraint that matters: no underline, no link colour,
# no visited state. The glyph must look exactly as it did before. A focus ring is the one
# visible affordance, because a link nobody can reach by keyboard is not a link, and each
# carries a title/aria-label naming its destination — an emoji is not an accessible name.


def clusters(text: str) -> list[str]:
    """Split a glyph run into individual glyphs. `🧹⚠️` is TWO glyphs and four code points:
    iterating characters would link a variation selector on its own and split the warning
    sign from the mark that makes it an emoji."""
    out: list[str] = []
    for ch in text:
        joined = bool(out) and (
            unicodedata.category(ch) in _cr.ZERO_WIDTH
            or ch in "\ufe0f\u200d"
            or out[-1].endswith("\u200d")
        )
        if joined:
            out[-1] += ch
        else:
            out.append(ch)
    return [c for c in out if c.strip()]


class Legend:
    """Glyph -> the row that defines it, read from the Targets and Threads tables.

    Built from the same parse as everything else: the Threads table is authoritative for
    thread glyphs (its FIRST glyph is the thread's own; anything after is a Target's smiley
    or the `⚠️` warning), and the Targets table is authoritative for smileys."""

    def __init__(self, tables) -> None:
        self.thread: dict[str, tuple[str, str]] = {}
        self.target: dict[str, tuple[str, str]] = {}
        self.threads: list[tuple[str, str, str]] = []
        tt = _cr.find(tables, "Targets")
        for r in (tt.rows if tt else []):
            xid, _t = id_cell(cell(r, 0))
            for g in clusters(cell(r, 1)):
                self.target.setdefault(g, (xid, _plain(cell(r, 2))))
        th = _cr.find(tables, "Threads")
        for r in (th.rows if th else []):
            tid, _t = id_cell(cell(r, 0))
            gl = clusters(cell(r, 1))
            own = gl[0] if gl else ""
            title = _plain(cell(r, 2))
            if own:
                self.thread.setdefault(own, (tid, title))
            self.threads.append((tid, own, title))


#: Set once per render. The section renderers are leaf functions called in one pass from
#: render_html, so threading a Legend through every signature buys nothing over this.
_LEGEND: Legend | None = None


def glyph_run(glyphs: str, *, skip: str = "") -> str:
    """The glyph run as links, except `skip` (a defining row does not link to itself) and
    `⚠️`, which points at nothing by definition — it is the absence of a Target."""
    out: list[str] = []
    for g in clusters(glyphs):
        dest = label = ""
        if _LEGEND and g != skip:
            if g in _LEGEND.thread:
                tid, title = _LEGEND.thread[g]
                dest, label = f"thread-{tid}", f"Thread {tid} — {title}"
            elif g in _LEGEND.target:
                xid, title = _LEGEND.target[g]
                dest, label = f"target-{xid}", f"Target {xid} — {title}"
        if dest:
            out.append(
                f'<a class="glyphlink" href="#{esc(dest)}" title="{esc(label)}" '
                f'aria-label="{esc(label)}">{esc(g)}</a>'
            )
        elif UNMAPPED in g:
            out.append(f'<span class="unmapped" title="{esc(UNMAPPED_NOTE)}" '
                       f'aria-label="{esc(UNMAPPED_NOTE)}">{esc(g)}</span>')
        else:
            out.append(esc(g))
    return "".join(out)


def thread_of(tag: str) -> str:
    m = re.match(r"^(T\d+)\b", tag.strip())
    return m.group(1) if m else ""


# --- the thread / target glyph column --------------------------------------


def thread_cell(tag: str) -> str:
    """`T1 🧪😎` — the number George types, then the glyphs he scans for. Its own narrow
    aligned column, never floating in the text: the glyphs are DATA (which line of work,
    which aim), and the second one's absence is the drift signal."""
    tag = tag.strip()
    if not tag:
        return '<td class="thread"></td>'
    m = re.match(r"^(T\d+)\s*(.*)$", tag)
    num, glyphs = (m.group(1), m.group(2).strip()) if m else ("", tag)
    warn = UNMAPPED in glyphs
    classes = "thread warn" if warn else "thread"
    inner = f'<span class="tnum">{esc(num)}</span>' if num else ""
    if glyphs:
        inner += f'<span class="glyph">{glyph_run(glyphs)}</span>'
    return f'<td class="{classes}">{inner}</td>'


def id_cell(rid: str) -> tuple[str, str]:
    """`A48 · r61` splits into the scan-edge identifier and the trailing round stamp."""
    left, tail = _rr.split_tail(rid)
    return left, tail


def round_cell(tail: str) -> str:
    """The round trails the row as a quiet stamp, not a headed column — it is the age
    signal and George never types it."""
    return f'<td class="round">{esc(tail)}</td>' if tail else '<td class="round"></td>'


# --- sections --------------------------------------------------------------


def section_open(name: str, trailing: str = "") -> str:
    label = trailing or TRAILING_LABEL.get(name.lower(), "")
    trail = f'<span class="rulelabel">{esc(label)}</span>' if label else ""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (
        f'<section class="sec" id="{slug}">'
        f'<h2 class="sechead"><span class="secname">{esc(name)}</span>'
        f'<span class="hairline" aria-hidden="true"></span>{trail}</h2>'
    )


def targets_html(t) -> str:
    """X#, smiley, Target, Hit when, Status. `Hit when` is the falsifiable test agreed at
    intake, so it is set apart rather than run in as a fourth sentence — the whole point of
    a Target is that it can be missed."""
    out = [section_open("Targets"), '<div class="tablewrap"><table class="reg targets">']
    for r in t.rows:
        rid, tail = id_cell(cell(r, 0))
        smiley = cell(r, 1)
        out.append(
            f'<tr id="target-{esc(rid)}">'
            f'<td class="id"><span class="rid">{esc(rid)}</span></td>'
            f'<td class="thread"><span class="glyph">{glyph_run(smiley, skip=smiley.strip())}</span></td>'
            f'<td class="title" data-label="Target">{inline(cell(r, 2))}</td>'
            f'<td class="body hitwhen" data-label="Hit when">'
            f'<span class="hwlabel">Hit when</span>{body_html(cell(r, 3))}</td>'
            f'<td class="status" data-label="Status">{inline(cell(r, 4))}</td>'
            f"{round_cell(tail)}"
            "</tr>"
        )
    out.append("</table></div></section>")
    return "".join(out)


def threads_html(t) -> str:
    """The Threads table is both the register's index of live work AND the page's filter.

    It renders all of its rows always, even while a filter is active, because it is the
    control: hiding the unselected rows would leave nothing to switch to."""
    out = [section_open("Threads"), '<div class="tablewrap"><table class="reg threads">']
    for r in t.rows:
        rid, tail = id_cell(cell(r, 0))
        glyphs = cell(r, 1)
        warn = UNMAPPED in glyphs
        own = (clusters(glyphs) or [""])[0]
        # The accessible control is a real button wearing the title's own type — not a
        # `tabindex` and a keydown handler bolted to a `<tr>`. Enter, Space, the focus ring
        # and the accessible name all come for free, and `aria-pressed` carries the state.
        pick = (
            f'<button type="button" class="threadpick" id="pick-{esc(rid)}" '
            f'data-scope="{esc(rid)}" aria-pressed="false">{inline(cell(r, 2))}</button>'
        )
        out.append(
            f'<tr id="thread-{esc(rid)}" data-thread="{esc(rid)}" data-control="scope" '
            f'class="threadrow{" warnrow" if warn else ""}">'
            f'<td class="id"><span class="rid">{esc(rid)}</span></td>'
            f'<td class="thread{" warn" if warn else ""}">'
            f'<span class="glyph">{glyph_run(glyphs, skip=own)}</span></td>'
            f'<td class="title" data-label="Thread">{pick}</td>'
            f'<td class="body" data-label="Description">{body_html(cell(r, 3))}</td>'
            f"{round_cell(tail)}"
            "</tr>"
        )
    out.append("</table></div>")
    # Empty in the markup and filled by the script: with JS off there is no control, so a
    # printed "click a thread" hint would be a lie about a page that cannot do it.
    out.append('<p class="filterstatus" id="filter-status" role="status"></p>')
    out.append("</section>")
    return "".join(out)


def answers_html(md: str) -> str:
    """The verdict is the headline; the reasoning is prose; the call-outs are margin notes.

    This is the one section that is deliberately NOT a grid (ruled highbar r11). On a page
    the sidenote can finally be a true margin note level with its paragraph, which is what
    the terminal form was approximating with a 46-column right gutter."""
    out = [section_open("Answers")]
    for r, question, paras in _rr.answer_blocks(md):
        rid, tail = id_cell(cell(r, 0))
        tag = cell(r, 1)
        out.append(f'<article class="answer" data-thread="{esc(thread_of(tag))}">')
        out.append(
            '<div class="ahead">'
            f'<span class="rid">{esc(rid)}</span>'
            f'<span class="athread"><span class="tnum">{esc(thread_of(tag))}</span>'
            f'{glyph_run(re.sub(r"^T\d+\s*", "", tag))}</span>'
            f'<span class="averdict">{inline(cell(r, 2))}</span>'
            + (f'<span class="around">{esc(tail)}</span>' if tail else "")
            + "</div>"
        )
        if question:
            # George, 2026-09-29: the answer's own question, quoted or summarized, "direct
            # quote ideally" — set apart from the reasoning below it, not folded into the
            # first paragraph, so a reader can tell what was asked from what is argued. No
            # added quote glyphs: the draft's own `> Asked: "..."` already carries them for
            # a direct quote, and adding more would double them up.
            out.append(
                f'<p class="asked"><span class="asklabel">Asked</span>'
                f'<span class="askq">{inline(question)}</span></p>'
            )
        for para, note in paras:
            out.append('<div class="pair">')
            out.append(f'<div class="para">{_answer_para(para)}</div>')
            if note:
                out.append(f'<aside class="side">{inline(note)}</aside>')
            else:
                out.append('<aside class="side empty" aria-hidden="true"></aside>')
            out.append("</div>")
        out.append("</article>")
    out.append("</section>")
    return "".join(out)


def _answer_para(lines: list[str]) -> str:
    """Consecutive plain lines are one paragraph; a `- ` line starts a bullet. Same reading
    of the draft as the terminal renderer, so the two cannot disagree about what a
    paragraph is."""
    items: list[tuple[bool, str]] = []
    for ln in lines:
        bullet = ln.startswith(("- ", "* "))
        if bullet:
            items.append((True, ln[2:].strip()))
        elif items and not items[-1][0]:
            items[-1] = (False, items[-1][1] + " " + ln)
        else:
            items.append((False, ln))
    out: list[str] = []
    i = 0
    while i < len(items):
        if items[i][0]:
            lis = []
            while i < len(items) and items[i][0]:
                lis.append(f"<li>{inline(items[i][1])}</li>")
                i += 1
            out.append("<ul>" + "".join(lis) + "</ul>")
        else:
            out.append(f"<p>{inline(items[i][1])}</p>")
            i += 1
    return "".join(out)


def work_html(t, md: str) -> str:
    out = [
        section_open("Work done", trailing="Evidence"),
        '<div class="tablewrap"><table class="reg work">',
        '<colgroup><col class="c-id"><col class="c-thread"><col class="c-title">'
        '<col class="c-body"><col class="c-ev"><col class="c-round"></colgroup>',
    ]
    for r in sorted(t.rows, key=lambda r: _rr.round_of(cell(r, 0))):
        rid, tail = id_cell(cell(r, 0))
        did, ev = split_evidence(cell(r, 3))
        out.append(
            f'<tr data-thread="{esc(thread_of(cell(r, 1)))}">'
            f'<td class="id"><span class="rid">{esc(rid)}</span></td>'
            f"{thread_cell(cell(r, 1))}"
            f'<td class="title" data-label="Title">{inline(cell(r, 2))}</td>'
            f'<td class="body" data-label="What I did">{did}</td>'
            f'<td class="body evidence" data-label="Evidence">{ev}</td>'
            f"{round_cell(tail)}"
            "</tr>"
        )
    # The summary sits BELOW the rows (r70): it is what George glances back to, and a glance
    # back lands after the reading. It SPANS every column, because it is the through-line of
    # the whole table and not a value belonging to any one of them — as a floating paragraph
    # under the table it read as one more cell, which is the opposite of what it says.
    summary = _rr.summary_line(md)
    if summary:
        out.append(
            '<tr class="wdsrow"><td class="wds" colspan="6">'
            f'<span class="wdslabel">WDS</span>{inline(summary)}</td></tr>'
        )
    out.append("</table></div></section>")
    return "".join(out)


def questions_html(t) -> str:
    out = [section_open("Open questions"), '<div class="tablewrap"><table class="reg questions">']
    for r in sorted(t.rows, key=lambda r: _rr.round_of(cell(r, 0))):
        rid, tail = id_cell(cell(r, 0))
        out.append(
            f'<tr data-thread="{esc(thread_of(cell(r, 1)))}">'
            f'<td class="id"><span class="rid">{esc(rid)}</span></td>'
            f"{thread_cell(cell(r, 1))}"
            f'<td class="title" data-label="Question">{inline(cell(r, 2))}</td>'
            f'<td class="body" data-label="What I need decided">{body_html(cell(r, 3), subids=True)}</td>'
            f'<td class="body why" data-label="Why it matters">{body_html(cell(r, 4))}</td>'
            f"{round_cell(tail)}"
            "</tr>"
        )
    out.append("</table></div></section>")
    return "".join(out)


def actions_html(t) -> str:
    """Why and Recommendation stay SEPARATE (r42). Fused, the opinion hides inside the
    description of the situation and George cannot see where fact stops and advice starts —
    which is the one thing this table exists to keep visible. On the page the separation is
    a column at width and a labelled, marked block when stacked; it is never one cell."""
    out = [section_open("Actions"), '<div class="tablewrap"><table class="reg actions">']
    for r in sorted(t.rows, key=lambda r: _rr.round_of(cell(r, 0))):
        rid, tail = id_cell(cell(r, 0))
        out.append(
            f'<tr data-thread="{esc(thread_of(cell(r, 1)))}">'
            f'<td class="id"><span class="rid">{esc(rid)}</span></td>'
            f"{thread_cell(cell(r, 1))}"
            f'<td class="title" data-label="Action">{inline(cell(r, 2))}</td>'
            f'<td class="body why" data-label="Why">{body_html(cell(r, 3), subids=True)}</td>'
            f'<td class="body rec" data-label="Recommendation">{body_html(cell(r, 4))}</td>'
            f"{round_cell(tail)}"
            "</tr>"
        )
    out.append("</table></div></section>")
    return "".join(out)


def background_waits(md: str) -> list[str]:
    """The live waits, each with when it fires — that number is what tells George how long
    he can ignore the session. Read from the section text, not from `parse()`: Background is
    one headerless row and `parse()` only registers a table with a `|---|` separator."""
    body = _cr.section_body(md, "Background")
    cells: list[str] = []
    for line in body.splitlines():
        if line.strip().startswith("|"):
            cells += _cr.split_row(line)
    return [c for c in cells if c and c.lower() != "background" and not set(c) <= set("-: ")]


def background_html(md: str) -> str:
    waits = background_waits(md)
    if not waits:
        return ""
    items = "".join(f'<li class="wait">{inline(w)}</li>' for w in waits)
    return section_open("Background") + f'<ul class="waits">{items}</ul></section>'


def tldr_bullets(md: str) -> list[str]:
    body = _cr.section_body(md, "TL;DR")
    return [ln.strip()[2:].strip() for ln in body.splitlines() if ln.strip().startswith("- ")]


def tldr_html(md: str) -> str:
    bullets = tldr_bullets(md)
    if not bullets:
        return ""
    items = "".join(f"<li>{inline(b)}</li>" for b in bullets)
    return section_open("TL;DR") + f'<ul class="tldr">{items}</ul></section>'


def passthrough_html(name: str, body: str) -> str:
    """A section with no renderer is shown, not dropped. `## Background` went missing for a
    whole evening because an allowlist skipped what it did not recognise; the text renderer
    now reports the skip and so does this."""
    print(f"[render-artifact] WARNING: no renderer for section {name!r} — passed through raw", file=sys.stderr)
    return (
        section_open(name)
        + '<p class="passnote">No renderer for this section — shown as written, not dropped.</p>'
        + f'<pre class="passthrough">{esc(body.strip())}</pre></section>'
    )


# --- the page --------------------------------------------------------------

FONTS = (
    '<link rel="stylesheet" '
    'href="https://fonts.googleapis.com/css2?'
    "family=Fraunces:opsz,wght@9..144,400..700&"
    "family=Source+Serif+4:opsz,wght@8..60,400..600&"
    "family=IBM+Plex+Mono:wght@400;500&display=swap\">"
)

CSS = """
/* Palette. The COMPLETE light set lives on bare :root; the dark blocks redefine only
   these same tokens, so no colour has its only definition inside a media query.
   A cool slate with a green bias, not flat grey and deliberately not warm cream. */
:root {
  --paper:   #f5f7f6;
  --panel:   #eceff0;
  --ink:     #191f22;
  --ink-2:   #3d4a50;
  --muted:   #6d7b81;
  --faint:   #93a0a5;
  --rule:    #ccd4d5;
  --rule-2:  #e0e6e6;
  --accent:  #14615c;
  --accent-2:#0e4a46;
  --warn-ink:#7a4a08;
  --warn-bg: #f2e6cf;
  --warn-rule:#c99a3d;
  --code-bg: #e5eaea;
  --shadow:  rgba(20,40,40,.08);
  /* Section hues: one muted colour per section, chosen to sit together, not to shout. */
  --hue-targets:    #8a5a83;
  --hue-threads:    #4a6a9a;
  --hue-answers:    #6b5aa0;
  --hue-work-done:  #14615c;
  --hue-open-questions: #9a6a1c;
  --hue-actions:    #a24d3d;
  --hue-background: #5c6f7a;
  --hue-tl-dr:      #5a7a3f;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper:   #121618;
    --panel:   #1a2022;
    --ink:     #e4eae8;
    --ink-2:   #bcc7c6;
    --muted:   #8d9b9c;
    --faint:   #6c7a7b;
    --rule:    #2d3639;
    --rule-2:  #222b2d;
    --accent:  #6dc0b4;
    --accent-2:#94d6cb;
    --warn-ink:#e7bd6d;
    --warn-bg: #2e2515;
    --warn-rule:#8a6a24;
    --code-bg: #232c2e;
    --shadow:  rgba(0,0,0,.4);
    --hue-targets:    #c39abd;
    --hue-threads:    #8fb0dc;
    --hue-answers:    #b1a3dd;
    --hue-work-done:  #6dc0b4;
    --hue-open-questions: #e0b566;
    --hue-actions:    #e39a89;
    --hue-background: #9fb0ba;
    --hue-tl-dr:      #a4c88b;
  }
}
:root[data-theme="dark"] {
  --paper:   #121618;
  --panel:   #1a2022;
  --ink:     #e4eae8;
  --ink-2:   #bcc7c6;
  --muted:   #8d9b9c;
  --faint:   #6c7a7b;
  --rule:    #2d3639;
  --rule-2:  #222b2d;
  --accent:  #6dc0b4;
  --accent-2:#94d6cb;
  --warn-ink:#e7bd6d;
  --warn-bg: #2e2515;
  --warn-rule:#8a6a24;
  --code-bg: #232c2e;
  --shadow:  rgba(0,0,0,.4);
  --hue-targets:    #c39abd;
  --hue-threads:    #8fb0dc;
  --hue-answers:    #b1a3dd;
  --hue-work-done:  #6dc0b4;
  --hue-open-questions: #e0b566;
  --hue-actions:    #e39a89;
  --hue-background: #9fb0ba;
  --hue-tl-dr:      #a4c88b;
}

--- FACES ---
:root {
  --serif: "Source Serif 4", Charter, Georgia, "Times New Roman", serif;
  --display: "Fraunces", Georgia, "Iowan Old Style", serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

* { box-sizing: border-box; }

/* The filter sets `hidden`; the publisher's reset carries this too, repeated here so the
   control cannot depend on a skeleton this file does not own. */
[hidden] { display: none !important; }

/* A glyph link jumps to a row somewhere else on the page, so say where it landed. */
@media (prefers-reduced-motion: no-preference) {
  :root { scroll-behavior: smooth; }
}
tr[id], section.sec { scroll-margin-top: 1.2rem; }
tr[id]:target td { background: var(--panel); }

body {
  background: var(--paper);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.58;
  -webkit-text-size-adjust: 100%;
}

/* ONE gutter, set once, on the one outer wrapper. Vertical spacing is padding-block so a
   shorthand can never quietly zero the sides. */
.page {
  max-width: 78rem;
  margin: 0 auto;
  padding-inline: 20px;
  padding-block: 2.5rem 4rem;
}

a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: .15em; }

code, .rid, .tnum, .round, .evlabel, .wdslabel, .hwlabel, .asklabel, .subid, .rulelabel, .dateline {
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}
code {
  background: var(--code-bg);
  padding: .06em .28em;
  border-radius: 2px;
  font-size: .84em;
}
.wiki { font-family: var(--mono); font-size: .86em; color: var(--ink-2); }

/* --- masthead --- */
.masthead { border-bottom: 1px solid var(--rule); padding-block-end: 1rem; margin-block-end: 2.2rem; }
.masthead h1 {
  font-family: var(--display);
  font-weight: 600;
  font-size: clamp(1.9rem, 5vw, 2.9rem);
  letter-spacing: -.012em;
  line-height: 1.1;
  margin: 0;
}
/* Which session, which round — readable at a glance, because the page is reconciled
   against a terminal and George runs several sessions at once. */
.eyebrow {
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  font-size: .74rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 .5rem;
}
.dateline {
  color: var(--muted);
  font-size: .72rem;
  letter-spacing: .1em;
  text-transform: uppercase;
  margin: .7rem 0 0;
}
.dateline .dot { color: var(--faint); padding-inline: .45em; }

/* --- section rules --- */
.sec { margin-block: 3rem; }
.sechead {
  display: flex;
  align-items: baseline;
  gap: .7rem;
  margin: 0 0 1.1rem;
  font-family: var(--display);
  font-weight: 600;
  font-size: 1.05rem;
  letter-spacing: .02em;
}
.secname { white-space: nowrap; }
.hairline { flex: 1 1 auto; height: 1px; background: var(--rule); }
.rulelabel {
  font-size: .66rem;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--muted);
  white-space: nowrap;
}

/* --- register tables ---
   No vertical rules anywhere. One hairline between rows and nothing else: the columns are
   held by alignment, which is what the grid was only ever standing in for. */
.tablewrap { overflow-x: auto; }
table.reg {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
table.reg td {
  vertical-align: top;
  padding: .85rem .9rem .95rem 0;
  border: 0;
}
table.reg tr + tr td { border-top: 1px solid var(--rule-2); }

td.id { width: 5.2rem; padding-left: 0; }
.rid {
  font-size: .8rem;
  font-weight: 500;
  color: var(--accent-2);
  letter-spacing: .01em;
  white-space: nowrap;
}
td.thread { width: 4.6rem; white-space: nowrap; }
.tnum { display: block; font-size: .66rem; color: var(--faint); letter-spacing: .04em; }
.glyph { font-size: 1.05rem; line-height: 1.3; letter-spacing: .04em; }

/* UNFORMATTED, George's word: a glyph that is a link must look exactly like a glyph that is
   not. No underline, no colour, no visited state — inherit everything. The focus ring is the
   single exception, because a link no keyboard can reach is not a link. */
a.glyphlink {
  color: inherit;
  text-decoration: none;
  cursor: pointer;
}
a.glyphlink:hover, a.glyphlink:visited, a.glyphlink:active { color: inherit; text-decoration: none; }
a.glyphlink:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 3px;
}
.unmapped { cursor: help; display: inline-block; }
/* The warning mark belongs to the `⚠️` itself, not to the run it sits in: a border under the
   whole glyph cell would put an underline beneath the neighbouring glyph LINK, which is
   exactly the formatting a glyph link is required not to have. */
.unmapped {
  border-bottom: 2px solid var(--warn-rule);
  padding-bottom: 1px;
}
tr.warnrow td.title { color: var(--warn-ink); }

td.title {
  width: 13rem;
  font-family: var(--display);
  font-weight: 500;
  font-size: .95rem;
  line-height: 1.3;
  letter-spacing: -.004em;
}
td.body { max-width: 65ch; color: var(--ink-2); font-size: .92rem; }
td.body p, td.body ul { max-width: 68ch; }  /* measure, not fill: a fixed-layout td's own
                                               max-width is inert, the block's is not */
td.body p { margin: 0 0 .6rem; }
td.body p:last-child { margin-bottom: 0; }
td.round {
  width: 3rem;
  text-align: right;
  font-size: .68rem;
  color: var(--faint);
  padding-right: 0;
}
td.status { width: 11rem; font-size: .8rem; color: var(--muted); }

/* Targets: the falsifiable test is set apart, because it is the thing that says hit or
   not-yet. Everything else in the row is description. */
td.hitwhen { background: var(--panel); padding: .7rem .8rem; }
.hwlabel, .evlabel, .wdslabel, .asklabel {
  display: block;
  font-size: .62rem;
  letter-spacing: .13em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: .3rem;
}
table.targets td.title { font-size: 1rem; }

/* Evidence is the proof, and George ruled it out of the description and into its own column
   beside it: on a page there is room for the claim and its proof side by side, which is
   easier to check than a footing at the end of a paragraph. */
td.evidence {
  background: var(--panel);
  border-left: 2px solid var(--accent) !important;
  padding: .7rem .8rem !important;
  font-family: var(--mono);
  font-size: .74rem;
  line-height: 1.55;
  color: var(--ink-2);
}
td.evidence p { max-width: none; margin: 0 0 .5rem; }
td.evidence p:last-child { margin-bottom: 0; }
td.evidence code { background: transparent; padding: 0; font-size: 1em; }
table.work .c-body { width: 40%; }
table.work .c-ev { width: 24%; }

/* Recommendation is opinion. Marked, never fused with Why. */
td.rec { border-left: 2px solid var(--rule) !important; padding-left: .9rem; }
.subid {
  display: inline-block;
  font-size: .76rem;
  font-weight: 500;
  color: var(--accent-2);
  margin-right: .4em;
}

/* The through-line of the whole table, so it spans the whole table — no column owns it. */
tr.wdsrow td.wds {
  border-top: 2px solid var(--rule) !important;
  background: var(--panel);
  padding: .8rem .9rem !important;
  font-size: .93rem;
  color: var(--ink-2);
  max-width: none;
}
tr.wdsrow td.wds .wdslabel { display: inline-block; margin: 0 .6em 0 0; }
tr[id]:target td.wds { background: var(--panel); }

/* --- the thread selector: the Threads rows ARE the control --- */
/* It stays a row in a Tufte table — no card, no button chrome. A pointer, a hover tint, and
   one unmistakable mark on the active row, because that mark is the only thing on the page
   explaining why most of the other rows just vanished. */
tr.threadrow.live { cursor: pointer; }
tr.threadrow.live:hover td { background: var(--rule-2); }
tr.threadrow.active td { background: var(--panel); }
tr.threadrow.active td.id { box-shadow: inset 3px 0 0 var(--accent); }
tr.threadrow.active .rid { color: var(--accent); }

/* The accessible control, wearing the title's own type: inherit everything, own nothing. */
button.threadpick {
  font: inherit;
  letter-spacing: inherit;
  color: inherit;
  background: none;
  border: 0;
  padding: 0;
  margin: 0;
  text-align: left;
  cursor: pointer;
  display: block;
  width: 100%;
}
button.threadpick:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: 2px;
}

.filterstatus {
  margin: .9rem 0 0;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  font-size: .68rem;
  letter-spacing: .04em;
  color: var(--muted);
}

/* --- answers: prose with true margin notes --- */
.answer { margin-block-end: 2.4rem; }
/* The original question, set apart from the reasoning that follows it (George, 2026-09-29).
   Same label idiom as Hit when / Evidence / WDS: a small caps grey tag on its own line,
   then the content — here the quoted question itself, in the accent hue, so a reader can
   place it as "what was asked" at a glance rather than reading it as more explanation. */
.asked {
  margin: 0 0 1.3rem;
  padding: .7rem .9rem;
  background: var(--panel);
  border-left: 2px solid var(--rule);
  border-radius: 0 4px 4px 0;
}
.askq { font-style: italic; color: var(--ink-2); }
.sec .asked { border-left-color: color-mix(in srgb, var(--h) 45%, var(--rule)); }
.ahead {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: .55rem .8rem;
  padding-bottom: .8rem;
  border-bottom: 1px solid var(--rule-2);
  margin-bottom: 1.1rem;
}
.ahead .averdict {
  flex: 1 1 24ch;
  font-family: var(--display);
  font-weight: 500;
  font-size: 1.22rem;
  line-height: 1.28;
  letter-spacing: -.008em;
  max-width: 58ch;
  color: var(--ink);
}
.athread { font-size: 1rem; white-space: nowrap; }
.around { font-family: var(--mono); font-size: .68rem; color: var(--faint); }

.pair {
  display: grid;
  grid-template-columns: minmax(0, 65ch) 15rem;
  gap: 0 2.2rem;
  align-items: start;
}
.para { max-width: 65ch; }
.para p { margin: 0 0 .9rem; }
.para ul { margin: 0 0 .9rem; padding-left: 1.1rem; }
.para li { margin-bottom: .35rem; }
aside.side {
  font-size: .8rem;
  line-height: 1.5;
  color: var(--muted);
  padding-top: .15rem;
}
aside.side.empty { display: none; }

/* --- background + tl;dr --- */
ul.waits { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: .6rem; }
li.wait {
  background: var(--panel);
  border: 1px solid var(--rule-2);
  border-radius: 3px;
  padding: .45rem .7rem;
  font-size: .83rem;
  color: var(--ink-2);
  max-width: 44ch;
}
/* The TL;DR reads at the same weight as the description columns, not at full ink. It is a
   recap of the prose, so it should not out-shout the rows it summarises — George, r27. */
ul.tldr { margin: 0; padding-left: 1.2rem; max-width: 72ch; color: var(--ink-2); }
ul.tldr li { margin-bottom: .95rem; }
ul.tldr li::marker { color: var(--faint); }

/* --- passthrough --- */
.passnote { font-size: .8rem; color: var(--warn-ink); margin: 0 0 .6rem; }
pre.passthrough {
  overflow-x: auto;
  background: var(--panel);
  border-left: 2px solid var(--warn-rule);
  padding: .8rem;
  font-family: var(--mono);
  font-size: .76rem;
  white-space: pre-wrap;
  word-break: break-word;
}

/* --- section hues ---
   The page was one slate wash with a single teal accent. Each section now carries one muted
   hue (the --hue-* tokens above, redefined for dark) and spends it in the same few places:
   the heading and its band, the ID column, the hairline between rows, the evidence bar and
   the summary row. Body text, glyphs and links keep the neutral ink: colour marks WHERE you
   are on the page, never what a row means. Tints use color-mix; where a browser lacks it the
   declaration is dropped and the neutral rule underneath stays, so nothing breaks. */
.sec { --h: var(--accent); }
#targets.sec        { --h: var(--hue-targets); }
#threads.sec        { --h: var(--hue-threads); }
#answers.sec        { --h: var(--hue-answers); }
#work-done.sec      { --h: var(--hue-work-done); }
#open-questions.sec { --h: var(--hue-open-questions); }
#actions.sec        { --h: var(--hue-actions); }
#background.sec     { --h: var(--hue-background); }
#tl-dr.sec          { --h: var(--hue-tl-dr); }

.sec .secname { color: var(--h); }
.sec .sechead {
  padding: .34rem .7rem;
  margin-inline: -.7rem;
  border-radius: 4px;
  background: color-mix(in srgb, var(--h) 9%, transparent);
}
.sec .hairline {
  height: 2px;
  border-radius: 1px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--h) 60%, var(--rule)), var(--rule));
}
.sec .rulelabel { color: color-mix(in srgb, var(--h) 65%, var(--muted)); }
.sec .rid, .sec .subid, .sec .wdslabel { color: var(--h); }
.sec li::marker { color: var(--h); }
.sec td.evidence {
  border-left-color: var(--h) !important;
  background: color-mix(in srgb, var(--h) 6%, var(--panel));
}
.sec td.rec { border-left-color: color-mix(in srgb, var(--h) 50%, var(--rule)) !important; }
.sec tr.wdsrow td.wds {
  border-top-color: color-mix(in srgb, var(--h) 45%, var(--rule)) !important;
  background: color-mix(in srgb, var(--h) 7%, var(--panel));
}
/* Row hairlines live on the cells on a wide page and on the row once it stacks. */
@media (min-width: 761px) {
  .sec table.reg tr + tr td { border-top-color: color-mix(in srgb, var(--h) 16%, var(--rule-2)); }
}

/* --- narrow: 900px drops the margin column, 760px unstacks the grid --- */
@media (max-width: 900px) {
  .pair { grid-template-columns: minmax(0, 1fr); }
  aside.side {
    margin: -.3rem 0 1rem 1.1rem;
    padding-left: .8rem;
    border-left: 2px solid var(--rule);
    font-size: .78rem;
  }
}
@media (max-width: 760px) {
  body { font-size: 16px; }
  .page { padding-inline: 16px; }
  .tablewrap { overflow-x: visible; }
  table.reg, table.reg tbody { display: block; width: 100%; }
  table.reg tr {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    padding-block: 1.2rem;
  }
  table.reg tr + tr { border-top: 1px solid var(--rule); }
  table.reg tr + tr td { border-top: 0; }
  .sec table.reg tr + tr { border-top-color: color-mix(in srgb, var(--h) 16%, var(--rule)); }
  table.reg td {
    display: block;
    width: auto;
    max-width: none;
    padding: 0;
  }
  table.reg td.id { order: 1; margin-right: .6rem; }
  table.reg td.thread { order: 2; margin-right: .6rem; }
  table.reg td.thread .tnum { display: inline; margin-right: .25em; }
  table.reg td.round { order: 3; text-align: left; margin-left: auto; }
  table.reg td.title { order: 4; flex: 1 0 100%; margin-block: .35rem .6rem; font-size: 1.05rem; }
  table.reg td.body, table.reg td.status { order: 5; flex: 1 0 100%; }
  table.reg td.body + td.body, table.reg td.status { margin-top: .9rem; }
  table.reg td.rec { border-left: 0 !important; padding-left: 0; }
  table.reg td.evidence { padding: .6rem .7rem !important; }
  table.reg tr.wdsrow { padding-block: 0; }
  table.reg tr.wdsrow td.wds { flex: 1 0 100%; margin-top: .8rem; }
  table.reg td[data-label].body::before,
  table.reg td[data-label].status::before {
    content: attr(data-label);
    display: block;
    font-family: var(--mono);
    font-size: .62rem;
    letter-spacing: .13em;
    text-transform: uppercase;
    color: var(--muted);
    color: color-mix(in srgb, var(--h) 65%, var(--muted));
    margin-bottom: .3rem;
  }
  table.reg td.hitwhen::before { content: none; }
  li.wait { max-width: none; flex: 1 1 100%; }
}
"""
# `---` inside a CSS comment-free region would be a syntax error; the face block above is
# separated by a comment, written here without slashes so the docstring stays readable.
CSS = CSS.replace("--- FACES ---", "/* faces */")


def dateline(md: str, draft: Path, tables) -> str:
    bits: list[str] = []
    rnd = round_label(draft, tables)
    if rnd:
        bits.append(f"round {rnd}")
    for name, label in (("Threads", "thread"), ("Open questions", "open question"), ("Actions", "action")):
        t = _cr.find(tables, name)
        if t and t.rows:
            n = len(t.rows)
            bits.append(f"{n} {label}{'' if n == 1 else 's'}")
    waits = background_waits(md)
    bits.append(f"{len(waits)} live wait{'' if len(waits) == 1 else 's'}" if waits else "session idle")
    dot = '<span class="dot">·</span>'
    return dot.join(esc(b) for b in bits)


def resolve_session(draft: Path, given: str | None) -> str:
    """`publish-register.py` always passes `--session` explicitly (derived the same way,
    from the calling directory's own name), so this fallback only matters when
    `render-artifact.py` is run by hand with no `--session`. Running many sessions at once
    makes a register with no session name on it indistinguishable from any other
    session's — which is the whole reason a fallback exists at all, rather than an empty
    title. `Path.cwd().name` is the portable version of that fallback: whatever directory
    convention a session's working directory follows, its own name is the session name,
    with no assumption baked in about what that convention looks like."""
    if given:
        return given.strip()
    return Path.cwd().name


def page_title(session: str) -> str:
    """The session name is the IDENTITY half, so it goes first and survives any trim. No
    round number: the title has to stay stable across rounds to stay recognisable in the
    artifact gallery, and the round is on the page instead. No appended explainer either —
    that is what the publish `description` is for."""
    return f"{session} Session Register" if session else "Session Register"


def round_label(draft: Path, tables) -> str:
    m = re.search(r"\br(\d+)\b", draft.stem)
    if m:
        return f"r{m.group(1)}"
    rnd = max([_rr.round_of(cell(r, 0)) for t in tables for r in t.rows] or [0])
    return f"r{rnd}" if rnd else ""


#: Plain inline JS, no library, and nothing is hidden until it runs — with JS off or broken
#: every row stays visible, which is the only acceptable failure mode for a control that hides
#: content. The thread each row belongs to comes from `data-thread`, written at render time
#: from the parse, never re-derived by reading the DOM's text back.
#:
#: THE CONTROL IS THE THREADS TABLE (ruled by George after using the chips): clicking a
#: thread's row scopes the register to it, clicking the same row again clears. One affordance,
#: no separate All control, and the thing you point at is the thing you are selecting.
#:
#: Three separations hold this together, and each one is a bug that would otherwise happen:
#:
#: 1. A CONTROL ROW IS NEVER A SCOPED ROW. The Threads table has to stay whole while a filter
#:    is active — it IS the control, and if selecting T3 hid the other thread rows the only row
#:    left to click would be T3, so switching threads would be impossible. So thread rows carry
#:    `data-control` and the scoped population is `[data-thread]:not([data-control])`.
#: 2. A GLYPH LINK NAVIGATES, IT DOES NOT FILTER. The glyph links now live INSIDE the rows that
#:    carry the filter handler, so a click on one bubbles to the row. The row handler returns
#:    early for any click originating inside an `<a>`. This is the same collision as the
#:    `data-thread`-on-the-chips bug, in a new place, and it is tested by name.
#: 3. THE BUTTON DOES NOT DOUBLE-FIRE. The accessible control is a real `<button>` in the title
#:    cell, so Enter and Space work and the focus ring and accessible name are free. Its own
#:    handler stops propagation, so the row handler never sees the same activation twice — two
#:    toggles would land back where it started and read as "the click did nothing".
FILTER_JS = """
(function () {
  var rows = [].slice.call(document.querySelectorAll('[data-thread]:not([data-control])'));
  var controls = [].slice.call(document.querySelectorAll('[data-control]'));
  var picks = [].slice.call(document.querySelectorAll('[data-scope]'));
  var status = document.getElementById('filter-status');
  var sections = [].slice.call(document.querySelectorAll('section.sec'));
  var current = '';
  if (!rows.length || !controls.length) { return; }

  function apply(sel) {
    var shown = 0;
    rows.forEach(function (el) {
      var hit = !sel || el.getAttribute('data-thread') === sel;
      el.hidden = !hit;
      if (hit) { shown++; }
    });
    sections.forEach(function (sec) {
      var owned = [].slice.call(sec.querySelectorAll('[data-thread]:not([data-control])'));
      if (!owned.length) { return; }
      var live = 0;
      owned.forEach(function (el) { if (!el.hidden) { live++; } });
      sec.hidden = live === 0;
    });
    controls.forEach(function (tr) {
      var on = tr.getAttribute('data-thread') === sel && !!sel;
      tr.classList.toggle('active', on);
    });
    picks.forEach(function (b) {
      var on = b.getAttribute('data-scope') === sel && !!sel;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    if (status) {
      status.textContent = sel
        ? 'showing ' + shown + ' of ' + rows.length + ' rows \u00b7 ' + sel +
          ' \u2014 click ' + sel + ' again to clear'
        : 'click a thread to scope the register \u00b7 showing all ' + rows.length + ' rows';
    }
  }

  function toggle(sel) {
    if (!sel) { return; }
    current = (current === sel) ? '' : sel;
    apply(current);
  }

  function inside(el, sel) {
    return !!(el && el.closest && el.closest(sel));
  }

  picks.forEach(function (b) {
    b.addEventListener('click', function (ev) {
      ev.stopPropagation();
      toggle(b.getAttribute('data-scope'));
    });
  });

  /* The pointer and the hover tint are painted only under `.live`, added here — so with JS
     off, or on a trivial turn that has no scoped rows at all (the early return above), a
     thread row does not advertise a click that will do nothing. */
  controls.forEach(function (tr) {
    tr.classList.add('live');
    tr.addEventListener('click', function (ev) {
      if (inside(ev.target, 'a')) { return; }
      if (inside(ev.target, '[data-scope]')) { return; }
      toggle(tr.getAttribute('data-thread'));
    });
  });

  apply('');
})();
"""


def render_html(md: str, draft: Path, session: str = "") -> str:
    global _LEGEND
    headings, tables = _cr.parse(md)
    _LEGEND = Legend(tables)
    known = {h.lower() for h in ORDER}
    body: list[str] = []
    for name in ORDER:
        key = name.lower()
        if key == "answers":
            if _rr.answer_blocks(md):
                body.append(answers_html(md))
            continue
        if key == "background":
            body.append(background_html(md))
            continue
        if key == "tl;dr":
            body.append(tldr_html(md))
            continue
        t = _cr.find(tables, name)
        if t is None or not t.rows:
            continue  # empty is a legitimate state and must not render as an empty shell
        if key == "targets":
            body.append(targets_html(t))
        elif key == "threads":
            body.append(threads_html(t))
        elif key == "work done":
            body.append(work_html(t, md))
        elif key == "open questions":
            body.append(questions_html(t))
        elif key == "actions":
            body.append(actions_html(t))
    # Anything the walk above did not know, shown rather than dropped.
    for h in headings:
        if h.lower() not in known and h != "(preamble)":
            body.append(passthrough_html(h, _cr.section_body(md, h)))

    title = page_title(session)
    eyebrow = f'<p class="eyebrow">{esc(session)}</p>' if session else ""
    return "\n".join(
        [
            f"<title>{esc(title)}</title>",
            FONTS,
            f"<style>{CSS}</style>",
            '<div class="page">',
            '<header class="masthead">',
            eyebrow,
            f"<h1>{esc(title)}</h1>",
            f'<p class="dateline">{dateline(md, draft, tables)}</p>',
            "</header>",
            *[b for b in body if b],
            "</div>",
            f"<script>{FILTER_JS}</script>",
            "",
        ]
    )


# --- terminal pointer ------------------------------------------------------


def _plain(text: str) -> str:
    return _cr.strip_markup(text).strip()


def _wrap(text: str, width: int) -> list[str]:
    return _cr.wrap_markdown(_plain(text), width) or [""]


def render_terminal(md: str, draft: Path, session: str = "", width: int = 92) -> str:
    """TL;DR, then a bare index of Open questions and Actions: identifier, glyphs, title.

    Nothing else. The bodies, the Why and the Recommendation are on the page; printing them
    twice is the repetition failure the register exists to remove. This is a pointer — it
    says which rows are open and what they are called, so George can find one."""
    _, tables = _cr.parse(md)
    out: list[str] = []

    # The session name leads, identically to the page's title and eyebrow: George reconciles
    # this output against the artifact, and two things that do not name themselves the same
    # way cannot be reconciled at a glance.
    rnd = round_label(draft, tables)
    if session or rnd:
        out.append(" · ".join(x for x in (session, rnd) if x))
        out.append("")

    # Targets FIRST, above the TL;DR (Q100, ruled): the contract makes it the every-round
    # guardrail whose job is answering "are we still aimed at the thing" without George
    # asking, and the failure it was built to catch (r40) was it silently vanishing. Behind a
    # click on a page it stops doing that, so it stays in the terminal too. `Hit when` does
    # NOT — the falsifiable test is for reading, and reading happens on the page.
    tt = _cr.find(tables, "Targets")
    for r in (tt.rows if tt else []):
        if tt.rows.index(r) == 0:
            out.append("Targets")
        xid, _t = id_cell(cell(r, 0))
        head = f"{xid}  {_plain(cell(r, 1))}  "
        text = "  ·  ".join(x for x in (_plain(cell(r, 2)), _plain(cell(r, 4))) if x)
        lines = _wrap(text, max(24, width - _cr.cell_width(head) - 2))
        out.append("  " + head + lines[0])
        out += ["  " + " " * _cr.cell_width(head) + ln for ln in lines[1:]]
    if tt and tt.rows:
        out.append("")

    bullets = tldr_bullets(md)
    if bullets:
        out.append("TL;DR")
        for b in bullets:
            lines = _wrap(b, width - 4)
            out.append(f"  · {lines[0]}")
            out += [f"    {ln}" for ln in lines[1:]]
            out.append("")

    for name in ("Open questions", "Actions"):
        t = _cr.find(tables, name)
        if t is None or not t.rows:
            continue
        rows = sorted(t.rows, key=lambda r: _rr.round_of(cell(r, 0)))
        idw = max(_cr.cell_width(id_cell(cell(r, 0))[0]) for r in rows)
        tailw = max(_cr.cell_width(id_cell(cell(r, 0))[1]) for r in rows)
        glyphw = max(_cr.cell_width(_glyphs(cell(r, 1))) for r in rows)
        out.append(name)
        for r in rows:
            rid, tail = id_cell(cell(r, 0))
            g = _glyphs(cell(r, 1))
            out.append(
                "  "
                + _pad(rid, idw)
                + "  "
                + _pad(tail, tailw)
                + "  "
                + _pad(g, glyphw)
                + "  "
                + _plain(cell(r, 2))
            )
        out.append("")
    return "\n".join(out).rstrip()


def _glyphs(tag: str) -> str:
    """The thread and Target glyphs only — the number is already carried by the identifier
    the row is indexed under, and the glyphs are what George scans."""
    return re.sub(r"^T\d+\s*", "", tag.strip())


def _pad(text: str, width: int) -> str:
    """Plain spaces, not NBSP: this is terminal output, not markdown pretending to be
    columns. Width is measured in DISPLAY columns — an emoji is two, so len() goes ragged."""
    return text + " " * max(0, width - _cr.cell_width(text))


#: A stub DOM just faithful enough to RUN `FILTER_JS`, so the toggle, the link guard and the
#: double-fire guard are executed rather than eyeballed. macOS ships JavaScriptCore behind
#: `osascript -l JavaScript`, which is the only engine this host has — no node, no browser, no
#: dependency added. Where that is missing the behaviour cases SKIP and say so out loud rather
#: than passing silently, because a test that cannot run must not read as a test that passed.
#:
#: What it does NOT prove: layout, hover, focus rings, smooth scrolling, or real browser event
#: ordering. It proves the decision logic, which is where both of this control's bugs lived.
DOM_STUB_JS = r"""
function El(tag, attrs) {
  this.tag = tag; this.attrs = attrs || {}; this.children = []; this.parent = null;
  this.hidden = false; this.textContent = ''; this._lis = {}; this._classes = {};
  var self = this;
  (this.attrs['class'] || '').split(/\s+/).forEach(function (c) { if (c) { self._classes[c] = 1; } });
  this.classList = {
    add: function (c) { self._classes[c] = 1; },
    remove: function (c) { delete self._classes[c]; },
    contains: function (c) { return !!self._classes[c]; },
    toggle: function (c, on) { if (on) { self._classes[c] = 1; } else { delete self._classes[c]; } }
  };
}
El.prototype.add = function (kid) { kid.parent = this; this.children.push(kid); return kid; };
El.prototype.getAttribute = function (n) { return n in this.attrs ? this.attrs[n] : null; };
El.prototype.setAttribute = function (n, v) { this.attrs[n] = v; };
El.prototype.hasAttribute = function (n) { return n in this.attrs; };
El.prototype.addEventListener = function (t, fn) { (this._lis[t] = this._lis[t] || []).push(fn); };

function matchesSimple(el, sel) {
  var m = /^([a-z]+)?(?:\.([A-Za-z0-9_-]+))?(?:\[([a-z-]+)\])?$/.exec(sel.trim());
  if (!m || (!m[1] && !m[2] && !m[3])) { throw new Error('unsupported selector: ' + sel); }
  if (m[1] && el.tag !== m[1]) { return false; }
  if (m[2] && !el.classList.contains(m[2])) { return false; }
  if (m[3] && !el.hasAttribute(m[3])) { return false; }
  return true;
}
function matches(el, sel) {
  var parts = sel.split(':not(');
  if (!matchesSimple(el, parts[0])) { return false; }
  for (var i = 1; i < parts.length; i++) {
    if (matchesSimple(el, parts[i].replace(/\)\s*$/, ''))) { return false; }
  }
  return true;
}
El.prototype.closest = function (sel) {
  var n = this;
  while (n) { if (matches(n, sel)) { return n; } n = n.parent; }
  return null;
};
El.prototype.querySelectorAll = function (sel) {
  var out = [];
  (function walk(n) {
    n.children.forEach(function (k) { if (matches(k, sel)) { out.push(k); } walk(k); });
  })(this);
  return out;
};
El.prototype.click = function () {
  var ev = { target: this, stopped: false, stopPropagation: function () { this.stopped = true; } };
  var n = this;
  while (n) {
    var ls = n._lis['click'] || [];
    for (var i = 0; i < ls.length; i++) { ls[i].call(n, ev); }
    if (ev.stopped) { break; }
    n = n.parent;
  }
};

var document = new El('#document', {});
document.getElementById = function (id) {
  var hit = null;
  (function walk(n) { n.children.forEach(function (k) { if (k.attrs.id === id) { hit = k; } walk(k); }); })(document);
  return hit;
};

/* The fixture is the SHAPE of a rendered page — three thread rows that are controls, and
   three scoped rows spread over two sections, plus a Targets section that owns none. Only
   structure is invented here; no register content. */
function threadRow(tid) {
  var tr = new El('tr', { id: 'thread-' + tid, 'data-thread': tid, 'data-control': 'scope', 'class': 'threadrow' });
  var glyphTd = tr.add(new El('td', { 'class': 'thread' }));
  var span = glyphTd.add(new El('span', { 'class': 'glyph' }));
  span.add(new El('a', { 'class': 'glyphlink', href: '#target-X1' }));
  var titleTd = tr.add(new El('td', { 'class': 'title' }));
  titleTd.add(new El('button', { id: 'pick-' + tid, 'data-scope': tid, 'class': 'threadpick' }));
  return tr;
}
function scopedRow(tid) { return new El('tr', { 'data-thread': tid }); }

var secThreads = document.add(new El('section', { id: 'threads', 'class': 'sec' }));
var tThreads = secThreads.add(new El('table', {}));
['T1', 'T3', 'T4'].forEach(function (t) { tThreads.add(threadRow(t)); });
secThreads.add(new El('p', { id: 'filter-status', 'class': 'filterstatus' }));

var secWork = document.add(new El('section', { id: 'work-done', 'class': 'sec' }));
var tWork = secWork.add(new El('table', {}));
tWork.add(scopedRow('T1')); tWork.add(scopedRow('T3'));

var secActions = document.add(new El('section', { id: 'actions', 'class': 'sec' }));
secActions.add(new El('table', {})).add(scopedRow('T4'));

var secTargets = document.add(new El('section', { id: 'targets', 'class': 'sec' }));
secTargets.add(new El('table', {})).add(new El('tr', { id: 'target-X1' }));
"""

CHECKS_JS = r"""
var fail = [];
function ok(cond, name) { if (!cond) { fail.push(name); } }
function row(sec, tid) { return document.getElementById(sec).querySelectorAll('[data-thread]').filter(function (e) { return e.getAttribute('data-thread') === tid && !e.hasAttribute('data-control'); })[0]; }
function pick(tid) { return document.getElementById('pick-' + tid); }
function trOf(tid) { return document.getElementById('thread-' + tid); }
function status() { return document.getElementById('filter-status').textContent; }
function threadRowsHidden() { return trOf('T1').hidden || trOf('T3').hidden || trOf('T4').hidden; }

/* 1 — nothing hidden before a click */
ok(!row('work-done', 'T1').hidden && !row('actions', 'T4').hidden, 'initial: no row hidden');
ok(status().indexOf('showing all 3 rows') >= 0, 'initial: status counts every row');

ok(trOf('T1').classList.contains('live') && trOf('T3').classList.contains('live'),
   'initial: the rows advertise themselves as clickable only once the script runs');

/* 2 — clicking a thread row scopes to it */
trOf('T3').click();
ok(!row('work-done', 'T3').hidden, 'scope T3: its own row stays');
ok(row('work-done', 'T1').hidden && row('actions', 'T4').hidden, 'scope T3: other rows hide');
ok(trOf('T3').classList.contains('active'), 'scope T3: the row is marked active');
ok(pick('T3').getAttribute('aria-pressed') === 'true', 'scope T3: aria-pressed on the control');
ok(status().indexOf('1 of 3 rows') >= 0 && status().indexOf('click T3 again to clear') >= 0,
   'scope T3: status says what shows and how to clear');
ok(document.getElementById('actions').hidden, 'scope T3: a section with no live row hides');
ok(!document.getElementById('targets').hidden, 'scope T3: Targets is never scoped');

/* CONSEQUENCE 1 — the control must survive its own filter */
ok(!threadRowsHidden(), 'scope T3: the Threads table stays whole');
ok(!document.getElementById('threads').hidden, 'scope T3: the Threads section stays visible');

/* 3 — clicking a DIFFERENT thread switches without clearing first */
trOf('T1').click();
ok(!row('work-done', 'T1').hidden && row('work-done', 'T3').hidden, 'switch to T1: scope moved');
ok(pick('T1').getAttribute('aria-pressed') === 'true' &&
   pick('T3').getAttribute('aria-pressed') === 'false', 'switch to T1: only one control is pressed');

/* 4 — clicking the SAME thread again clears the filter */
trOf('T1').click();
ok(!row('work-done', 'T1').hidden && !row('work-done', 'T3').hidden && !row('actions', 'T4').hidden,
   'toggle off: every row is back');
ok(!trOf('T1').classList.contains('active'), 'toggle off: the active mark is gone');
ok(pick('T1').getAttribute('aria-pressed') === 'false', 'toggle off: aria-pressed released');
ok(status().indexOf('showing all 3 rows') >= 0, 'toggle off: status back to all');

/* CONSEQUENCE 2 — a glyph link inside an ACTIVE thread row navigates, it does not toggle */
trOf('T3').click();
var before = status();
trOf('T3').querySelectorAll('a')[0].click();
ok(status() === before, 'glyph click inside the active row does not change the scope');
ok(trOf('T3').classList.contains('active'), 'glyph click inside the active row leaves it active');
ok(row('work-done', 'T1').hidden, 'glyph click inside the active row does not clear the filter');

/* the button must not double-fire through the row handler */
trOf('T3').click();
ok(status().indexOf('showing all') >= 0, 'row click off T3 clears');
pick('T3').click();
ok(trOf('T3').classList.contains('active'),
   'the title button toggles ONCE, not twice through the row');

JSON.stringify(fail);
"""


def js_selftest() -> tuple[int, int, str]:
    """Execute FILTER_JS against the stub DOM. Returns (failures, cases, engine-note)."""
    import json
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("osascript"):
        return 0, 0, "SKIPPED — no JavaScriptCore on this host (`osascript` absent)"
    script = DOM_STUB_JS + "\n" + FILTER_JS + "\n" + CHECKS_JS
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(script)
        path = fh.name
    try:
        proc = subprocess.run(["osascript", "-l", "JavaScript", path],
                              capture_output=True, text=True, timeout=60)
    finally:
        Path(path).unlink(missing_ok=True)
    if proc.returncode != 0:
        print(f"  \u2717 the filter script did not run: {proc.stderr.strip()[:400]}")
        return 1, 0, "ERRORED"
    try:
        failures = json.loads(proc.stdout.strip() or "[]")
    except json.JSONDecodeError:
        print(f"  \u2717 unreadable harness output: {proc.stdout.strip()[:200]}")
        return 1, 0, "ERRORED"
    total = script.count("ok(")
    for f in failures:
        print(f"  \u2717 {f}")
    return len(failures), total, "JavaScriptCore"


#: The cases that were BROKEN, kept executable so they cannot break again in silence.
#: `draft-r22.md` is the real fixture — it is the draft that exposed the Evidence bug, and it
#: carries `` `¶` `` inside an Evidence line because George was writing ABOUT the sentinel.
#: These are that same shape reduced to the smallest input that shows it, so a regression
#: names itself instead of being noticed on a published page.
SELFTEST = [
    (
        "a pilcrow inside a code span must not split the cell",
        "Did a thing. ¶ Evidence: `SKILL.md` says `¶` stays reserved, and the sentence continues.",
        ["<code>¶</code>", "and the sentence continues."],
        ["stays reserved because</p>"],
    ),
    (
        "backticked paths inside Evidence stay inside the Evidence column",
        "Did a thing. ¶ Evidence: `render-register.py` matches `out-r20.txt`.",
        ["<code>render-register.py</code>", "<code>out-r20.txt</code>"],
        ["<p>"],
    ),
    (
        "an identifier followed by an apostrophe is a possessive, not a sub-question label",
        "Q99b's direction is implemented; Q99c is live.",
        ["Q99b&#x27;s direction"],
        ['<span class="subid">'],
    ),
]


def selftest() -> int:
    """Run the reduced cases. Not contract validation — `render-register.py --check` owns
    that — just proof that the three defects found while building this stay fixed."""
    bad = 0
    for name, cell_text, want, unwanted in SELFTEST:
        did, ev = split_evidence(cell_text)
        rendered = did + ev if ev else body_html(cell_text, subids=True)
        for w in want:
            if w not in rendered:
                print(f"  ✗ {name}: missing {w!r}"); bad += 1
        for u in unwanted:
            if u in (ev or rendered):
                print(f"  ✗ {name}: {u!r} leaked out of its container"); bad += 1
        if ev and "Evidence:" in ev:
            print(f"  ✗ {name}: the label was not consumed"); bad += 1
    jsbad, jscases, engine = js_selftest()
    bad += jsbad
    where = f"{len(SELFTEST)} markup cases"
    where += f", {jscases} behaviour cases ({engine})" if jscases else f"; behaviour cases {engine}"
    print(f"selftest: {where}")
    print("selftest clean" if not bad else f"{bad} failure(s)")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="render a response register as an artifact page")
    ap.add_argument("draft", type=Path, nargs="?")
    ap.add_argument("--html", type=Path, help="write the artifact body to this file")
    ap.add_argument("--terminal", action="store_true", help="print the TL;DR and a row index")
    ap.add_argument("--session", default=None, help="session name for the title; derived from the draft path if omitted")
    ap.add_argument("--width", type=int, default=92, help="display columns for --terminal")
    ap.add_argument("--selftest", action="store_true", help="run the reduced regression cases and exit")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    md = args.draft.read_text()
    session = resolve_session(args.draft, args.session)
    if args.draft is None:
        ap.error("give a draft, or --selftest")
    if not args.html and not args.terminal:
        ap.error("give --html <out.html>, --terminal, or both")
    if args.html:
        args.html.write_text(render_html(md, args.draft, session))
        print(f"wrote {args.html} ({args.html.stat().st_size} bytes)", file=sys.stderr)
        if not session:
            print("[render-artifact] WARNING: no session name — pass --session so the title names it", file=sys.stderr)
    if args.terminal:
        print(render_terminal(md, args.draft, session, args.width))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
