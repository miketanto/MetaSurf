"""The single entitlements module (plan §4.2): user -> set of entitlement flags.

Every premium gate in the API goes through here — no inline tier checks
anywhere else. New paid products are new flags, not new checks.

There is no auth yet (Phase 2), so flags are resolved from the
``X-Entitlements`` request header (comma-separated, unknown flags ignored) —
a deliberate seam the auth layer will replace with a real user lookup; route
code depends only on ``Entitlements``. Free responses keep the premium
fields present-but-locked (plan §8: tease, don't hide).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header

PREMIUM = "premium"
KNOWN_FLAGS = frozenset({PREMIUM})


@dataclass(frozen=True)
class Entitlements:
    flags: frozenset[str]

    def has(self, flag: str) -> bool:
        return flag in self.flags


def resolve_entitlements(
    x_entitlements: Annotated[str | None, Header()] = None,
) -> Entitlements:
    if not x_entitlements:
        return Entitlements(frozenset())
    requested = {part.strip() for part in x_entitlements.split(",")}
    return Entitlements(frozenset(requested & KNOWN_FLAGS))


Entitled = Annotated[Entitlements, Depends(resolve_entitlements)]
