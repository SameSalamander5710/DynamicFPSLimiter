"""Regression guard for the GuiQueue drain wiring in DFL_v5.py.

core.DFL_v5 cannot be imported in tests (importing it runs the application), so
this test guards the wiring at the source level: the app must drain the GuiQueue
from the main render loop, NOT from a self-rescheduling ``dpg.set_frame_callback``
hook. In DearPyGui 2.x all callbacks run on a dedicated background thread and
``set_frame_callback()`` defers registration to that same thread, so a long
callback (e.g. LUID detection) can delay the re-registration until after the
target frame has already been checked — orphaning the hook forever and silently
freezing the in-app log and every queued GUI update.
"""
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DFL_V5 = SRC_DIR / "core" / "DFL_v5.py"


def _source() -> str:
    return DFL_V5.read_text(encoding="utf-8")


def test_main_loop_drains_gui_queue():
    src = _source()
    assert "gui_queue.drain()" in src
    assert "dpg.is_dearpygui_running()" in src
    assert "dpg.render_dearpygui_frame()" in src


def test_no_frame_callback_drain_wiring():
    src = _source()
    assert "dpg.set_frame_callback(" not in src
    assert "_frame_hook" not in src


def test_plotting_loop_uses_min_polling_interval():
    """L18: the plotting-loop sleep must use min() of the two polling intervals,
    not math.lcm() which couples unrelated sensors and can produce surprising
    long sleep values."""
    src = _source()
    assert "math.lcm(" not in src
    assert "min(cm.gpupollinginterval, cm.cpupollinginterval)" in src


def test_gui_queue_wired_with_on_error():
    """S3: the app must route GuiQueue failures to logging so a broken queued
    callback is diagnosable in error_log.txt instead of vanishing."""
    src = _source()
    assert "GuiQueue(on_error=" in src


def test_gpu_gating_branch_uses_is_not_none():
    """L20: the limiter-decision gating branch must treat 0% as a valid GPU
    reading. A bare truthiness test on gpuUsage silently disables limiting
    whenever the GPU percentile is 0."""
    src = _source()
    assert "if gpuUsage is not None and process_name" in src
    assert "if gpuUsage and process_name" not in src
