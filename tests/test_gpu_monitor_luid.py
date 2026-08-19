"""F9 regression tests: GPU monitor cross-thread LUID state + get_gpu_usage re-init.

- get_gpu_usage() must NOT call initialize() (it reuses the existing query/counters,
  so it no longer clobbers query_handle/counter_handles mid-run or leaks the query).
- toggle_luid_selection() guards its self.luid write with self._lock (the monitor
  thread reads self.luid under the same lock in gpu_run).
- toggle_luid_selection() routes its dpg.* calls through the GuiQueue (deferred to the
  main thread) rather than calling dpg directly.

The monitor is built via __new__ (bypassing __init__) so no real PDH query is opened
and no background thread is started.
"""
import ctypes
import threading
import types
from types import SimpleNamespace

from conftest import FakeDPG, StubLogger
from core import gpu_monitor
from core.gpu_monitor import GPUUsageMonitor
from core.gui_queue import GuiQueue


def _make_monitor(dpg=None, gui_queue=None, luid_selected=False, luid="All"):
    m = GPUUsageMonitor.__new__(GPUUsageMonitor)
    m.interval = 0.01
    m.max_samples = 20
    m.samples = []
    m.gpu_percentile = 0
    m.percentile = 70
    m.logger = StubLogger()
    m.dpg = dpg
    m.themes_manager = SimpleNamespace(
        themes={"revert_gpu_theme": "blue", "detect_gpu_theme": "grey"}
    )
    m.gui_queue = gui_queue
    m.query_handle = ctypes.c_void_p(0x100)
    m.counter_handles = {
        "0x1": [ctypes.c_void_p(0x11)],
        "0x2": [ctypes.c_void_p(0x22)],
    }
    m.instances = []
    m.luid_selected = luid_selected
    m.luid = luid
    m.looping = False
    m._lock = threading.Lock()
    m._thread = None
    return m


def _fake_pdh():
    return types.SimpleNamespace(
        PdhCollectQueryData=lambda h: 0,
        PdhGetFormattedCounterValue=lambda *a, **k: 0,
    )


def test_get_gpu_usage_does_not_call_initialize(monkeypatch):
    m = _make_monitor(FakeDPG())
    init_calls = []
    m.initialize = lambda: init_calls.append(1)
    monkeypatch.setattr(gpu_monitor, "pdh", _fake_pdh())
    monkeypatch.setattr(gpu_monitor.time, "sleep", lambda *a, **k: None)

    usage, luid = m.get_gpu_usage()

    assert init_calls == []  # initialize() was NOT called
    assert luid in ("0x1", "0x2")
    assert usage == 0  # PdhGetFormattedCounterValue returns 0 -> doubleValue stays 0.0


class _RecordingLock:
    """A lock that counts how many times it was entered."""

    def __init__(self):
        self._lock = threading.Lock()
        self.entered = 0

    def __enter__(self):
        self.entered += 1
        self._lock.acquire()
        return self

    def __exit__(self, *exc):
        self._lock.release()
        return False


def test_toggle_luid_selection_locks_luid_write():
    m = _make_monitor(FakeDPG(), gui_queue=GuiQueue(), luid_selected=False)
    rec = _RecordingLock()
    m._lock = rec
    m.get_gpu_usage = lambda **kw: (50, "0x1")

    m.toggle_luid_selection()

    assert m.luid == "0x1"
    assert m.luid_selected is True
    assert rec.entered >= 1  # the self.luid write was guarded by the lock


def test_toggle_luid_selection_routes_dpg_via_gui_queue():
    dpg = FakeDPG()
    q = GuiQueue()
    m = _make_monitor(dpg, gui_queue=q, luid_selected=False)
    m.get_gpu_usage = lambda **kw: (50, "0x1")

    m.toggle_luid_selection()

    # No dpg.* call was made directly; everything is buffered in the queue.
    assert dpg.calls == []
    assert len(q) > 0

    # Draining (as the main-thread frame hook does) executes the dpg calls.
    q.drain()
    names = [c[0] for c in dpg.calls]
    assert "configure_item" in names
    assert "bind_item_theme" in names
    assert "set_value" in names
    assert len(q) == 0


def test_toggle_luid_selection_deselect_routes_dpg_via_gui_queue():
    dpg = FakeDPG()
    q = GuiQueue()
    m = _make_monitor(dpg, gui_queue=q, luid_selected=True, luid="0x1")

    m.toggle_luid_selection()

    assert dpg.calls == []
    assert m.luid == "All"
    assert m.luid_selected is False
    q.drain()
    names = [c[0] for c in dpg.calls]
    assert "configure_item" in names
    assert "bind_item_theme" in names
    assert "set_value" in names
