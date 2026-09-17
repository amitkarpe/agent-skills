#!/usr/bin/env python3
"""Focused tests for the reversible skill profile controller."""
from __future__ import annotations

import json
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "apply-skill-profile.py"


class ProfileControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.dest = self.root / "dest"
        self.records = self.root / "records"
        self.config = self.root / "config.toml"
        (self.repo / "skills").mkdir(parents=True)
        (self.repo / "profiles").mkdir()
        self.dest.mkdir()
        for name in ("alpha", "beta", "gamma"):
            skill = self.repo / "skills" / name
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        (self.repo / "profiles" / "core.txt").write_text("alpha\n", encoding="utf-8")
        (self.dest / "beta").symlink_to(self.repo / "skills" / "beta")
        (self.dest / "external").mkdir()
        self.original = (
            'model = "test-model"\n\n'
            '[[skills.config]]\n'
            'path = "/external/example/SKILL.md"\n'
            'enabled = false\n'
        )
        self.config.write_text(self.original, encoding="utf-8")

    def run_controller(self, *extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        command = [
            "python3",
            str(SCRIPT),
            "--repo-root",
            str(self.repo),
            "--dest-root",
            str(self.dest),
            "--config-path",
            str(self.config),
            "--record-dir",
            str(self.records),
            *extra,
        ]
        return subprocess.run(command, check=check, capture_output=True, text=True)

    def test_dry_run_apply_idempotent_and_restore(self) -> None:
        before = self.config.read_bytes()
        result = self.run_controller("--profile", "core")
        self.assertIn("mode=dry-run enabled=1 disabled=2 link=1", result.stdout)
        self.assertEqual(before, self.config.read_bytes())
        self.assertFalse((self.dest / "alpha").exists())

        self.run_controller("--profile", "core", "--apply")
        self.assertTrue((self.dest / "alpha").is_symlink())
        self.assertTrue((self.dest / "beta").is_symlink())
        self.assertTrue((self.dest / "external").is_dir())
        data = tomllib.loads(self.config.read_text(encoding="utf-8"))
        entries = data["skills"]["config"]
        source_states = {
            Path(entry["path"]).parent.name: entry["enabled"]
            for entry in entries
            if str(self.repo / "skills") in entry["path"]
        }
        self.assertEqual({"alpha": True, "beta": False, "gamma": False}, source_states)
        self.assertIn("/external/example/SKILL.md", [entry["path"] for entry in entries])

        records = list(self.records.glob("*.json"))
        self.assertEqual(1, len(records))
        second = self.run_controller("--profile", "core", "--apply")
        self.assertIn("no changes required", second.stdout)
        self.assertEqual(records, list(self.records.glob("*.json")))

        self.run_controller("--restore-record", str(records[0]), "--apply")
        self.assertEqual(self.original, self.config.read_text(encoding="utf-8"))
        self.assertFalse((self.dest / "alpha").exists())
        self.assertTrue((self.dest / "beta").is_symlink())
        self.assertTrue((self.dest / "external").is_dir())

    def test_exact_enable_and_disable_adjust_profile(self) -> None:
        self.run_controller(
            "--profile",
            "core",
            "--enable",
            "beta",
            "--disable",
            "alpha",
            "--apply",
        )
        data = tomllib.loads(self.config.read_text(encoding="utf-8"))
        states = {
            Path(entry["path"]).parent.name: entry["enabled"]
            for entry in data["skills"]["config"]
            if str(self.repo / "skills") in entry["path"]
        }
        self.assertEqual({"alpha": False, "beta": True, "gamma": False}, states)

    def test_manual_source_override_fails_without_mutation(self) -> None:
        source = self.repo / "skills" / "alpha" / "SKILL.md"
        conflict = f'[[skills.config]]\npath = {json.dumps(str(source))}\nenabled = true\n'
        self.config.write_text(conflict, encoding="utf-8")
        before = self.config.read_bytes()
        result = self.run_controller("--profile", "core", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("outside managed block", result.stderr)
        self.assertEqual(before, self.config.read_bytes())
        self.assertFalse((self.dest / "alpha").exists())


if __name__ == "__main__":
    unittest.main()
