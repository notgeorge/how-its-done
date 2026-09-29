#!/usr/bin/env python3
"""Publish a response-register draft as LOCAL html pages, kept per round (ruled 2026-09-27).

    python3 publish-register.py <draft-rN.md> [--session NAME] [--open]

Run it from the session's working directory. The session name defaults to that directory's
basename (a TAP worktree is named after its session: bom-bom, demo-dev, git-serious). The pages
land in that project's Claude directory, so every session keeps its own history:

    ~/.claude/projects/<cwd with every non-alphanumeric character as '-'>/registers/

Writes, under REG_DIR:
  rN.html       this round, kept forever, with prev / next / latest / index links
  current.html  the same page, plus a watcher that announces a newer round
  latest.js     `window.__latestRound = N; window.__latestTldr = [...]` — what the watcher polls
  index.html    every round, newest first, with its TL;DR headline

The body comes from render-artifact.py (the shared renderer, unchanged). The watcher polls by
re-inserting a <script src="latest.js?t=..."> every few seconds: script tags load from file://
where fetch() does not.

**On the live page (2026-09-29, George: "on refresh popping in a modal that says 'new content
available, include the tl;dr' and a button that's already selected so I can press enter to clear
the modal").** A silent `location.reload()` gave no at-a-glance signal that anything had changed —
you'd only find out by noticing the page had moved. So a newer round instead opens a native
`<dialog>` naming the round and listing its TL;DR bullets (from `latest.js`, so no extra file://
fetch), with one autofocused button. Enter (or a click) submits the `method="dialog"` form, which
closes the dialog and reloads. Escape leaves the page as it is and the poll will offer again — the
one case this does NOT handle is a deliberate "not now, and stop asking"; add a second button if
that turns out to be wanted. Older rounds (`rN.html`, not `current.html`) keep the quieter inline
"newer round available" badge — reloading someone off a historical round they opened on purpose is
the wrong default, so that page only points at `current.html` rather than jumping there for them.
"""
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path.home() / ".claude/skills/response-format"
def _opt(name: str) -> str | None:
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        sys.exit(f"{name} needs a value")
    return None


_CWD = Path(os.getcwd()).resolve()
SESSION = _opt("--session") or _CWD.name
REG_DIR = Path.home() / ".claude/projects" / re.sub(r"[^A-Za-z0-9]", "-", str(_CWD)) / "registers"

NAV_CSS = """
.regnav{position:sticky;top:env(safe-area-inset-top,0px);z-index:9;display:flex;flex-wrap:wrap;gap:.4rem 1rem;
 align-items:center;padding:.55rem 16px;font:500 13px/1.3 "IBM Plex Mono",ui-monospace,monospace;
 background:var(--panel);color:var(--ink);border-bottom:1px solid var(--rule)}
.regnav a{color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.regnav .here{font-weight:700;color:var(--ink)}
.regnav .dim{color:var(--muted)}
.regnav .spacer{flex:1}
.regnav time{color:var(--muted)}
.regnav .stale{padding:.1rem .45rem;border-radius:3px;background:var(--warn-bg);color:var(--warn-ink);border:1px solid var(--warn-rule)}
dialog.newround{max-width:26rem;width:calc(100% - 2rem);border:1px solid var(--rule);border-radius:10px;
 padding:1.1rem 1.3rem 1.3rem;background:var(--paper);color:var(--ink);box-shadow:0 12px 40px var(--shadow)}
dialog.newround::backdrop{background:rgba(0,0,0,.6)}
dialog.newround .nr-head{margin:0 0 .6rem;font:600 1.05rem/1.3 var(--display),Georgia,serif}
dialog.newround .nr-tldr{margin:0 0 1.1rem;padding-left:1.1rem;font-size:.92rem;line-height:1.5;color:var(--ink-2)}
dialog.newround .nr-tldr li+li{margin-top:2rem}
dialog.newround button{font:600 .82rem/1 "IBM Plex Mono",ui-monospace,monospace;background:var(--accent);
 color:var(--paper);border:0;border-radius:6px;padding:.6rem 1.05rem;cursor:pointer}
dialog.newround button:focus-visible{outline:2px solid var(--accent-2);outline-offset:2px}
"""


