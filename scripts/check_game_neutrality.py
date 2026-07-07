#!/usr/bin/env python3
"""CI gate: nothing in models/, jobs/, api/ may import game-specific modules or
reference game-specific literals (plan §4.1 rule 2).

Checks, per Python file in the gated packages:
- imports of the game-specific packages (ingest, archetypes);
- identifiers/attributes containing game-specific substrings;
- string literals exactly matching game or format names from config/formats.json,
  or known game-specific vocabulary.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GATED_PACKAGES = ("models", "jobs", "api")
FORBIDDEN_IMPORT_ROOTS = {"ingest", "archetypes"}
FORBIDDEN_NAME_SUBSTRINGS = ("scryfall", "mtgo", "oracle")
EXTRA_FORBIDDEN_LITERALS = {"scryfall", "mtgo", "oracle_id", "mainboard", "sideboard"}


def forbidden_literals() -> set[str]:
    cfg = json.loads((REPO / "config" / "formats.json").read_text())
    lits = set(EXTRA_FORBIDDEN_LITERALS)
    for game in cfg["games"]:
        lits.add(game["name"])
        for fmt in game["formats"]:
            lits.add(fmt["name"])
    return lits


def check_file(path: Path, literals: set[str]) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                    violations.append(f"{path}:{node.lineno} imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                violations.append(f"{path}:{node.lineno} imports from {node.module}")
        elif isinstance(
            node, ast.Name | ast.Attribute | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            else:
                name = node.name
            low = name.lower()
            if any(s in low for s in FORBIDDEN_NAME_SUBSTRINGS):
                violations.append(f"{path}:{node.lineno} game-specific identifier '{name}'")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.lower() in literals
        ):
            violations.append(f"{path}:{node.lineno} game-specific string literal '{node.value}'")
    return violations


def main() -> int:
    literals = forbidden_literals()
    violations: list[str] = []
    n_files = 0
    for pkg in GATED_PACKAGES:
        for path in sorted((REPO / pkg).rglob("*.py")):
            n_files += 1
            violations.extend(check_file(path, literals))
    if violations:
        print("game-neutrality check FAILED:")
        for v in violations:
            print(" ", v)
        return 1
    print(f"game-neutrality check passed ({n_files} files scanned in {GATED_PACKAGES})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
