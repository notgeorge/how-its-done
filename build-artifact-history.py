#!/usr/bin/env python3
"""Build the browser mirror WITH its history: the newest round as the Artifact page, and every
round kept on disk as a supporting page beside it (ruled 2026-11-25).

    python3 build-artifact-history.py <draft-rN.md> --out <scratchpad>/artifact [--session NAME]

Run it from the session's working directory, after publish-register.py (which keeps the local
rounds this reads). It writes:

  <out>/register.html          the newest round, with a strip linking to the history
  <out>/rounds/rN.html         every round on disk, each a full page with prev / next / all rounds
  <out>/rounds/index.html      every round, newest first, with its TL;DR headline
  <out>/files.json             the Artifact `files` map for the rounds, keyed by published path

Publish with the Artifact tool: file_path = <out>/register.html, files = the map in files.json.
Always the same out directory, so the URL never changes. Files left out of a publish are kept by
the host, so a round once published stays published; this script still sends every round so a
re-render (a renderer fix, a re-stitched next link) reaches the old pages too.

Why: the mirror used to be the newest round only, and George could not see the previous
response once it was replaced (2026-11-25, regscale r29: "replacing the current doc means i
can't see the previous response"). Local pages kept the history, but the browser link did not.

The rounds' pages carry no `latest.js` watcher: an Artifact cannot poll a sibling file the way a
file:// page does, and the newest round is always the page itself. Inside rounds/, "latest"
points at the newest round's own file rather than back up at the page, because the page's
published path is the host's to choose.
"""

from __future__ import annotations

import html
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location("publish_register", SKILL / "publish-register.py")
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)  # type: ignore[union-attr]


def _opt(name: str) -> str | None:
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def render(draft: Path) -> str:
    out = subprocess.run(
        [sys.executable, str(SKILL / "render-artifact.py"), str(draft), "--html", "/dev/stdout",
         "--session", pr.SESSION],
        check=True, capture_output=True, text=True,
    ).stdout
    return re.sub(r"^wrote .*$", "", out, flags=re.M)


def round_nav(n: int, rounds: list[int]) -> str:
    prev = max((r for r in rounds if r < n), default=None)
    nxt = min((r for r in rounds if r > n), default=None)
    latest = max(rounds)
    parts = [f'<span class="here">{html.escape(pr.SESSION)} · r{n}</span>',
             f'<time>{html.escape(pr.stamp(n))}</time>']
    parts.append(f'<a href="r{prev}.html">← r{prev}</a>' if prev else "<span class='dim'>← first</span>")
    parts.append(f'<a href="r{nxt}.html">r{nxt} →</a>' if nxt else "<span class='dim'>newest</span>")
    parts.append('<span class="spacer"></span>')
    parts.append('<a href="index.html">all rounds</a>')
    parts.append(f'<a href="r{latest}.html">latest (r{latest})</a>' if n != latest else "<span class='dim'>latest</span>")
    return f'<nav class="regnav">{"".join(parts)}</nav>'


def round_page(body: str, n: int, rounds: list[int]) -> str:
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"<title>{html.escape(pr.SESSION)} r{n}</title>\n"
        f"<style>{pr.NAV_CSS}</style>\n</head>\n<body>\n"
        + round_nav(n, rounds) + "\n" + body + "\n</body>\n</html>\n"
    )


def index_page(rounds: list[int]) -> str:
    rows = []
    for r in sorted(rounds, reverse=True):
        d = pr.REG_DIR / f"r{r}.draft.md"
        head = html.escape(pr.tldr_headline(d)) if d.exists() else ""
        rows.append(f'<li><a href="r{r}.html">r{r}</a> <span class="t">{html.escape(pr.stamp(r))}</span> — {head}</li>')
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(pr.SESSION)} rounds</title><style>"
        ":root{--bg:#f7f6f2;--fg:#1d1c1a;--a:#2a5db0;--dim:#6b6860}"
        "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17181a;--fg:#e6e3dc;--a:#9cc3ff;--dim:#9a968c}}"
        ":root[data-theme=dark]{--bg:#17181a;--fg:#e6e3dc;--a:#9cc3ff;--dim:#9a968c}"
        "body{font:15px/1.5 Georgia,serif;max-width:72ch;margin:0 auto;padding:1.5rem 16px;"
        "background:var(--bg);color:var(--fg)}a{color:var(--a)}.t{color:var(--dim);font-size:.85em}"
        "li{margin:.45rem 0}</style></head><body>"
        f"<h1>{html.escape(pr.SESSION)} — every round</h1><ol reversed>{''.join(rows)}</ol></body></html>\n"
    )


HISTORY_STRIP_CSS = (
    "<style>.histstrip{display:flex;gap:1rem;flex-wrap:wrap;align-items:baseline;"
    "font:13px/1.4 system-ui,sans-serif;padding:.5rem 16px;border-bottom:1px solid rgba(127,127,127,.25)}"
    ".histstrip a{color:inherit;opacity:.8}.histstrip .dim{opacity:.55}</style>"
)


def history_strip(n: int, rounds: list[int]) -> str:
    prev = max((r for r in rounds if r < n), default=None)
    parts = [f'<span class="dim">{html.escape(pr.SESSION)} · r{n} · {html.escape(pr.stamp(n))}</span>']
    if prev:
        parts.append(f'<a href="rounds/r{prev}.html">← previous round (r{prev})</a>')
    parts.append(f'<a href="rounds/index.html">all {len(rounds)} rounds</a>')
    return HISTORY_STRIP_CSS + f'<nav class="histstrip">{"".join(parts)}</nav>\n'


def main() -> None:
    skip = {i + 1 for i, a in enumerate(sys.argv) if a in ("--session", "--out")}
    args = [a for i, a in enumerate(sys.argv) if i > 0 and i not in skip and not a.startswith("--")]
    out_dir = _opt("--out")
    if len(args) != 1 or not out_dir:
        sys.exit(__doc__)
    draft = Path(args[0]).resolve()
    n = pr.round_of(draft)
    out = Path(out_dir).resolve()
    (out / "rounds").mkdir(parents=True, exist_ok=True)

    rounds = sorted(set(pr.rounds_on_disk()) | {n})
    files: dict[str, str] = {}
    for r in rounds:
        src = draft if r == n else pr.REG_DIR / f"r{r}.draft.md"
        if not src.exists():
            continue
        p = out / "rounds" / f"r{r}.html"
        p.write_text(round_page(render(src), r, rounds))
        files[f"rounds/r{r}.html"] = str(p)
    (out / "rounds" / "index.html").write_text(index_page(rounds))
    files["rounds/index.html"] = str(out / "rounds" / "index.html")

    # The strip goes after the render's head-like preamble (<title>, <link>, <style>) so the page
    # title is still the first thing the host sees, and before the first body element.
    page = render(draft)
    m = re.search(r"^<(?!title|link|style|meta|/)[a-z]", page, flags=re.M)
    cut = m.start() if m else 0
    (out / "register.html").write_text(page[:cut] + history_strip(n, rounds) + page[cut:])
    (out / "files.json").write_text(json.dumps(files, indent=1) + "\n")
    print(f"wrote {out / 'register.html'} + {len(files)} history files ({out / 'files.json'})")


if __name__ == "__main__":
    main()
