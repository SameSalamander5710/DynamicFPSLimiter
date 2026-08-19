"""F7 regression tests: LHM Computer lifecycle.

- LHMSensor.start() after stop() must re-open the computer (previously the
  poll loop iterated a Computer that had already been Closed).
- A double start() must not double-open.
- get_all_sensor_infos() must close its one-shot Computer (previously leaked),
  even when enumeration raises.
"""
import pytest

from core import librehardwaremonitor as lhm_mod


class _FakeHardwareType:
    Cpu = "Cpu"
    GpuAmd = "GpuAmd"
    GpuNvidia = "GpuNvidia"


class _FakeSensorType:
    Load = "Load"
    Temperature = "Temperature"
    Power = "Power"


class _FakeHardware:
    def __init__(self):
        self.Name = "FakeCPU"
        self.HardwareType = _FakeHardwareType.Cpu
        self.Sensors = []

    def Update(self):
        pass


class _FakeComputer:
    created = []

    def __init__(self):
        self.IsGpuEnabled = False
        self.IsCpuEnabled = False
        self.Hardware = [_FakeHardware()]
        self.open_calls = 0
        self.close_calls = 0
        _FakeComputer.created.append(self)

    def Open(self):
        self.open_calls += 1

    def Close(self):
        self.close_calls += 1


def _install_fake_lhm(monkeypatch):
    _FakeComputer.created.clear()
    monkeypatch.setattr(
        lhm_mod, "ensure_loaded",
        lambda base_dir=None, logger=None: (_FakeComputer, _FakeSensorType, _FakeHardwareType),
    )
    monkeypatch.setattr(
        lhm_mod, "get_types",
        lambda base_dir=None: (_FakeComputer, _FakeSensorType, _FakeHardwareType),
    )


def _make_sensor(stub_logger, fake_dpg):
    return lhm_mod.LHMSensor(lambda: True, stub_logger, fake_dpg, {}, interval=0.01, base_dir=None)


def test_start_after_stop_reopens_computer(monkeypatch, stub_logger, fake_dpg):
    _install_fake_lhm(monkeypatch)
    sensor = _make_sensor(stub_logger, fake_dpg)
    first = sensor.computer
    assert first.open_calls == 1
    assert sensor._computer_open is True

    sensor.start()
    sensor.stop()
    assert first.close_calls == 1
    assert sensor._computer_open is False

    sensor.start()
    assert sensor.computer is not first
    assert sensor.computer.open_calls == 1
    assert sensor._computer_open is True
    sensor.stop()
    assert sensor.computer.close_calls == 1


def test_double_start_does_not_double_open(monkeypatch, stub_logger, fake_dpg):
    _install_fake_lhm(monkeypatch)
    sensor = _make_sensor(stub_logger, fake_dpg)
    sensor.start()
    sensor.start()
    assert sensor.computer.open_calls == 1
    sensor.stop()


def test_get_all_sensor_infos_closes_its_computer(monkeypatch):
    _install_fake_lhm(monkeypatch)
    infos = lhm_mod.get_all_sensor_infos(None)
    assert infos == []
    assert len(_FakeComputer.created) == 1
    assert _FakeComputer.created[0].close_calls == 1


def test_get_all_sensor_infos_closes_on_enumeration_error(monkeypatch):
    class _ExplodingComputer:
        def __init__(self):
            self.IsGpuEnabled = False
            self.IsCpuEnabled = False
            self.close_calls = 0
            _FakeComputer.created.append(self)

        @property
        def Hardware(self):
            raise RuntimeError("boom")

        def Open(self):
            pass

        def Close(self):
            self.close_calls += 1

    _install_fake_lhm(monkeypatch)
    monkeypatch.setattr(
        lhm_mod, "get_types",
        lambda base_dir=None: (_ExplodingComputer, _FakeSensorType, _FakeHardwareType),
    )
    with pytest.raises(RuntimeError, match="boom"):
        lhm_mod.get_all_sensor_infos(None)
    assert _FakeComputer.created[-1].close_calls == 1
