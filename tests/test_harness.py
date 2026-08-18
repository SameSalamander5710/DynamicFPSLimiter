"""Verification tests for the test harness itself (the stub fixtures in
tests/conftest.py). These must pass before any Phase 2 flaw test relies on
the fixtures."""
from pathlib import Path


def test_fake_dpg_value_roundtrip(fake_dpg):
    fake_dpg.set_value("input_maxcap", 114)
    assert fake_dpg.get_value("input_maxcap") == 114
    assert fake_dpg.does_item_exist("input_maxcap")
    fake_dpg.delete_item("input_maxcap")
    assert not fake_dpg.does_item_exist("input_maxcap")
    assert fake_dpg.get_value("missing") is None


def test_fake_dpg_records_calls_with_thread(fake_dpg):
    fake_dpg.set_value("x", 1)
    name, args, kwargs, thread = fake_dpg.calls[-1]
    assert name == "set_value"
    assert args == ("x", 1)
    assert kwargs == {}
    assert thread


def test_fake_dpg_unknown_api_is_noop(fake_dpg):
    result = fake_dpg.some_future_api(1, 2, three=3)
    assert result is None
    assert fake_dpg.calls[-1][0] == "some_future_api"


def test_fake_dpg_draw_layer_context_manager(fake_dpg):
    with fake_dpg.draw_layer(tag="Foreground", parent="fps_cap_drawlist"):
        fake_dpg.draw_circle((10, 20), 7, fill=(200, 200, 200), parent="Foreground")
    assert fake_dpg.does_item_exist("Foreground")
    draw_calls = [c for c in fake_dpg.calls if c[0] == "draw_circle"]
    assert len(draw_calls) == 1


def test_fake_dpg_get_item_configuration_returns_dict(fake_dpg):
    config = fake_dpg.get_item_configuration("input_maxcap")
    assert isinstance(config, dict)


def test_stub_logger(stub_logger):
    stub_logger.add_log("hello")
    stub_logger.add_log(42)
    assert stub_logger.messages == ["hello", "42"]


def test_rtss_stub_file_writer(rtss_stub):
    # File-based method runs for real; update=False must not touch the DLL.
    assert rtss_stub.set_limit_denominator("Global", 1000, update=False) is True
    profile = Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    content = profile.read_text(encoding="utf-8")
    assert "LimitDenominator=1000" in content
    assert rtss_stub.update_profiles_calls == 0

    # update=True must go through the (no-op) UpdateProfiles exactly once.
    assert rtss_stub.set_limit_denominator("Global", 100, update=True) is True
    assert rtss_stub.update_profiles_calls == 1
    assert "LimitDenominator=100" in profile.read_text(encoding="utf-8")


def test_rtss_stub_dll_methods_are_noops(rtss_stub):
    assert rtss_stub.LoadProfile("Global") is None
    assert rtss_stub.SetProfileProperty("Global", "FramerateLimit", "144") is True
    assert rtss_stub.GetProfileProperty("Global", "FramerateLimit") is False


def test_fake_lhm(fake_lhm):
    computer_cls, sensor_type, hardware_type = fake_lhm

    comp = computer_cls()
    comp.Open()
    assert comp.is_open
    comp.Close()
    assert not comp.is_open

    # Member access returns stable, distinct string keys.
    assert hardware_type.Cpu == hardware_type.Cpu
    assert sensor_type.Temperature != sensor_type.Utilization
