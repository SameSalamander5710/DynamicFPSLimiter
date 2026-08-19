"""F2 regression tests: a LibreHardwareMonitor load failure must degrade
gracefully (no sensors, monitoring disabled) instead of crashing startup."""
import sys
from types import SimpleNamespace

import pytest

import core.lhm_loader as lhm_loader
import core.librehardwaremonitor as lhm_mod
from core.lhm_loader import LHMLoadError


def _lhm_load_error():
    return LHMLoadError(
        "simulated .NET load failure",
        dll_path=r"C:\fake\LibreHardwareMonitorLib.dll",
    )


def test_ensure_loaded_raises_lhm_load_error_when_addreference_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(lhm_loader, "_LOADED", False)

    def boom(path):
        raise RuntimeError("simulated .NET runtime failure")

    monkeypatch.setattr(lhm_loader.clr, "AddReference", boom)

    with pytest.raises(LHMLoadError) as ei:
        lhm_loader.ensure_loaded(base_dir=str(tmp_path))

    assert "LibreHardwareMonitorLib.dll" in str(ei.value)
    assert ei.value.dll_path
    # A failed load must not be cached as loaded, so a later retry is possible.
    assert lhm_loader._LOADED is False


def test_ensure_loaded_raises_lhm_load_error_when_import_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(lhm_loader, "_LOADED", False)
    monkeypatch.setattr(lhm_loader.clr, "AddReference", lambda path: None)
    # Force the assembly import to fail deterministically.
    monkeypatch.setitem(sys.modules, "LibreHardwareMonitor", None)
    monkeypatch.setitem(sys.modules, "LibreHardwareMonitor.Hardware", None)

    with pytest.raises(LHMLoadError):
        lhm_loader.ensure_loaded(base_dir=str(tmp_path))


def test_get_all_sensor_infos_returns_empty_and_logs_on_lhm_failure(monkeypatch, stub_logger):
    def boom(base_dir=None):
        raise _lhm_load_error()

    monkeypatch.setattr(lhm_mod, "get_types", boom)

    assert lhm_mod.get_all_sensor_infos(None, stub_logger) == []
    assert any("unavailable" in m for m in stub_logger.messages)


def test_config_manager_constructs_without_lhm(monkeypatch, fake_dpg, stub_logger, tmp_path):
    def boom(base_dir=None):
        raise _lhm_load_error()

    monkeypatch.setattr(lhm_mod, "get_types", boom)

    from core.config_manager import ConfigManager

    cm = ConfigManager(
        stub_logger,
        fake_dpg,
        None,  # rtss
        None,  # tray
        SimpleNamespace(themes={}),
        str(tmp_path / "app"),
    )

    assert cm.sensor_infos == []
    assert any("unavailable" in m for m in stub_logger.messages)


def test_lhmsensor_disabled_when_lhm_unavailable(monkeypatch, fake_dpg, stub_logger, tmp_path):
    def boom(base_dir=None, logger=None):
        raise _lhm_load_error()

    monkeypatch.setattr(lhm_mod, "ensure_loaded", boom)

    from core.librehardwaremonitor import LHMSensor

    sensor = LHMSensor(
        lambda: False,
        stub_logger,
        fake_dpg,
        SimpleNamespace(themes={}),
        base_dir=str(tmp_path),
    )

    assert sensor.disabled is True
    assert sensor.computer is None
    assert sensor.SensorType is None
    assert any("unavailable" in m for m in stub_logger.messages)

    # start/stop must be safe no-ops while disabled.
    sensor.start()
    assert sensor._thread is None
    sensor.stop()
    assert sensor.computer is None


def test_fps_utils_constructs_and_evaluates_without_lhm(monkeypatch, fake_dpg, stub_logger, tmp_path):
    def boom(base_dir=None, logger=None):
        raise _lhm_load_error()

    monkeypatch.setattr(lhm_mod, "ensure_loaded", boom)
    import core.fps_utils as fps_utils_mod

    monkeypatch.setattr(fps_utils_mod, "get_types", boom)

    from core.fps_utils import FPSUtils
    from core.librehardwaremonitor import LHMSensor

    sensor = LHMSensor(
        lambda: False,
        stub_logger,
        fake_dpg,
        SimpleNamespace(themes={}),
        base_dir=str(tmp_path),
    )
    fake_dpg.set_value("input_monitoring_method", "LibreHM")
    cm = SimpleNamespace(sensor_infos=[])

    fu = FPSUtils(cm, sensor, stub_logger, fake_dpg, 610, base_dir=str(tmp_path))

    assert fu.SensorType is None
    assert fu.HardwareType is None
    assert fu.evaluate_cap_change([], []) == (False, False)
