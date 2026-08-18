import contextlib
import sys
import threading
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

requires_win32 = pytest.mark.skipif(sys.platform != "win32", reason="requires Windows")


class StubLogger:
    """Minimal stand-in for core.logger.AppLogger: records messages only."""

    def __init__(self):
        self.messages = []

    def add_log(self, message):
        self.messages.append(str(message))


class FakeDPG:
    """Minimal stand-in for the ``dearpygui.dearpygui`` module.

    - Stores values and item tags in plain dicts.
    - Records every call as ``(name, args, kwargs, thread_name)`` so tests can
      assert *what* was called and *from which thread* (thread-safety checks).
    - Any DearPyGui API not explicitly modeled falls back to a no-op recorder
      via ``__getattr__``, so new call sites never break the fake.
    """

    def __init__(self):
        self.values = {}
        self.items = set()
        self.calls = []
        self._lock = threading.Lock()

    def _record(self, name, args, kwargs):
        with self._lock:
            self.calls.append((name, args, kwargs, threading.current_thread().name))

    # -- value / item API ---------------------------------------------------
    def get_value(self, tag=None):
        self._record("get_value", (tag,), {})
        return None if tag is None else self.values.get(tag)

    def set_value(self, tag, value):
        self._record("set_value", (tag, value), {})
        self.items.add(tag)
        self.values[tag] = value

    def does_item_exist(self, tag):
        self._record("does_item_exist", (tag,), {})
        return tag in self.items

    def configure_item(self, tag, **kwargs):
        self._record("configure_item", (tag,), kwargs)
        self.items.add(tag)

    def delete_item(self, tag, children_only=False):
        self._record("delete_item", (tag, children_only), {})
        self.items.discard(tag)

    def get_item_configuration(self, tag):
        self._record("get_item_configuration", (tag,), {})
        return {}

    # -- theme API ------------------------------------------------------------
    def bind_theme(self, theme):
        self._record("bind_theme", (theme,), {})

    def bind_item_theme(self, tag, theme):
        self._record("bind_item_theme", (tag, theme), {})

    # -- plot API -------------------------------------------------------------
    def set_axis_limits(self, tag, lower, upper):
        self._record("set_axis_limits", (tag, lower, upper), {})

    def set_axis_limits_auto(self, tag):
        self._record("set_axis_limits_auto", (tag,), {})

    # -- callbacks --------------------------------------------------------------
    def set_frame_callback(self, delay, callback):
        self._record("set_frame_callback", (delay, callback), {})

    def add_value_callback(self, tag, callback):
        self._record("add_value_callback", (tag, callback), {})

    def register_value_callback(self, callback):
        self._record("register_value_callback", (callback,), {})

    # -- draw API -----------------------------------------------------------------
    def draw_layer(self, tag=None, parent=None, **kwargs):
        self._record("draw_layer", (tag, parent), kwargs)
        if tag is not None:
            self.items.add(tag)
        return contextlib.nullcontext()

    def draw_circle(self, *args, **kwargs):
        self._record("draw_circle", args, kwargs)

    def draw_text(self, *args, **kwargs):
        self._record("draw_text", args, kwargs)

    # -- catch-all --------------------------------------------------------------------
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _noop(*args, **kwargs):
            self._record(name, args, kwargs)
            return None

        return _noop


@pytest.fixture
def fake_dpg(monkeypatch):
    """Install a FakeDPG as ``dearpygui.dearpygui`` for fresh imports, and
    re-point the ``dpg`` attribute of any already-imported core module."""
    fake = FakeDPG()
    package = types.ModuleType("dearpygui")
    package.dearpygui = fake
    monkeypatch.setitem(sys.modules, "dearpygui", package)
    monkeypatch.setitem(sys.modules, "dearpygui.dearpygui", fake)
    for name, mod in list(sys.modules.items()):
        if (name == "core" or name.startswith("core.")) and hasattr(mod, "dpg"):
            monkeypatch.setattr(mod, "dpg", fake)
    return fake


@pytest.fixture
def stub_logger():
    return StubLogger()


@pytest.fixture
def rtss_stub(tmp_path):
    """A real RTSSController instance with a temp Profiles dir and no-op
    DLL-bound methods (no RTSSHooks64.dll load). File-based methods
    (set_limit_denominator, set_fractional_fps_direct, get_framerate_limit)
    run for real against the temp dir."""
    from core.rtss_functions import RTSSController

    ctrl = object.__new__(RTSSController)
    rtss_dir = tmp_path / "RTSS"
    profiles_dir = rtss_dir / "Profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "Global").write_text(
        "FramerateLimit=0\nLimitDenominator=1\n", encoding="utf-8"
    )

    ctrl.rtss_install_path = str(rtss_dir)
    ctrl.rtss_path = str(rtss_dir / "RTSSHooks64.dll")
    ctrl.logger = StubLogger()
    ctrl.update_profiles_calls = 0

    def _update_profiles():
        ctrl.update_profiles_calls += 1

    ctrl.LoadProfile = lambda *a, **k: None
    ctrl.SaveProfile = lambda *a, **k: None
    ctrl.GetProfileProperty = lambda *a, **k: False
    ctrl.SetProfileProperty = lambda *a, **k: True
    ctrl.DeleteProfile = lambda *a, **k: None
    ctrl.ResetProfile = lambda *a, **k: None
    ctrl.UpdateProfiles = _update_profiles
    ctrl.SetFlags = lambda *a, **k: 0
    return ctrl


class _FakeEnum:
    """Stand-in for a .NET enum type: any member access returns a stable
    string key (``<TypeName>.<Member>``) so dict keying and equality work."""

    def __init__(self, name):
        object.__setattr__(self, "_fake_name", name)

    def __getattr__(self, item):
        if item.startswith("_"):
            raise AttributeError(item)
        return f"{self._fake_name}.{item}"

    def __str__(self):
        return self._fake_name

    def __repr__(self):
        return f"<FakeEnum {self._fake_name}>"


class FakeComputer:
    """Stand-in for LibreHardwareMonitor.Hardware.Computer."""

    def __init__(self, *args, **kwargs):
        self.is_open = False
        self._hardware = []

    def Open(self):
        self.is_open = True

    def Close(self):
        self.is_open = False

    @property
    def Hardware(self):
        return self._hardware


@pytest.fixture
def fake_lhm(monkeypatch):
    """Pretend the LHM .NET assembly is already loaded, returning fake
    Computer/SensorType/HardwareType types from core.lhm_loader."""
    import core.lhm_loader as lhm_loader

    fake_computer = FakeComputer
    fake_sensor_type = _FakeEnum("SensorType")
    fake_hardware_type = _FakeEnum("HardwareType")

    monkeypatch.setattr(lhm_loader, "_LOADED", True)
    monkeypatch.setattr(lhm_loader, "_Computer", fake_computer)
    monkeypatch.setattr(lhm_loader, "_SensorType", fake_sensor_type)
    monkeypatch.setattr(lhm_loader, "_HardwareType", fake_hardware_type)
    return fake_computer, fake_sensor_type, fake_hardware_type
