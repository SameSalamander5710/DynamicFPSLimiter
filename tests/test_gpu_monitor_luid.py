"""F9 regression tests: GPU monitor cross-thread LUID state + get_gpu_usage re-init.

- get_gpu_usage() must NOT call initialize() (it reuses the existing query/counters,
  so it no longer clobbers query_handle/counter_handles mid-run or leaks the query).
- toggle_luid_selection() guards its self.luid write with self._lock (the monitor
  thread reads self.luid under the same lock in gpu_run).
- toggle_luid_selection() routes its dpg.* calls through the GuiQueue (deferred to the
  main thread) rather than calling dpg directly.
- S1: the detection PDH work runs on a short-lived worker thread (never on the DPG
  callback thread); a double-click while a detection is in flight is ignored; a
  failed detection queues a status update instead of raising on the callback thread.

The monitor is built via __new__ (bypassing __init__) so no real PDH query is opened
and no background thread is started.
"""
import ctypes
import threading
import time
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
    m._pdh_lock = threading.RLock()
    m._detecting = False
    m._thread = None
    return m


def _fake_pdh():
    return types.SimpleNamespace(
        PdhCollectQueryData=lambda h: 0,
        PdhGetFormattedCounterValue=lambda *a, **k: 0,
    )


def _wait_worker_submitted(q, timeout=5.0):
    """Wait until the detection worker has queued its _apply closure.

    The worker's last action is submitting _apply, so once the queue is
    non-empty all PDH work is complete (deterministic, no extra sleeping).
    """
    deadline = time.time() + timeout
    while len(q) == 0 and time.time() < deadline:
        time.sleep(0.005)
    assert len(q) > 0, "detection worker never queued its result"


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
    q = GuiQueue()
    m = _make_monitor(FakeDPG(), gui_queue=q, luid_selected=False)
    rec = _RecordingLock()
    m._lock = rec
    m.get_gpu_usage = lambda **kw: (50, "0x1")

    m.toggle_luid_selection()
    _wait_worker_submitted(q)
    q.drain()

    assert m.luid == "0x1"
    assert m.luid_selected is True
    assert m._detecting is False
    assert rec.entered >= 1  # the self.luid write was guarded by the lock


def test_toggle_luid_selection_routes_dpg_via_gui_queue():
    dpg = FakeDPG()
    q = GuiQueue()
    m = _make_monitor(dpg, gui_queue=q, luid_selected=False)
    m.get_gpu_usage = lambda **kw: (50, "0x1")

    m.toggle_luid_selection()
    _wait_worker_submitted(q)

    # No dpg.* call was made directly; everything is buffered in the queue.
    assert dpg.calls == []
    assert len(q) > 0

    # Draining (as the main render loop does) executes the dpg calls.
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


def test_toggle_luid_selection_does_not_block_calling_thread(monkeypatch):
    """S1: the PDH double-collect must run on the worker thread, never on the
    thread that invoked the button callback (the DPG callback thread)."""
    dpg = FakeDPG()
    q = GuiQueue()
    m = _make_monitor(dpg, gui_queue=q, luid_selected=False)

    pdh_threads = []

    def collect(h):
        pdh_threads.append(threading.get_ident())
        return 0

    monkeypatch.setattr(gpu_monitor, "pdh", types.SimpleNamespace(
        PdhCollectQueryData=collect,
        PdhGetFormattedCounterValue=lambda *a, **k: 0,
    ))
    monkeypatch.setattr(gpu_monitor.time, "sleep", lambda *a, **k: None)

    caller = threading.get_ident()
    m.toggle_luid_selection()
    _wait_worker_submitted(q)
    q.drain()

    assert pdh_threads, "detection never reached the PDH layer"
    assert caller not in pdh_threads  # no PDH work on the calling (callback) thread
    assert m.luid_selected is True
    assert m.luid in ("0x1", "0x2")
    assert m._detecting is False


def test_toggle_luid_selection_double_click_starts_single_worker(monkeypatch):
    """S1: a second click while detection is in flight is ignored, not used to
    start a second worker racing the first on the shared PDH query."""
    dpg = FakeDPG()
    q = GuiQueue()
    m = _make_monitor(dpg, gui_queue=q, luid_selected=False)

    gate = threading.Event()
    worker_threads = []

    def collect(h):
        worker_threads.append(threading.get_ident())
        gate.wait(timeout=5)  # hold the worker inside its PDH call
        return 0

    monkeypatch.setattr(gpu_monitor, "pdh", types.SimpleNamespace(
        PdhCollectQueryData=collect,
        PdhGetFormattedCounterValue=lambda *a, **k: 0,
    ))
    monkeypatch.setattr(gpu_monitor.time, "sleep", lambda *a, **k: None)

    m.toggle_luid_selection()
    deadline = time.time() + 5
    while not worker_threads and time.time() < deadline:
        time.sleep(0.005)
    assert worker_threads, "first worker never reached the PDH layer"

    m.toggle_luid_selection()  # double-click while in flight
    assert m._detecting is True

    gate.set()
    _wait_worker_submitted(q)
    q.drain()

    assert len(set(worker_threads)) == 1  # only one worker ever ran PDH calls
    assert m.luid_selected is True
    assert m._detecting is False


def test_toggle_luid_selection_detection_failure_queues_status(monkeypatch):
    """S1: a failed detection is logged and a status update is queued for the
    main thread; the monitor stays unselected and the flag is cleared."""
    dpg = FakeDPG()
    q = GuiQueue()
    m = _make_monitor(dpg, gui_queue=q, luid_selected=False)

    def collect(h):
        raise RuntimeError("pdh down")

    monkeypatch.setattr(gpu_monitor, "pdh", types.SimpleNamespace(
        PdhCollectQueryData=collect,
        PdhGetFormattedCounterValue=lambda *a, **k: 0,
    ))

    m.toggle_luid_selection()
    _wait_worker_submitted(q)
    q.drain()

    assert m.luid_selected is False
    assert m.luid == "All"
    assert m._detecting is False
    assert any("LUID detection error" in msg for msg in m.logger.messages)
    assert any("Failed to detect active LUID." in msg for msg in m.logger.messages)
    assert dpg.values.get("luid_status_text") == "Failed to detect active LUID."
