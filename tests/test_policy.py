"""Partial-fulfilment decision table (blueprint §5.4), exhaustively."""

import pytest

from app.orders.policy import decide


def snapshot(mode, permitted, must_have_lines=()):
    return {
        "fulfilment_policy": {"mode": mode, "permitted_omissions": list(permitted)},
        "legs": [
            {
                "leg_id": "leg_1",
                "lines": [
                    {"line_id": "a1", "must_have": "a1" in must_have_lines},
                    {"line_id": "a2", "must_have": "a2" in must_have_lines},
                ],
            },
            {"leg_id": "leg_2", "lines": [{"line_id": "b1", "must_have": "b1" in must_have_lines}]},
        ],
    }


@pytest.mark.parametrize(
    ("mode", "permitted", "must_have", "failed", "kind", "reason"),
    [
        ("complete_required", [], [], set(), "full", "all legs accepted"),
        ("complete_required", [], [], {"leg_2"}, "cancel_all", "complete_required"),
        ("complete_required", [], ["b1"], {"leg_2"}, "cancel_all", "must_have_unavailable"),
        ("allow_partial", ["b1"], ["b1"], {"leg_2"}, "cancel_all", "must_have_unavailable"),
        ("allow_partial", ["b1"], [], {"leg_2"}, "partial", "permitted_omissions"),
        ("allow_partial", ["a1"], [], {"leg_1"}, "cancel_all", "omission_not_permitted"),
        ("allow_partial", ["a1", "a2"], [], {"leg_1"}, "partial", "permitted_omissions"),
        ("allow_partial", [], [], {"leg_2"}, "cancel_all", "omission_not_permitted"),
        (
            "allow_partial",
            ["a1", "a2", "b1"],
            [],
            {"leg_1", "leg_2"},
            "cancel_all",
            "nothing_left_to_fulfil",
        ),
    ],
)
def test_decision_table(mode, permitted, must_have, failed, kind, reason):
    decision = decide(snapshot(mode, permitted, must_have), failed)
    assert (decision.kind, decision.reason) == (kind, reason)
    if kind == "partial":
        assert set(decision.removed_leg_ids) == failed
