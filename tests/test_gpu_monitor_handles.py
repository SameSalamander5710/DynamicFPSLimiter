"""F8 regression tests: PDH query-handle lifecycle in GPUUsageMonitor.

- initialize() must close any existing query before opening a new one (previously
  the old HQUERY leaked on every re-init).
- _close_query() closes the handle and resets state; a second call is a no-op.
- reinitialize() must assign self.counter_handles from the re-setup (previously the
  new handles were discarded, leaving the poll loop pointing at orphaned counters).

The monitor is built via __new__ (bypassing __init__) so no real PDH query is opened
and no background thread is started. The query-setup methods are mocked to return
deterministic handles, and the PDH entry points that take a plain handle
(PdhCloseQuery / PdhCollectQueryData) are faked.
"""
import ctypes
import threading
import types

from core import gpu_monitor
from core.gpu_monitor import GPUUsageMonitor


def _make_monitor(stub_logger):
    m = GPUUsageMonitor.__new__(GPUUsageMonitor)
    m.interval = 0.01
    m.max_samples = 20
    m.samples = []
    m.gpu_percentile = 0
    m.percentile = 70
    m.logger = stub_logger
    m.dpg = None
    m.themes_manager = None
    m.query_handle = None
    m.counter_handles = {}
    m.instances = []
    m.luid_selected = False
    m.luid = "All"
    m.looping = False
    m._lock = threading.Lock()
    m._thread = None
    return m


def _fake_pdh(closed):
    return types.SimpleNamespace(
        PdhCloseQuery=lambda h: (closed.append(h), 0)[1],
        PdhCollectQueryData=lambda h: 0,
    )


def test_initialize_closes_previous_query(monkeypatch, stub_logger):
    m = _make_monitor(stub_logger)
    h1 = ctypes.c_void_p(0x1111)
    h2 = ctypes.c_void_p(0x2222)
    handles = iter([h1, h2])
    m._init_gpu_state = lambda: next(handles)
    m._setup_gpu_instances = lambda: ["inst"]
    m._setup_gpu_query_from_instances = lambda q, i, et: (q, {"0x1": [ctypes.c_void_p(0xAA)]})

    closed = []
    monkeypatch.setattr(gpu_monitor, "pdh", _fake_pdh(closed))

    m.initialize()
    assert m.query_handle == h1
    assert closed == []

    m.initialize()
    assert m.query_handle == h2
    assert closed == [h1]


def test_close_query_resets_state(monkeypatch, stub_logger):
    m = _make_monitor(stub_logger)
    h = ctypes.c_void_p(0x4444)
    m.query_handle = h
    m.counter_handles = {"0x1": [ctypes.c_void_p(0x55)]}

    closed = []
    monkeypatch.setattr(gpu_monitor, "pdh", _fake_pdh(closed))

    m._close_query()
    assert closed == [h]
    assert m.query_handle is None
    assert m.counter_handles == {}

    m._close_query()
    assert closed == [h]


def test_reinitialize_assigns_counter_handles(monkeypatch, stub_logger):
    m = _make_monitor(stub_logger)
    h = ctypes.c_void_p(0x3333)
    m._init_gpu_state = lambda: h
    m._setup_gpu_instances = lambda: ["inst"]

    calls = {"n": 0}

    def setup(q, i, et):
        calls["n"] += 1
        return q, {f"0x{calls['n']}": [ctypes.c_void_p(0x100 + calls["n"])]}

    m._setup_gpu_query_from_instances = setup

    monkeypatch.setattr(gpu_monitor, "pdh", _fake_pdh([]))

    m.initialize()
    assert calls["n"] == 1
    assert "0x1" in m.counter_handles

    m.reinitialize()
    # initialize() inside reinitialize() is call 2; reinitialize's own setup is call 3.
    assert calls["n"] == 3
    assert "0x3" in m.counter_handles
    assert "0x2" not in m.counter_handles
