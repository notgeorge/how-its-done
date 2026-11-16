"""Scripted checks of the hand-off packer and checker.

Run: python3 push-to-buildbox/tests/test_handoff.py

Each refusal in SKILL.md has a test here, because a refusal nobody has seen fire is a
refusal nobody can rely on. The repositories are throwaway ones made in a temp directory,
with a bare repository standing in for the remote.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "handoff.py"
TEMPLATES = HERE.parent / "templates"

SECTIONS = [
    "Intent and end state", "Current state", "Next action", "Settled decisions", "Do not",
    "Known unknowns", "How to verify", "Environment", "Who to ask", "Quoted material",
]


def run(*args: str, cwd: Path | None = None) -> tuple[int, str]:
    done = subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, cwd=cwd)
    return done.returncode, done.stdout + done.stderr


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


class Fixture:
    """A work tree with a pushed commit, and a hand-off source directory pointing at it."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.remote = tmp / "remote.git"
        self.work = tmp / "work"
        self.source = tmp / "source"
        self.out = tmp / "out"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.work)], check=True)
        git(self.work, "config", "user.email", "fixture@example.invalid")
        git(self.work, "config", "user.name", "Fixture")
        (self.work / "spec.md").write_text("the work\n")
        git(self.work, "add", "spec.md")
        git(self.work, "commit", "-q", "-m", "work")
        git(self.work, "remote", "add", "origin", str(self.remote))
        git(self.work, "push", "-q", "-u", "origin", "main")
        self.source.mkdir()
        self.write_brief()
        self.write_decisions()
        self.write_json()

    def write_brief(self, *, sections: list[str] | None = None, extra: str = "") -> None:
        body = "# Hand-off brief: fixture\n\n"
        for name in sections if sections is not None else SECTIONS:
            body += f"## {name}\n\nSomething true about {name.lower()}.\n\n"
        (self.source / "BRIEF.md").write_text(body + extra)

    def write_decisions(self, text: str | None = None) -> None:
        (self.source / "DECISIONS.md").write_text(text if text is not None else
            "# Settled decisions\n\n## D1 Use the plain layout\n\nDecision: plain.\n\nWhy: fewer moving parts.\n")

    def write_json(self, **changes: object) -> None:
        data = {
            "title": "Fixture hand-off", "prepared_by": "fixture session",
            "goal": "Prove the packer works end to end.", "end_state": "An archive that checks itself.",
            "next_action": {"id": "N1", "text": "Open the first issue and read it."},
            "do_not": [{"id": "DN1", "text": "Do not rebuild the fixture."}],
            "decisions": [{"id": "D1", "title": "Use the plain layout"}],
            "repos": [{"name": "work", "path": str(self.work), "role": "the fixture work tree"}],
            "issues": [{"ref": "example/work#1", "title": "First issue"}],
            "required_secret_names": ["example/build-token"],
            "verify_commands": ["true"], "ask": "The fixture author.", "stop_when": "Anything is unclear.",
        }
        data.update(changes)
        (self.source / "handoff.json").write_text(json.dumps(data))

    def pack(self) -> tuple[int, str]:
        return run("pack", str(self.source), "--out", str(self.out))

    def archive(self) -> Path:
        return next(self.out.glob("handoff-*.tar.gz"))

    def digest(self) -> str:
        return hashlib.sha256(self.archive().read_bytes()).hexdigest()

    def head(self) -> str:
        return git(self.work, "rev-parse", "HEAD")


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self._tmp.name).resolve())

    def tearDown(self) -> None:
        self._tmp.cleanup()


