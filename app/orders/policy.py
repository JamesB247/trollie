"""Partial-fulfilment decision table (blueprint §5.4; PRD partial-fulfilment rules).

Pure function of the approved snapshot and the failed legs:
- any must-have line in a failed leg -> stop (both modes; must-have overrides partial);
- complete-required -> stop;
- allow-partial -> continue only if every line of every failed leg is an expressly
  permitted omission, at least one leg remains, and no fee or window gets worse.
Money freed by a removal is never used to add, swap or upgrade anything.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Decision:
    kind: str  # full | partial | cancel_all
    reason: str
    removed_leg_ids: tuple[str, ...] = ()


def decide(snapshot: dict[str, Any], failed_leg_ids: set[str]) -> Decision:
    if not failed_leg_ids:
        return Decision("full", "all legs accepted")
    legs = {leg["leg_id"]: leg for leg in snapshot["legs"]}
    failed_lines = [ln for leg_id in failed_leg_ids for ln in legs[leg_id]["lines"]]
    if any(ln["must_have"] for ln in failed_lines):
        return Decision("cancel_all", "must_have_unavailable")
    policy = snapshot.get("fulfilment_policy") or {}
    if policy.get("mode") != "allow_partial":
        return Decision("cancel_all", "complete_required")
    permitted = set(policy.get("permitted_omissions", []))
    if not all(ln["line_id"] in permitted for ln in failed_lines):
        return Decision("cancel_all", "omission_not_permitted")
    if failed_leg_ids >= set(legs):
        return Decision("cancel_all", "nothing_left_to_fulfil")
    # Removing a whole leg removes its own delivery fee and window; remaining legs keep the
    # exact approved fees and windows, so no approved condition gets worse.
    return Decision("partial", "permitted_omissions", tuple(sorted(failed_leg_ids)))
