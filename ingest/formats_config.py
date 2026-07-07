"""Loader for config/formats.json — formats are config, never code branches."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "formats.json"


@dataclass(frozen=True)
class FormatConfig:
    game: str
    name: str
    do_import: bool
    slug_tokens: tuple[str, ...]
    board_zones: tuple[str, ...]
    expected_mainboard_min: int
    expected_sideboard_max: int
    vector_exclude_type_line_prefixes: tuple[str, ...] = ()

    @property
    def config_jsonb(self) -> dict[str, object]:
        return {
            "slug_tokens": list(self.slug_tokens),
            "board_zones": list(self.board_zones),
            "expected_mainboard_min": self.expected_mainboard_min,
            "expected_sideboard_max": self.expected_sideboard_max,
            "vector_exclude_type_line_prefixes": list(
                self.vector_exclude_type_line_prefixes
            ),
        }


def load_formats(path: Path = CONFIG_PATH) -> list[FormatConfig]:
    raw = json.loads(path.read_text())
    out: list[FormatConfig] = []
    for game in raw["games"]:
        for fmt in game["formats"]:
            out.append(
                FormatConfig(
                    game=game["name"],
                    name=fmt["name"],
                    do_import=fmt["import"],
                    slug_tokens=tuple(fmt["slug_tokens"]),
                    board_zones=tuple(fmt["board_zones"]),
                    expected_mainboard_min=fmt["expected_mainboard_min"],
                    expected_sideboard_max=fmt["expected_sideboard_max"],
                    vector_exclude_type_line_prefixes=tuple(
                        fmt.get("vector_exclude_type_line_prefixes") or ()
                    ),
                )
            )
    return out
