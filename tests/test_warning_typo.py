"""L13 regression test: warning message typo (src/core/warning.py).

"can be changes" -> "can be changed". The check runs purely
(no DPG required); a SimpleNamespace stands in for the ConfigManager.
"""
import types

from core.warning import check_min_greater_than_minvalidfps


def _make_config(minvalidfps=60):
    return types.SimpleNamespace(minvalidfps=minvalidfps)


def test_message_does_not_contain_typo():
    msg = check_min_greater_than_minvalidfps(
        dpg=None, cm=_make_config(), mincap=30
    )
    assert msg is not None
    assert "can be changes" not in msg
    assert "can be changed" in msg


def test_message_mentions_minimum_valid_fps():
    msg = check_min_greater_than_minvalidfps(
        dpg=None, cm=_make_config(minvalidfps=60), mincap=30
    )
    assert "60" in msg


def test_no_warning_when_cap_is_valid():
    msg = check_min_greater_than_minvalidfps(
        dpg=None, cm=_make_config(minvalidfps=60), mincap=60
    )
    assert msg is None