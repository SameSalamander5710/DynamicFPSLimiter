"""A2: dpg is injected into core modules instead of imported at module top.

app.py is the single module that imports ``dearpygui`` and hands the
instance to every submodule (via constructor params or ``set_dpg``). These
tests guard (1) the source invariant that no other core module keeps the
module-level import and (2) that the injected fake ``dpg`` is actually used
by the refactored call paths.
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
CORE_DIR = SRC_DIR / "core"

MODULE_LEVEL_IMPORT = "import dearpygui.dearpygui as dpg"

# Every core module (except app.py) must drop the module-level dpg import.
NON_ORCHESTRATOR_MODULES = [
    "autostart.py",
    "cpu_monitor.py",
    "rtss_interface.py",
    "fps_utils.py",
    "config_manager.py",
    "logger.py",
    "themes.py",
    "tray_functions.py",
    "drag_helper.py",
    "launch_popup.py",
]


def _has_module_level_dpg_import(src: str) -> bool:
    return any(
        line.startswith(MODULE_LEVEL_IMPORT)
        for line in src.splitlines()
    )


@pytest.mark.parametrize("filename", NON_ORCHESTRATOR_MODULES)
def test_no_module_level_dpg_import(filename):
    src = (CORE_DIR / filename).read_text(encoding="utf-8")
    assert not _has_module_level_dpg_import(src), (
        f"{filename} still imports dpg at module level"
    )


def test_app_keeps_exactly_one_module_level_dpg_import():
    src = (CORE_DIR / "app.py").read_text(encoding="utf-8")
    count = sum(
        1 for line in src.splitlines()
        if line.startswith(MODULE_LEVEL_IMPORT)
    )
    assert count == 1


# ---------------------------------------------------------------------------
# Behavioral: the injected dpg (FakeDPG) must be what call paths actually use.
# ---------------------------------------------------------------------------

def test_logger_set_dpg_injects_and_is_used(fake_dpg, monkeypatch):
    import core.logger as logger
    monkeypatch.setattr(logger, "_dpg", None)
    monkeypatch.setattr(logger, "log_messages", ["alpha", "beta"])

    logger.set_dpg(fake_dpg)
    assert logger._dpg is fake_dpg

    fake_dpg.items.add("LogText")  # pretend the log widget exists
    fake_dpg.calls.clear()
    logger._apply_log_text_to_widget()

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert len(set_value_calls) == 1
    assert set_value_calls[0][1][0] == "LogText"
    assert set_value_calls[0][1][1] == "alpha\nbeta"


def test_logger_apply_log_text_without_dpg_does_not_raise(monkeypatch):
    import core.logger as logger
    monkeypatch.setattr(logger, "log_messages", ["x"])
    monkeypatch.setattr(logger, "_dpg", None)

    logger._apply_log_text_to_widget()  # must not raise


def test_drag_handler_uses_injected_dpg(fake_dpg, monkeypatch):
    import core.drag_helper as drag_mod
    monkeypatch.setattr(drag_mod, "get_mouse_screen_pos", lambda: (100, 50))
    monkeypatch.setattr(drag_mod, "is_left_mouse_button_down", lambda: False)

    def _get_mouse_pos(local=True):
        fake_dpg._record("get_mouse_pos", (local,), {})
        return (100, 30)

    def _is_mouse_button_down(button=0):
        fake_dpg._record("is_mouse_button_down", (button,), {})
        return False

    fake_dpg.get_mouse_pos = _get_mouse_pos
    fake_dpg.get_viewport_pos = lambda: (0, 0)
    fake_dpg.set_viewport_pos = lambda pos: None
    fake_dpg.is_mouse_button_down = _is_mouse_button_down
    fake_dpg.calls.clear()

    from core.drag_helper import ViewportDragHandler

    handler = ViewportDragHandler(viewport_width=420, dpg=fake_dpg)
    assert handler.dpg is fake_dpg

    handler.on_mouse_click(None, None, None)
    handler.drag_viewport(None, None, None)
    handler.on_mouse_release(None, None, None)

    # on_mouse_click consults the injected fake instead of a module-level dpg
    # import.
    assert any(c[0] == "get_mouse_pos" for c in fake_dpg.calls)
    assert any(c[0] == "is_mouse_button_down" for c in fake_dpg.calls)


def test_themes_manager_stores_injected_dpg(fake_dpg):
    from core.themes import ThemesManager

    tm = ThemesManager("/nowhere", fake_dpg)
    assert tm.dpg is fake_dpg


def test_tray_manager_stores_injected_dpg(fake_dpg):
    from core.tray_functions import TrayManager

    tray = TrayManager("TestApp", "", None, None, 100, None, dpg=fake_dpg)
    assert tray.dpg is fake_dpg