def round_of(draft: Path) -> int:
    m = re.search(r"draft-r(\d+)\.md$", draft.name)
    if not m:
        sys.exit(f"cannot read the round from {draft.name}; expected draft-rN.md")
    return int(m.group(1))


def rounds_on_disk() -> list[int]:
    return sorted(int(p.stem[1:]) for p in REG_DIR.glob("r*.html") if p.stem[1:].isdigit())


def tldr_headline(draft: Path) -> str:
    md = draft.read_text()
    m = re.search(r"^## TL;DR\s*\n+\s*-\s*(.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def tldr_bullets(draft: Path) -> list[str]:
    """Every TL;DR bullet, for the new-round modal — the headline alone is not enough context
    to decide whether to interrupt scrolling and reload right now."""
    md = draft.read_text()
    m = re.search(r"^## TL;DR\s*\n(.*?)(?:\n##|\Z)", md, re.S | re.M)
    if not m:
        return []
    return [ln.strip()[2:].strip() for ln in m.group(1).splitlines() if ln.strip().startswith("- ")]


def stamp(n: int) -> str:
    """When round n was first published, local time; recorded once so a later re-stitch
    of the page (for its next link) does not move it."""
    f = REG_DIR / f"r{n}.time"
    if not f.exists():
        import datetime
        f.write_text(datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"))
    return f.read_text().strip()


def nav(n: int, rounds: list[int], live: bool) -> str:
    prev = max((r for r in rounds if r < n), default=None)
    nxt = min((r for r in rounds if r > n), default=None)
    parts = [f'<span class="here">{SESSION} · r{n}</span>', f'<time>{html.escape(stamp(n))}</time>']
    parts.append(f'<a href="r{prev}.html">← r{prev}</a>' if prev else "<span class='dim'>← first</span>")
    parts.append(f'<a href="r{nxt}.html">r{nxt} →</a>' if nxt else "<span class='dim'>newest</span>")
    parts.append('<span class="spacer"></span>')
    parts.append('<a href="index.html">all rounds</a>')
    parts.append("<span class='dim'>live · auto-refreshing</span>" if live else '<a href="current.html">latest</a>')
    # Rendered on every page, live or not, hidden until JS finds something newer — the live
    # page needs it too now: it's what stays up after an Escape declines the modal, so the
    # "new content" signal doesn't just vanish along with the dialog (George, 2026-09-29).
    parts.append('<span class="stale" id="stale" hidden>newer round available</span>')
    return f'<nav class="regnav">{"".join(parts)}</nav>'


WATCH_JS = """
<script>
(function(){
  var mine = %d, live = %s, shown = false;
  function esc(s){ var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function announce(n, tldr){
    // The badge is the durable signal, unhidden the moment a newer round is seen — not only
    // after the dialog is declined — so it is there even if the dialog never gets a chance
    // to be read. Idempotent: safe to run every poll while `shown` guards the dialog itself.
    var badge = document.getElementById('stale');
    if (badge) { badge.hidden = false; badge.style.cursor = 'pointer'; badge.onclick = function(){ location.reload(); }; }
    if (shown) return;
    var dlg = document.createElement('dialog');
    if (typeof dlg.showModal !== 'function') { location.reload(); return; }  // no <dialog>: old fallback
    shown = true;
    dlg.className = 'newround';
    var items = (tldr && tldr.length) ? tldr.map(function(t){ return '<li>' + esc(t) + '</li>'; }).join('')
      : '<li>(round r' + n + ' has no TL;DR)</li>';
    dlg.innerHTML =
      '<form method="dialog">' +
        '<p class="nr-head">New content available — r' + n + '</p>' +
        '<ul class="nr-tldr">' + items + '</ul>' +
        '<button value="load" autofocus>Load it</button>' +
      '</form>';
    document.body.appendChild(dlg);
    dlg.addEventListener('close', function(){
      if (dlg.returnValue === 'load') { location.reload(); return; }
      // Escape: dismiss for good this pageview. `shown` stays true on purpose — the badge
      // above (already visible) is now the only signal, so the dialog does not reappear on
      // the next poll (George, 2026-09-29: "if i hit escape ... it comes back in a few
      // seconds" — that was `shown = false` here re-arming it every cycle).
      dlg.remove();
    });
    dlg.showModal();
  }
  function poll(){
    var s = document.createElement('script');
    s.src = 'latest.js?t=' + Date.now();
    s.onload = s.onerror = function(){
      s.remove();
      var n = window.__latestRound;
      if (typeof n === 'number' && n > mine) {
        if (live) { announce(n, window.__latestTldr); return; }
        var el = document.getElementById('stale'); if (el) el.hidden = false;
      }
    };
    document.head.appendChild(s);
  }
  setInterval(poll, 5000);
})();
</script>
"""


def page(body: str, n: int, rounds: list[int], live: bool) -> str:
    # render-artifact.py emits a skeleton-less body (the Artifact host used to wrap it);
    # a local file needs the document around it.
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"<style>{NAV_CSS}</style>\n</head>\n<body>\n"
        + nav(n, rounds, live)
        + "\n"
        + body
        + (WATCH_JS % (n, "true" if live else "false"))
        + "\n</body>\n</html>\n"
    )


def main() -> None:
    skip = {i + 1 for i, a in enumerate(sys.argv) if a == "--session"}
    args = [a for i, a in enumerate(sys.argv) if i > 0 and i not in skip and not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    draft = Path(args[0]).resolve()
    n = round_of(draft)
    REG_DIR.mkdir(parents=True, exist_ok=True)
    body = subprocess.run(
        [sys.executable, str(SKILL / "render-artifact.py"), str(draft), "--html", "/dev/stdout", "--session", SESSION],
        check=True, capture_output=True, text=True,
    ).stdout
    body = re.sub(r"^wrote .*$", "", body, flags=re.M)
    (REG_DIR / f"r{n}.draft.md").write_text(draft.read_text())
    rounds = sorted(set(rounds_on_disk()) | {n})
    (REG_DIR / f"r{n}.html").write_text(page(body, n, rounds, live=False))
    # Re-stitch the previous round so its "next" link points here.
    prev = max((r for r in rounds if r < n), default=None)
    if prev is not None and (REG_DIR / f"r{prev}.draft.md").exists():
        pbody = subprocess.run(
            [sys.executable, str(SKILL / "render-artifact.py"), str(REG_DIR / f"r{prev}.draft.md"),
             "--html", "/dev/stdout", "--session", SESSION],
            check=True, capture_output=True, text=True,
        ).stdout
        pbody = re.sub(r"^wrote .*$", "", pbody, flags=re.M)
        (REG_DIR / f"r{prev}.html").write_text(page(pbody, prev, rounds, live=False))
    latest = max(rounds)
    if n == latest:
        (REG_DIR / "current.html").write_text(page(body, n, rounds, live=True))
        (REG_DIR / "latest.js").write_text(
            f"window.__latestRound = {n};\nwindow.__latestTldr = {json.dumps(tldr_bullets(draft))};\n"
        )
    rows = []
    for r in sorted(rounds, reverse=True):
        d = REG_DIR / f"r{r}.draft.md"
        head = html.escape(tldr_headline(d)) if d.exists() else ""
        rows.append(f'<li><a href="r{r}.html">r{r}</a> — {head}</li>')
    (REG_DIR / "index.html").write_text(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{SESSION} rounds</title><style>body{{font:15px/1.5 Georgia,serif;max-width:70ch;"
        "margin:0 auto;padding:1.5rem 16px;background:#f7f6f2;color:#1d1c1a}"
        "@media (prefers-color-scheme:dark){body{background:#17181a;color:#e6e3dc}a{color:#9cc3ff}}"
        f"li{{margin:.4rem 0}}</style></head><body><h1>{SESSION} — every round</h1>"
        f'<p><a href="current.html">live page</a></p><ol reversed>{"".join(rows)}</ol></body></html>\n'
    )
    print(REG_DIR / "current.html")
    if "--open" in sys.argv:
        subprocess.run(["open", str(REG_DIR / "current.html")], check=False)


if __name__ == "__main__":
    main()
