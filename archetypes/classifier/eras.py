"""Date-windowed rule sets for rotating formats.

MTGOFormatData ships an *active* rule folder per format (`standard/`) plus
dated historical folders for past rotations (`standard-20230701-20240802/`,
`standard-20240803-20250730/`). This module derives the rotation eras from
those folder names — no config — so a deck is labeled with the rule set that
was current when its event happened, not today's post-rotation rules. General:
any format with dated folders gets eras automatically (Standard rotates most,
but bans/era boundaries apply to any format).

An era is a `[start, end]` date window mapped to a definitions directory. The
active `<format>/` folder is the open-ended current era (from the last dated
end + 1 day). A format with no dated folders has a single open era = itself.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from archetypes.classifier.definitions import DEFINITIONS_ROOT


@dataclass(frozen=True)
class Era:
    start: dt.date | None  # None = open (from corpus start)
    end: dt.date | None  # None = open (to corpus end / present)
    rules_dir: str  # definitions subdir name


def _parse(stamp: str) -> dt.date:
    return dt.date(int(stamp[0:4]), int(stamp[4:6]), int(stamp[6:8]))


def format_eras(format_name: str, root: Path = DEFINITIONS_ROOT) -> list[Era]:
    """Rotation eras for a format, ordered by date. Dated folders
    (`<format>-YYYYMMDD-YYYYMMDD`) are bounded eras; the base `<format>/` folder
    is the open current era after the latest dated window."""
    pat = re.compile(rf"^{re.escape(format_name)}-(\d{{8}})-(\d{{8}})$")
    dated: list[Era] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        m = pat.match(p.name)
        if m:
            dated.append(Era(_parse(m.group(1)), _parse(m.group(2)), p.name))
    dated.sort(key=lambda e: e.start or dt.date.min)

    eras = list(dated)
    if (root / format_name).is_dir():
        cur_start = (
            dated[-1].end + dt.timedelta(days=1) if dated and dated[-1].end else None
        )
        eras.append(Era(cur_start, None, format_name))
    return eras


def rules_dir_for_date(format_name: str, date: dt.date, root: Path = DEFINITIONS_ROOT) -> str:
    """The definitions subdir whose era contains ``date`` (falls back to the
    base `<format>/` current era)."""
    for era in format_eras(format_name, root):
        if (era.start is None or date >= era.start) and (era.end is None or date <= era.end):
            return era.rules_dir
    return format_name
