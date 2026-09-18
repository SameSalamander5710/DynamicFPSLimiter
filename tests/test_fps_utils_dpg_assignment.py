"""Regression: FPSUtils.__init__ must assign ``self.dpg = dpg`` directly.

The previous ``dpg or dpg`` was a no-op that never provided the documented
global fallback; callers pass dpg explicitly today, so plain assignment is
correct and identity must be preserved exactly."""
from types import SimpleNamespace


def test_fps_utils_stores_passed_dpg_identity(fake_dpg, stub_logger, fake_lhm):
    from core.fps_utils import FPSUtils

    stub = object()
    lhm_sensor = SimpleNamespace(cpu_history_long={}, gpu_history_long={})
    cm = SimpleNamespace()
    fps_utils = FPSUtils(cm, lhm_sensor, stub_logger, stub, 610, base_dir=None)

    assert fps_utils.dpg is stub