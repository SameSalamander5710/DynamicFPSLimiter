"""A6: monitor_idle is a stateless, non-blocking idle check wired into DFL_v5.

The low-level get_idle_duration() stays as the raw utility; monitor_idle wraps it
with threshold comparison and error tolerance. DFL_v5 must call monitor_idle
instead of get_idle_duration directly. These tests cover the behavior and guard
the source invariants.
"""
from pathlib import Path

import pytest

from core import idle_timer

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
IDLE_TIMER = SRC_DIR / "core" / "idle_timer.py"
DFL_V5 = SRC_DIR / "core" / "DFL_v5.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_monitor_idle_returns_true_when_idle_past_threshold(monkeypatch):
    monkeypatch.setattr(idle_timer, "get_idle_duration", lambda: 20.0)
    assert idle_timer.monitor_idle(15) is True
    assert idle_timer.monitor_idle(30) is False


def test_monitor_idle_boundary_inclusive(monkeypatch):
    monkeypatch.setattr(idle_timer, "get_idle_duration", lambda: 5.0)
    assert idle_timer.monitor_idle(5) is True


def test_monitor_idle_error_tolerant_returns_false(monkeypatch):
    def _boom():
        raise RuntimeError("no user input info")

    monkeypatch.setattr(idle_timer, "get_idle_duration", _boom)
    assert idle_timer.monitor_idle(5) is False


def test_monitor_idle_non_blocking_no_debug_print_loop():
    src = _read(IDLE_TIMER)
    assert "while True:" not in src
    assert "get_idle_duration() >= threshold" in src
    assert "monitor_idle()" not in src


def test_dfl_v5_uses_monitor_idle():
    src = _read(DFL_V5)
    assert "monitor_idle(cm.idle_fps_delay)" in src
    assert "idle_secs =" not in src
    assert "get_idle_duration" not in src