class Pack(Case):
    def test_a_clean_pushed_source_packs(self) -> None:
        code, out = self.fx.pack()
        self.assertEqual(code, 0, out)
        self.assertIn("confirmed on the remote", out)
        prompt = next(self.fx.out.glob("*.prompt.txt")).read_text()
        self.assertIn(self.fx.digest(), prompt)  # the prompt carries the archive's digest
        self.assertIn("N1: Open the first issue", prompt)
        self.assertIn("DN1: Do not rebuild", prompt)

    def test_the_manifest_takes_the_commit_from_git_not_from_the_source(self) -> None:
        self.fx.pack()
        with tarfile.open(self.fx.archive()) as tar:
            manifest = json.load(tar.extractfile("handoff/manifest.json"))
        self.assertEqual(manifest["repos"][0]["commit"], self.fx.head())
        self.assertTrue(manifest["repos"][0]["pushed_verified"])

    def test_uncommitted_changes_are_refused(self) -> None:
        (self.fx.work / "spec.md").write_text("changed and not committed\n")
        code, out = self.fx.pack()
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes", out)

    def test_an_unpushed_commit_is_refused(self) -> None:
        (self.fx.work / "spec.md").write_text("committed, never pushed\n")
        git(self.fx.work, "commit", "-q", "-am", "local only")
        code, out = self.fx.pack()
        self.assertEqual(code, 1)
        self.assertIn("push", out)

    def test_a_branch_missing_from_the_remote_is_refused(self) -> None:
        git(self.fx.work, "switch", "-q", "-c", "never-pushed")
        code, out = self.fx.pack()
        self.assertEqual(code, 1)
        self.assertIn("does not exist on", out)

    def test_a_missing_or_reordered_section_is_refused(self) -> None:
        self.fx.write_brief(sections=SECTIONS[:-1])
        self.assertIn("must have exactly these sections", self.fx.pack()[1])
        self.fx.write_brief(sections=[SECTIONS[1], SECTIONS[0], *SECTIONS[2:]])
        self.assertEqual(self.fx.pack()[0], 1)

    def test_an_overlong_brief_is_refused(self) -> None:
        self.fx.write_brief(extra="filler\n" * 300)
        code, out = self.fx.pack()
        self.assertEqual(code, 1)
        self.assertIn("ceiling is 200", out)

    def test_a_decision_without_a_reason_is_refused(self) -> None:
        self.fx.write_decisions("# Settled decisions\n\n## D1 Use the plain layout\n\nDecision: plain.\n")
        code, out = self.fx.pack()
        self.assertEqual(code, 1)
        self.assertIn("'Why:'", out)

    def test_decisions_in_the_two_files_must_agree(self) -> None:
        self.fx.write_json(decisions=[{"id": "D1", "title": "a"}, {"id": "D2", "title": "b"}])
        self.assertIn("do not match", self.fx.pack()[1])

    def test_credential_shaped_text_is_refused_with_no_override(self) -> None:
        cases = {
            "AWS access key id": "AKIA" + "ABCDEFGHIJKLMNOP",
            "GitHub token": "ghp_" + "a" * 36,
            "private key block": "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
            "credential in a URL": "https://someone:" + "hunter2pass" + "@example.invalid/repo.git",
        }
        for label, value in cases.items():
            self.fx.write_brief(extra=f"\nnote: {value}\n")
            code, out = self.fx.pack()
            self.assertEqual(code, 1, label)
            self.assertIn(label, out)
        self.assertFalse(list(self.fx.out.glob("*.tar.gz")) if self.fx.out.exists() else [])

    def test_a_secret_value_in_the_names_list_is_refused(self) -> None:
        self.fx.write_json(required_secret_names=["token = abc def"])
        self.assertIn("never its value", self.fx.pack()[1])

    def test_a_stray_file_in_the_source_is_refused(self) -> None:
        (self.fx.source / "transcript.txt").write_text("everything that was said\n")
        code, out = self.fx.pack()
        self.assertEqual(code, 1)
        self.assertIn("unexpected entries", out)

    def test_an_appendix_file_is_packed_and_listed(self) -> None:
        (self.fx.source / "appendix").mkdir()
        (self.fx.source / "appendix" / "notes.md").write_text("supporting detail\n")
        self.assertEqual(self.fx.pack()[0], 0)
        with tarfile.open(self.fx.archive()) as tar:
            self.assertIn("handoff/appendix/notes.md", tar.getnames())

    def test_a_credential_in_the_remote_url_does_not_travel(self) -> None:
        self.fx.pack()
        with tarfile.open(self.fx.archive()) as tar:
            manifest = json.load(tar.extractfile("handoff/manifest.json"))
        self.assertNotIn("@", manifest["repos"][0]["url"])

    def test_the_templates_themselves_are_a_valid_starting_shape(self) -> None:
        text = (TEMPLATES / "BRIEF.md").read_text()
        self.assertEqual([ln[3:].strip() for ln in text.splitlines() if ln.startswith("## ")], SECTIONS)
        json.loads((TEMPLATES / "handoff.json").read_text())


