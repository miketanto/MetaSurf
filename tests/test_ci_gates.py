"""The two custom CI gates must pass on the current tree and actually catch
violations (self-test on a synthetic bad file)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_game_neutrality_gate_passes_on_tree():
    proc = subprocess.run(
        [sys.executable, "scripts/check_game_neutrality.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_game_neutrality_catches_violations(tmp_path):
    from scripts.check_game_neutrality import check_file, forbidden_literals

    bad = tmp_path / "bad.py"
    bad.write_text(
        "from ingest.normalize import cache_item\n"
        "FORMAT = 'modern'\n"
        "def get_scryfall_data():\n"
        "    return None\n"
    )
    violations = check_file(bad, forbidden_literals())
    assert len(violations) == 3


def test_determinism_gate_passes():
    proc = subprocess.run(
        [sys.executable, "scripts/check_determinism.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "sha256" in proc.stdout
