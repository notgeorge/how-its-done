#!/usr/bin/env python3
"""Render a whole response register, deterministically, in one call.

    python3 render-register.py draft.md                # the rendered response body
    python3 render-register.py draft.md --check        # contract findings only
    python3 render-register.py draft.md --check --strict   # exit 1 if anything is wrong

`draft.md` is the register written as ordinary markdown tables — `## Threads`,
`## Work done`, `## Actions`, and so on, in contract order. This turns it into the
fixed-width, hard-broken, live-markdown form George reads (SKILL.md § The rendered
layout), and refuses to guess: a section it does not recognise is passed through with
its heading so nothing is silently dropped.

WHY A SCRIPT AND NOT A PATTERN TO FOLLOW: the layout is arithmetic — column offsets,
display-vs-source width, NBSP padding, two-space hard breaks. Hand-assembly worked
while it was being designed and was already drifting by the end of that session (the
checker was validating an intermediate that got discarded rather than the text actually
sent). One input, one renderer, one checker over the same parse.

The geometry lives in GRID. Change it here, not in a response.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

_spec = importlib.util.spec_from_file_location("_cr", Path(__file__).parent / "check-response.py")
_cr = importlib.util.module_from_spec(_spec)
sys.modules["_cr"] = _cr
_spec.loader.exec_module(_cr)

NBSP = " "
BREAK = "  \n"          # two trailing spaces: a GFM hard break, so lines are not reflowed
BLANK = NBSP + "  \n"   # a genuinely empty line collapses; one holding an NBSP does not

#: The settled geometry (r54-r70). Widths are DISPLAY columns, not characters.
GRID = {"id": 8, "thread": 12, "title": 28, "body": 66, "body2": 58, "gutter": 5}

#: Which sections carry a thread column, and how many body columns each has.
SHAPE = {
    "targets": {"thread": False, "bodies": 2},
    "threads": {"thread": False, "bodies": 1},
    "work done": {"thread": True, "bodies": 1},
    "open questions": {"thread": True, "bodies": 2},
    "actions": {"thread": True, "bodies": 2},
}

#: Answers keep the ALTERNATE shape, not the grid's columns (ruled r11 in the highbar
#: session, George: "answer: explanation, then the text below it. wide format vs columns. but
#: the width of the answer should be constrained so it doesn't fill the whole screen. if there
#: are specific sections to call out tufte-style then place them in a column to the right").
#: A headline — ID, thread tag, the one-sentence answer — then the explanation as prose
#: underneath, all starting at the answer's text column so the ID edge stays clean, bounded
#: at `text` columns; sidenotes sit in a `side` column beside the paragraph they annotate.
ANSWER = {"text": 80, "side": 46}

#: The only column label that survives. Everything else is self-evident by position
#: (r58, George: "i built the format, i know what the columns mean"); a recommendation
#: is the one a reader can mistake for more explanation.
TRAILING_LABEL = {"actions": "Recommendation"}


def full_width() -> int:
    g = GRID
    return g["id"] + g["gutter"] + g["thread"] + g["gutter"] + g["title"] + g["gutter"] + g["body"] + g["gutter"]


def heading(name: str) -> str:
    """SECTION followed by a hairline. `┈` deliberately, never `-`: a run of hyphens is
    markdown (a horizontal rule, or a setext heading applied to the line above) and would
    break the hard-break scheme the columns depend on."""
    label = name.upper()
    trailing = TRAILING_LABEL.get(name.lower(), "")
    bar = label + " " + "┈" * max(4, full_width() - len(label) - 2)
    return bar + (f"  {trailing}" if trailing else "")


#: Source-only segment break inside a cell. George (highbar r14): "if there are sub-questions
#: inside an entry put them on their own line, we can use carriage returns inside the columns
#: ... then i can respond with lines specific to the question ala Q23c." A markdown table cell
#: cannot hold a newline and `<br>` does not render in his terminal (r19), so the draft writes
#: ` ¶ ` and each segment starts a new line in its column. `¶` never reaches the output.
SEGMENT = "¶"


def wrap_segments(text: str, width: int) -> list[str]:
    """wrap_markdown per `¶`-separated segment, each segment starting on its own line."""
    if SEGMENT not in text:
        return _cr.wrap_markdown(text, width)
    lines: list[str] = []
    for part in text.split(SEGMENT):
        if not part.strip():
            continue
        if lines:
            lines.append("")  # a blank line BETWEEN segments, so sub-questions breathe (r83)
        lines += _cr.wrap_markdown(part.strip(), width)
    return lines or [""]


def row(cells: list[str], with_thread: bool, bodies: int, tail: str = "") -> list[str]:
    g = GRID
    sep = NBSP * g["gutter"]
    widths = [g["body"]] if bodies == 1 else [g["body"], g["body2"]]
    rid, thread, title, *rest = cells
    stacks = [wrap_segments(title, g["title"])]
    stacks += [wrap_segments(c, w) for c, w in zip(rest, widths)]
    out = []
    for i in range(max(len(s) for s in stacks)):
        line = _cr.pad_markdown(rid if i == 0 else "", g["id"]) + sep
        if with_thread:
            line += _cr.pad_markdown(thread if i == 0 else "", g["thread"]) + sep
        line += _cr.pad_markdown(stacks[0][i] if i < len(stacks[0]) else "", g["title"])
        for k, w in enumerate(widths, start=1):
            line += sep + _cr.pad_markdown(stacks[k][i] if i < len(stacks[k]) else "", w)
        if i == 0 and tail:
            line += sep + tail
        out.append(line.rstrip())
    return out


def split_tail(rid: str) -> tuple[str, str]:
    """`A48 · r61` renders as `A48` at the left edge and `r61` trailing. The ID stays
    leftmost because George types it back constantly and hunting the right margin for it
    is worse than the problem moving it would solve (r62). The round trails because he
    never types that."""
    if " · " in rid:
        left, right = rid.split(" · ", 1)
        return left.strip(), right.strip()
    return rid.strip(), ""


def answer_blocks(md: str) -> list[tuple[list[str], str, list[tuple[list[str], str]]]]:
    """Each answer in `## Answers`: its AW table row, the original question (George,
    2026-09-29 — quoted or summarized, from a `> Asked: "..."` line immediately under the
    table), and the explanation below THAT as (paragraph lines, sidenote) pairs. A `> ` line
    straight after a paragraph is that paragraph's sidenote; a blank line ends a paragraph;
    the next table or heading ends the explanation. The draft keeps the single-row AW table
    (r38), so check-response.py's `check_answers` still finds every answer by its `AW`
    header, and its own `find_asked` reads the same `> Asked:` line this parses."""
    if "## Answers" not in md:
        return []
    section = md.split("## Answers", 1)[1].split("\n## ", 1)[0].splitlines()
    out: list[tuple[list[str], str, list[tuple[list[str], str]]]] = []
    i = 0
    while i < len(section):
        line = section[i]
        if line.strip().startswith("|") and i + 1 < len(section) and section[i + 1].strip().startswith("|"):
            j = i + 2
            rows = []
            while j < len(section) and section[j].strip().startswith("|"):
                rows.append(_cr.split_row(section[j]))
                j += 1
            question = ""
            while j < len(section) and not section[j].strip():
                j += 1
            if j < len(section):
                m = _cr.ASKED_RE.match(section[j].strip())
                if m:
                    question = m.group(1).strip()
                    j += 1
            paras: list[tuple[list[str], str]] = []
            buf: list[str] = []
            while j < len(section) and not section[j].strip().startswith("|"):
                ln = section[j].rstrip()
                if ln.startswith(">"):
                    note = ln.lstrip("> ").strip()
                    if buf:
                        paras.append((buf, note))
                        buf = []
                    elif paras:
                        paras[-1] = (paras[-1][0], (paras[-1][1] + " " + note).strip())
                elif not ln.strip():
                    if buf:
                        paras.append((buf, ""))
                        buf = []
                else:
                    buf.append(ln.strip())
                j += 1
            if buf:
                paras.append((buf, ""))
            for r in rows:
                out.append((r, question, paras))
                question, paras = "", []
            i = j
            continue
        i += 1
    return out


def render_answers(md: str) -> str:
    g = GRID
    sep = NBSP * g["gutter"]
    lead = NBSP * (g["id"] + g["gutter"] + g["thread"] + g["gutter"])
    lines = [heading("Answers")]
    for r, question, paras in answer_blocks(md):
        rid, tail = split_tail(r[0])
        thread = r[1] if len(r) > 1 else ""
        answer = r[2] if len(r) > 2 else ""
        head = _cr.wrap_markdown(answer, ANSWER["text"])
        for k, text in enumerate(head):
            prefix = (_cr.pad_markdown(rid, g["id"]) + sep + _cr.pad_markdown(thread, g["thread"]) + sep) if k == 0 else lead
            line = prefix + (_cr.pad_markdown(text, ANSWER["text"]) + sep + tail if k == 0 and tail else text)
            lines.append(line.rstrip())
        if question:
            # No text label here (r58: the terminal carries no column labels George didn't
            # ask for, position alone does the work) — italics are what set the original
            # question apart from the explanation that follows it. No added quote marks:
            # the draft's own `> Asked: "..."` already carries them when it is a direct
            # quote, and adding more would double them up.
            lines.append(BLANK.rstrip("\n").rstrip())
            for w in _cr.wrap_markdown(f'*{question}*', ANSWER["text"]):
                lines.append((lead + w).rstrip())
        for para, note in paras:
            lines.append(BLANK.rstrip("\n").rstrip())
            # Consecutive plain lines are one paragraph, reflowed; a `- ` line starts a bullet.
            items: list[str] = []
            for ln in para:
                if ln.startswith(("- ", "* ")) or not items:
                    items.append(ln)
                else:
                    items[-1] = items[-1] + " " + ln
            body: list[str] = []
            for item in items:
                bullet = item.startswith(("- ", "* "))
                wrapped = _cr.wrap_markdown(item[2:] if bullet else item, ANSWER["text"] - (2 if bullet else 0))
                body += [("• " if bullet and n == 0 else "  " if bullet else "") + w for n, w in enumerate(wrapped)]
            side = _cr.wrap_markdown(note, ANSWER["side"]) if note else []
            for n in range(max(len(body), len(side))):
                text = body[n] if n < len(body) else ""
                line = lead + (_cr.pad_markdown(text, ANSWER["text"]) + sep + side[n] if n < len(side) else text)
                lines.append(line.rstrip() or NBSP)
        lines.append("")
    return BREAK.join(lines).rstrip()


def render(md: str) -> str:
    _, tables = _cr.parse(md)
    blocks: list[str] = []
    summary = summary_line(md)
    answers_done = False
    for t in tables:
        key = t.heading.lower()
        if key == "answers":
            if not answers_done:
                blocks.append(render_answers(md))
                answers_done = True
            continue
        if key not in SHAPE:
            continue
        shape = SHAPE[key]
        lines = [heading(t.heading)]
        # Oldest first: staleness becomes position, which costs no ink at all (r62).
        rows = sorted(t.rows, key=lambda r: round_of(r[0]))
        for r in rows:
            rid, tail = split_tail(r[0])
            thread = r[1] if len(r) > 1 else ""
            rest = list(r[2:])
            if not shape["thread"]:
                rid = rid + thread
                thread = ""
            lines += row([rid, thread] + rest, shape["thread"], shape["bodies"], tail)
            lines.append("")
            # A divider under every open question except the last (George, bom-bom r30):
            # sub-question segments already carry blank lines, so a blank alone no longer
            # tells where one question ends and the next begins. `╌`, never `-`, for the
            # same markdown reason as the heading hairline.
            if key == "open questions" and r is not rows[-1]:
                lines.append("╌" * full_width())
                lines.append("")
        text = BREAK.join(lines).rstrip()
        if key == "work done" and summary:
            text += BREAK + BLANK.rstrip("\n") + BREAK + summary
        blocks.append(text)
    bg = background_block(md)
    if bg:
        blocks.append(bg)
    tl = tldr_block(md)
    if tl:
        blocks.append(tl)
    # Anything the walk above skipped, said out loud. A renderer that silently omits an
    # unrecognised section is how `## Background` went missing for a whole evening.
    # "answers" renders through its own path, not the SHAPE walk — omitting it here made
    # the warning fire on a correct draft (highbar, r85). A checker that cries wolf is one
    # its reader learns to skim, which is the failure this warning exists to prevent.
    known = set(SHAPE) | {"answers", "background", "tl;dr"}
    for t in _cr.parse(md)[1]:
        if t.heading.lower() not in known and t.heading != "(preamble)":
            print(f"[render-register] WARNING: no renderer for section {t.heading!r}", file=sys.stderr)
    return (BREAK + BLANK + BLANK).join(blocks)


def background_block(md: str, width: int = 96) -> str:
    """The live waits, last. One line per wait, each saying WHEN IT FIRES.

    This section existed in the contract and not in this renderer — `render()` only walked
    tables whose heading is in SHAPE, and "background" was never added, so a draft carrying
    one rendered every other section and dropped this one in silence. Found by the highbar
    session (r84) after it had hand-appended the strip three times to compensate.

    Worth naming the shape of the bug rather than just fixing it: SHAPE is an allowlist, and
    an unknown heading was skipped rather than refused. A renderer that silently omits what
    it does not recognise will keep doing it every time the contract grows, which is why the
    `continue` below now has an explicit companion in `render()` that reports the skip.
    """
    # Read the section text directly rather than going through parse(): Background is ONE
    # row with no header, and parse() only registers a table when a `|---|` separator
    # follows the first line. So the section was invisible at TWO layers — parse skipped
    # the headerless row, and render() skipped the unrecognised heading — which is how a
    # whole section of the contract went unrendered without a single error.
    m = re.search(r"^## Background\s*$", md, re.M)
    if not m:
        return ""
    body = re.split(r"^## ", md[m.end():], maxsplit=1, flags=re.M)[0]
    cells: list[str] = []
    for line in body.splitlines():
        if line.strip().startswith("|"):
            cells += [c.strip() for c in line.strip().strip("|").split("|")]
    waits = [c for c in cells if c and c.lower() != "background" and not set(c) <= set("-: ")]
    if not waits:
        return ""
    out = [heading("Background")]
    for w in waits:
        wrapped = _cr.wrap_markdown(w, width - 2)
        out.append("· " + wrapped[0])
        out += [NBSP * 2 + x for x in wrapped[1:]]
        out.append("")
    return BREAK.join(out).rstrip()


def tldr_block(md: str, width: int = 96) -> str:
    """The closing summary: what the PROSE above said, so George can tell whether to scroll.

    Deliberately NOT a rehash of Threads, Open questions or Actions — those render their own
    rows and repeating them is the "repetition" failure this whole format exists to remove
    (r83, George: "no need to rehash the things in actions open questions threads or goals,
    just a TL;DR"). It covers the answer at the top, which is the only part of a response
    that has no row of its own and therefore no other way to be found again.

    Fixed width, so nothing wraps off the page, and a blank line between bullets.
    """
    # Match the HEADING, anchored to the start of a line — not the string anywhere in the
    # document. The first draft split on a bare "## TL;DR" and landed inside a Work-done
    # cell that happened to mention the section by name, so the block came back empty and
    # silently rendered nothing. A marker that any prose can impersonate is not a marker.
    m = re.search(r"^## TL;DR\s*$", md, re.M)
    if not m:
        return ""
    body = re.split(r"^## ", md[m.end():], maxsplit=1, flags=re.M)[0]
    bullets = [ln.lstrip("- ").strip() for ln in body.splitlines() if ln.strip().startswith("- ")]
    if not bullets:
        return ""
    out = [heading("TL;DR")]
    for b in bullets:
        wrapped = _cr.wrap_markdown(b, width - 2)
        out.append("· " + wrapped[0])
        out += [NBSP * 2 + w for w in wrapped[1:]]
        out.append("")
    return BREAK.join(out).rstrip()


def round_of(rid: str) -> int:
    if " · r" in rid:
        try:
            return int(rid.split(" · r", 1)[1])
        except ValueError:
            return 0
    return 0


def summary_line(md: str) -> str:
    """The work summary: its own line, left-justified in the first column, BELOW the
    table — it is what George glances back to, and a glance back lands after the rows
    (r70). Written in the draft as a blockquote under `## Work done`."""
    if "## Work done" not in md:
        return ""
    body = md.split("## Work done", 1)[1].split("\n##", 1)[0]
    for line in body.splitlines():
        if line.startswith(">"):
            return line.lstrip("> ").strip()
    return ""


def stale_merge_actions(md: str) -> list[str]:
    """Every Action telling George to merge a PR, whose PR is ALREADY merged.

    r72, George: "is there some way you can double-check that a merge is actually needed
    before telling me to do it?" Yes — and it should not have needed asking. A merge ask
    is the one row in the register whose truth decays on its own, without anything
    happening in the conversation: he merges, and the row keeps asking. Nothing else here
    goes stale by itself, which is exactly why nothing was checking.

    Checks `state`, not `mergeStateStatus` — the latter reports transient values that
    look like progress and are not.
    """
    import json
    import re
    import subprocess

    findings: list[str] = []
    _, tables = _cr.parse(md)
    for t in tables:
        if t.heading.lower() != "actions":
            continue
        for r in t.rows:
            # Key on the ACTION TITLE only, not the whole row (r73: the first version
            # matched any PR number anywhere in the row, so a row citing a merged PR as
            # context — "#767 shipped an hour ago, this reverses it" — was reported as a
            # stale merge ask. A check that cries wolf is one its reader learns to skim,
            # which is worse than no check).
            # And the title must START with Merge — an imperative ask, which is how a merge
            # action is actually phrased. Matching "merge" anywhere in the title flagged
            # "Let me narrow the merge verifier", a row about tooling that asks nothing of
            # anyone. Two false-positive shapes in one evening is the signal that the
            # matcher wants to be narrow and explicit rather than clever.
            title = r[2] if len(r) > 2 else ""
            if not re.match(r"\s*merge\b", title, re.I):
                continue
            nums = set(re.findall(r"#(\d{2,6})", title))
            if not nums:
                findings.append(f"{r[0]}: says merge but names no PR in its title — say which one")
            for num in nums:
                try:
                    out = subprocess.run(
                        ["gh", "pr", "view", num, "--repo", "unified-systems-com/tap", "--json", "state"],
                        capture_output=True, text=True, timeout=20, check=True,
                    ).stdout
                    state = json.loads(out).get("state", "")
                except Exception:  # noqa: BLE001 — an unreachable API must not block a response
                    findings.append(f"{r[0]}: could not check #{num} — say so rather than asserting it needs merging")
                    continue
                if state == "MERGED":
                    findings.append(f"{r[0]}: #{num} is already MERGED — drop the row, do not ask again")
                elif state == "CLOSED":
                    findings.append(f"{r[0]}: #{num} is CLOSED unmerged — the ask is wrong, not just stale")
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="render (and check) a response register")
    ap.add_argument("draft", type=Path)
    ap.add_argument("--check", action="store_true", help="report contract findings instead of rendering")
    ap.add_argument("--strict", action="store_true", help="with --check, exit 1 when anything is wrong")
    ap.add_argument("--register", type=Path, default=None, help="response-register.md, for the Targets cross-check")
    ap.add_argument("--verify-merges", action="store_true", help="check every merge ask against the PR's real state")
    args = ap.parse_args(argv)
    md = args.draft.read_text()
    if args.verify_merges:
        stale = stale_merge_actions(md)
        print("\n".join(f"  ✗ {s}" for s in stale) if stale else "merge asks are all live")
        return 1 if (stale and args.strict) else 0
    if args.check:
        rc = _cr.main([str(args.draft)] + (["--register", str(args.register)] if args.register else []))
        return rc if args.strict else 0
    print(render(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