class Receive(Case):
    def setUp(self) -> None:
        super().setUp()
        self.assertEqual(self.fx.pack()[0], 0)
        self.far = self.fx.tmp / "far"
        self.far.mkdir()

    def unpack(self, archive: Path | None = None, digest: str | None = None) -> tuple[int, str]:
        return run("unpack", str(archive or self.fx.archive()), "--digest", digest or self.fx.digest(), "--into", str(self.far))

    def test_the_round_trip_unpacks_and_names_the_pointers(self) -> None:
        code, out = self.unpack()
        self.assertEqual(code, 0, out)
        self.assertIn(self.fx.head(), out)
        self.assertIn("example/build-token", out)
        self.assertTrue((self.far / "handoff" / "BRIEF.md").is_file())

    def test_the_unpacked_checker_verifies_its_own_package(self) -> None:
        self.unpack()
        done = subprocess.run([sys.executable, str(self.far / "handoff" / "receive.py"), "verify"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        (self.far / "handoff" / "BRIEF.md").write_text("altered after unpacking\n")
        done = subprocess.run([sys.executable, str(self.far / "handoff" / "receive.py"), "verify"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("does not match its digest", done.stdout + done.stderr)

    def test_a_wrong_digest_is_refused_before_anything_is_written(self) -> None:
        code, out = self.unpack(digest="0" * 64)
        self.assertEqual(code, 1)
        self.assertIn("digest mismatch", out)
        self.assertFalse((self.far / "handoff").exists())

    def rebuilt(self, change) -> Path:
        """The real archive with one thing changed, and its own (new) digest."""
        members: list[tuple[tarfile.TarInfo, bytes]] = []
        with tarfile.open(self.fx.archive()) as tar:
            for member in tar.getmembers():
                members.append((member, tar.extractfile(member).read()))
        members = change(members)
        path = self.fx.tmp / "rebuilt.tar.gz"
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tar:
                for info, data in members:
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data) if info.isfile() else None)
        path.write_bytes(buffer.getvalue())
        return path

    def refuse(self, change, expect: str) -> None:
        archive = self.rebuilt(change)
        code, out = self.unpack(archive, hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertEqual(code, 1, out)
        self.assertIn(expect, out)
        self.assertFalse((self.far / "handoff").exists())
        self.assertFalse((self.fx.tmp / "escaped.txt").exists())

    def test_an_altered_file_is_refused_even_with_a_matching_archive_digest(self) -> None:
        def change(members):
            return [(i, b"rewritten brief\n" if i.name.endswith("BRIEF.md") else d) for i, d in members]
        self.refuse(change, "does not match its digest")

    def test_an_added_file_is_refused(self) -> None:
        def change(members):
            extra = tarfile.TarInfo("handoff/extra.md")
            return members + [(extra, b"smuggled\n")]
        self.refuse(change, "disagree")

    def test_a_member_that_climbs_out_is_refused(self) -> None:
        def change(members):
            return members + [(tarfile.TarInfo("handoff/../../escaped.txt"), b"out\n")]
        self.refuse(change, "outside handoff/")

    def test_a_member_outside_the_package_directory_is_refused(self) -> None:
        def change(members):
            return members + [(tarfile.TarInfo("elsewhere/x.md"), b"x\n")]
        self.refuse(change, "outside handoff/")

    def test_a_link_member_is_refused(self) -> None:
        def change(members):
            link = tarfile.TarInfo("handoff/link")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            return members + [(link, b"")]
        self.refuse(change, "not a regular file")

    def readback(self, **changes: object) -> tuple[int, str]:
        self.unpack()
        with tarfile.open(self.fx.archive()) as tar:
            manifest = json.load(tar.extractfile("handoff/manifest.json"))
        data = {
            "handoff_id": manifest["handoff_id"],
            "goal_in_my_words": "Show that the packing tool works from start to finish on a fixture.",
            "end_state_in_my_words": "There is an archive on disk that can check its own contents.",
            "first_action": "N1", "do_not": ["DN1"], "decisions_acknowledged": ["D1"],
            "repos_at": {"work": self.fx.head()}, "open_questions": [], "unresolved_pointers": [],
        }
        data.update(changes)
        path = self.far / "handoff" / "readback.json"
        path.write_text(json.dumps(data))
        done = subprocess.run([sys.executable, str(self.far / "handoff" / "receive.py"), "readback", str(path)],
                              capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def test_a_complete_readback_passes(self) -> None:
        code, out = self.readback()
        self.assertEqual(code, 0, out)
        self.assertIn("wait for their go", out)

    def test_a_readback_missing_a_do_not_is_incomplete(self) -> None:
        code, out = self.readback(do_not=[])
        self.assertEqual(code, 1)
        self.assertIn("do_not must list exactly", out)

    def test_a_readback_for_the_wrong_commit_is_incomplete(self) -> None:
        code, out = self.readback(repos_at={"work": "0" * 40})
        self.assertEqual(code, 1)
        self.assertIn("repos_at", out)

    def test_a_readback_that_picks_another_first_action_is_incomplete(self) -> None:
        self.assertEqual(self.readback(first_action="N2")[0], 1)

    def test_a_one_word_restatement_is_incomplete(self) -> None:
        self.assertEqual(self.readback(goal_in_my_words="Understood.")[0], 1)

    def test_open_questions_hold_the_start(self) -> None:
        code, out = self.readback(open_questions=["Which environment is the target?"])
        self.assertEqual(code, 2)
        self.assertIn("BEFORE work starts", out)


if __name__ == "__main__":
    unittest.main()
