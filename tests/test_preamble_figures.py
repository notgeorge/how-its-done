"""Scripted check of the opening-prose cap, the page lead and `## Figures` (file-system r12, George).

Run: python3 ~/.claude/skills/response-format/tests/test_preamble_figures.py
A session wrote its whole answer above the first heading for ten rounds and the page showed
none of it; and a diagram could only be plain characters. These tests hold the fix in place.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE.parent / "render-register.py"
PAGE = HERE.parent / "render-artifact.py"

SVG = '<svg viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg"><rect class="f-box" x="4" y="4" width="192" height="52"/><text class="f-text" x="16" y="34">a stored file</text></svg>'

DRAFT = """{opening}

## Threads

| T# | | Title | Description |
| --- | --- | --- | --- |
| T1 | 🧪⚠️ | Figure test | A fixture thread for the preamble and figure checks. |

{figures}## TL;DR

- Fixture draft for the preamble and figure checks.
"""

FIGURES = """## Figures

F1 · One stored file on disk
```svg
{svg}
```

"""


def run(tool: Path, draft_text: str, *args: str) -> tuple[int, str, str]:
    """Run a tool over a draft; return (exit code, stdout+stderr, the page html if asked)."""
    with tempfile.TemporaryDirectory() as tmp:
        draft = Path(tmp) / "draft-r1.md"
        draft.write_text(draft_text, encoding="utf-8")
        html = Path(tmp) / "out.html"
        argv = [sys.executable, str(tool), *[a.replace("@HTML", str(html)) for a in args], str(draft)]
        done = subprocess.run(argv, capture_output=True, text=True)
        page = html.read_text(encoding="utf-8") if html.exists() else ""
        return done.returncode, done.stdout + done.stderr, page


def draft(opening: str = "A short opening line.", svg: str | None = SVG, extra: str = "") -> str:
    figures = FIGURES.format(svg=svg) if svg is not None else ""
    if extra:
        figures = figures.replace("F1 · One", extra + "\n\nF1 · One")
    return DRAFT.format(opening=opening, figures=figures)


class OpeningProse(unittest.TestCase):
    def test_a_short_opening_passes(self) -> None:
        _, out, _ = run(CHECK, draft(svg=None), "--check")
        self.assertIn("clean", out)

    def test_a_long_opening_is_refused_and_says_where_to_put_it(self) -> None:
        long = " ".join(["word"] * 61)
        _, out, _ = run(CHECK, draft(opening=long, svg=None), "--check")
        self.assertIn("opening prose", out)
        self.assertIn("Answers", out)
        self.assertNotIn("clean —", out)

    def test_the_page_shows_the_opening(self) -> None:
        _, _, page = run(PAGE, draft(opening="The lead sentence nobody should miss.", svg=None), "--html", "@HTML")
        self.assertIn("The lead sentence nobody should miss.", page)
        self.assertIn('class="lead"', page)


class Figures(unittest.TestCase):
    def test_a_figure_passes_and_is_drawn_on_the_page(self) -> None:
        _, out, _ = run(CHECK, draft(), "--check")
        self.assertIn("clean", out)
        _, _, page = run(PAGE, draft(), "--html", "@HTML")
        self.assertIn('<figure class="fig" id="F1">', page)
        self.assertIn('<rect class="f-box"', page)  # drawn, not escaped
        self.assertIn("One stored file on disk", page)

    def test_the_terminal_names_the_figure(self) -> None:
        _, out, _ = run(PAGE, draft(), "--terminal")
        self.assertIn("F1  One stored file on disk", out)

    def test_script_is_refused_and_never_reaches_the_page_as_markup(self) -> None:
        bad = SVG.replace("<rect", "<script>alert(1)</script><rect")
        _, out, _ = run(CHECK, draft(svg=bad), "--check")
        self.assertIn("not allowed in a figure", out)
        _, _, page = run(PAGE, draft(svg=bad), "--html", "@HTML")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)", page)  # shown as source instead

    def test_a_handler_and_a_link_are_refused(self) -> None:
        for bad in (SVG.replace("<rect", '<rect onclick="x()"'), SVG.replace("<rect", '<a href="http://x"/><rect')):
            _, out, _ = run(CHECK, draft(svg=bad), "--check")
            self.assertIn("not allowed in a figure", out)

    def test_a_stray_line_in_the_section_is_refused(self) -> None:
        _, out, _ = run(CHECK, draft(extra="Some prose that is not a caption."), "--check")
        self.assertIn("neither a caption nor inside an svg fence", out)

    def test_a_missing_viewbox_is_refused(self) -> None:
        _, out, _ = run(CHECK, draft(svg=SVG.replace(' viewBox="0 0 200 60"', "")), "--check")
        self.assertIn("no viewBox", out)


if __name__ == "__main__":
    unittest.main()
