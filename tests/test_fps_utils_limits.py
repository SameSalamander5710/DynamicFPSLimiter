"""F5 regression tests: current_stepped_limits() must be total — never return
None (and never an empty list) for any capmethod, so consumers like
``max(...)``/``min(...)``/``set(...)`` cannot crash."""
from decimal import Decimal
from types import SimpleNamespace


def _make_fps_utils(fake_dpg, stub_logger, cm, fake_lhm):
    from core.fps_utils import FPSUtils

    lhm_sensor = SimpleNamespace(cpu_history_long={}, gpu_history_long={})
    return FPSUtils(cm, lhm_sensor, stub_logger, fake_dpg, 610, base_dir=None)


def _set_ladder_inputs(fake_dpg, method, custom=""):
    fake_dpg.set_value("input_maxcap", 100)
    fake_dpg.set_value("input_mincap", 40)
    fake_dpg.set_value("input_capstep", 10)
    fake_dpg.set_value("input_capratio", 10)
    fake_dpg.set_value("input_capmethod", method)
    fake_dpg.set_value("input_customfpslimits", custom)


def test_custom_method_valid_string_returns_parsed(fake_dpg, stub_logger, fake_lhm):
    cm = SimpleNamespace(
        parse_and_normalize_string_to_decimal_set=lambda s: [Decimal("30"), Decimal("45"), Decimal("60")]
    )
    fu = _make_fps_utils(fake_dpg, stub_logger, cm, fake_lhm)
    _set_ladder_inputs(fake_dpg, "custom", "30, 45, 60")
    assert fu.current_stepped_limits() == [Decimal("30"), Decimal("45"), Decimal("60")]


def test_custom_method_parse_failure_falls_back_to_stepped(fake_dpg, stub_logger, fake_lhm):
    def boom(s):
        raise ValueError("bad")

    cm = SimpleNamespace(parse_and_normalize_string_to_decimal_set=boom)
    fu = _make_fps_utils(fake_dpg, stub_logger, cm, fake_lhm)
    _set_ladder_inputs(fake_dpg, "custom", "not, numbers")

    result = fu.current_stepped_limits()
    assert result == fu.make_stepped_values(100, 40, 10)
    assert len(result) >= 2
    assert any("Error parsing custom FPS limits" in m for m in stub_logger.messages)


def test_custom_method_empty_parse_result_falls_back(fake_dpg, stub_logger, fake_lhm):
    cm = SimpleNamespace(parse_and_normalize_string_to_decimal_set=lambda s: [])
    fu = _make_fps_utils(fake_dpg, stub_logger, cm, fake_lhm)
    _set_ladder_inputs(fake_dpg, "custom", "   ")

    result = fu.current_stepped_limits()
    assert result == fu.make_stepped_values(100, 40, 10)
    assert any("falling back" in m for m in stub_logger.messages)


def test_custom_method_empty_string_falls_back(fake_dpg, stub_logger, fake_lhm):
    cm = SimpleNamespace(parse_and_normalize_string_to_decimal_set=lambda s: [Decimal("1")])
    fu = _make_fps_utils(fake_dpg, stub_logger, cm, fake_lhm)
    _set_ladder_inputs(fake_dpg, "custom", "")

    assert fu.current_stepped_limits() == fu.make_stepped_values(100, 40, 10)


def test_unknown_method_falls_back_to_stepped(fake_dpg, stub_logger, fake_lhm):
    fu = _make_fps_utils(fake_dpg, stub_logger, SimpleNamespace(), fake_lhm)
    _set_ladder_inputs(fake_dpg, "bogus")

    result = fu.current_stepped_limits()
    assert result == fu.make_stepped_values(100, 40, 10)
    assert any("Unknown FPS cap method" in m for m in stub_logger.messages)


def test_step_method_unchanged(fake_dpg, stub_logger, fake_lhm):
    fu = _make_fps_utils(fake_dpg, stub_logger, SimpleNamespace(), fake_lhm)
    _set_ladder_inputs(fake_dpg, "step")
    assert fu.current_stepped_limits() == [40, 50, 60, 70, 80, 90, 100]


def test_ratio_method_unchanged(fake_dpg, stub_logger, fake_lhm):
    fu = _make_fps_utils(fake_dpg, stub_logger, SimpleNamespace(), fake_lhm)
    _set_ladder_inputs(fake_dpg, "ratio")
    assert fu.current_stepped_limits() == fu.make_ratioed_values(100, 40, 10)
