"""F1 regression tests: cap step-down policy (src/core/cap_policy.py).

The original code in DFL_v5.monitoring_loop had a dead
``if current_index < 0:`` branch (``list.index`` raises instead of
returning negative), so the intended one-rung step-down never executed.
The policy was extracted to ``cap_policy.next_cap_on_decrease`` and is
tested here purely — no DPG, no RTSS, no .NET.
"""
from pathlib import Path

import pytest

from core.cap_policy import next_cap_on_decrease

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

LADDER = [30, 45, 60, 75, 90]


@pytest.mark.parametrize(
    ("ladder", "current_cap", "fps_mean", "expected"),
    [
        # empty ladder
        ([], 60, 50, None),
        # in ladder at the lowest rung: already at floor
        (LADDER, 30, 25, None),
        (LADDER, 30, 90, None),
        # in ladder mid-range, cap <= fps_mean: step down exactly one rung
        (LADDER, 90, 95, 75),
        (LADDER, 75, 80, 60),
        (LADDER, 60, 60, 45),  # cap == fps_mean boundary
        (LADDER, 45, 45.5, 30),
        # in ladder, cap > fps_mean: jump to highest rung below fps_mean
        (LADDER, 90, 60, 45),
        (LADDER, 75, 30, None),  # nothing below fps_mean
        # not in ladder: highest rung below current cap
        (LADDER, 80, 95, 75),
        (LADDER, 50, 95, 45),
        (LADDER, 25, 95, None),  # below the whole ladder
        # unsorted custom ladder still behaves by membership/order
        ([60, 30, 90], 90, 95, 30),  # rung before 90 in user order
        ([60, 30, 90], 20, 95, None),
    ],
)
def test_next_cap_on_decrease(ladder, current_cap, fps_mean, expected):
    assert next_cap_on_decrease(ladder, current_cap, fps_mean) == expected


def test_dfl_v5_wired_to_policy_and_dead_check_removed():
    """Guard the integration point: DFL_v5's decrease branch must call the
    policy and must not contain the dead ``current_index < 0`` check."""
    src = (SRC_DIR / "core" / "DFL_v5.py").read_text(encoding="utf-8")
    assert "from core.cap_policy import next_cap_on_decrease" in src
    assert "next_cap_on_decrease(fps_limit_list, current_fps_cap, fps_mean)" in src
    assert "current_index < 0" not in src
