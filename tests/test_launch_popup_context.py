"""Regression tests for the launch-popup DearPyGui context lifecycle.

A second ``setup_dearpygui()`` on the same live DearPyGui context crashes
DPG 2.0.0 (access violation, 0xC0000005). The RTSS-missing startup path used
to hit this: `show_loading_popup` creates a context + viewport and calls
`setup_dearpygui()`, then `show_rtss_error_and_exit` called `setup_dearpygui()`
again on that same live context. The error popup must instead tear down the
loading context before it builds its own.
"""
import contextlib
import sys
from pathlib import Path

import pytest

from core import launch_popup as lp

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


class _StubThemes:
    """ThemesManager stand-in: no fonts to load, no theme objects to build."""

    themes = {"main_theme": object()}

    def __init__(self, *args, **kwargs):
        pass

    def create_themes(self):
        pass

    def create_fonts(self, *args, **kwargs):
        return {}

    def bind_font_to_item(self, *args, **kwargs):
        pass


@pytest.fixture
def _popup_env(monkeypatch, fake_dpg):
    """Stub themes and window centering so popups run against the fake dpg."""
    monkeypatch.setattr(lp, "ThemesManager", _StubThemes)
    monkeypatch.setattr(
        lp.TrayManager, "get_centered_viewport_position", staticmethod(lambda w, h: (0, 0))
    )
    # FakeDPG's __getattr__ returns None for `window`; make it a context manager.
    fake_dpg.window = lambda *a, **k: contextlib.nullcontext()
    lp._loading_popup_active = False
    return fake_dpg


def test_loading_popup_marks_context_active_and_hide_clears_it(_popup_env):
    lp.show_loading_popup("Loading", Base_dir="C:\\temp\\app", dpg=_popup_env)
    assert lp._loading_popup_active is True

    lp.hide_loading_popup(dpg=_popup_env)
    assert lp._loading_popup_active is False


def _run_error_popup(fake_dpg, monkeypatch):
    monkeypatch.setattr(lp, "show_missing_rtss_popup", lambda *a, **k: ("popup-shown",))
    with pytest.raises(SystemExit):
        lp.show_rtss_error_and_exit("C:\\fake\\RTSSHooks64.dll", dpg=fake_dpg)


def test_rtss_error_path_tears_down_live_loading_context(_popup_env, monkeypatch):
    lp._loading_popup_active = True  # a live loading context exists

    _run_error_popup(_popup_env, monkeypatch)

    assert lp._loading_popup_active is False
    names = [name for name, _, _, _ in _popup_env.calls]
    # The loading context must be destroyed before the error popup builds a new one.
    assert names.index("destroy_context") < names.index("create_context")


def test_rtss_error_path_skips_teardown_without_loading_popup(_popup_env, monkeypatch):
    lp._loading_popup_active = False  # no loading context is live
    hide_calls = []
    monkeypatch.setattr(lp, "hide_loading_popup", lambda dpg=None: hide_calls.append(dpg))

    _run_error_popup(_popup_env, monkeypatch)

    assert hide_calls == []


def test_source_guards_single_context_lifecycle():
    text = (SRC_DIR / "core" / "launch_popup.py").read_text(encoding="utf-8")
    # show_rtss_error_and_exit must check the "loading popup active" flag and
    # tear the live context down before it creates its own context. Reordering
    # those two lines would re-introduce the double-setup_dearpygui() crash.
    err_block = text[text.index("def show_rtss_error_and_exit") : text.index("def show_loading_popup")]
    assert "_loading_popup_active" in err_block
    assert err_block.index("_loading_popup_active") < err_block.index("create_context")


def test_no_dead_destroy_viewport_call_in_hide_loading_popup():
    text = (SRC_DIR / "core" / "launch_popup.py").read_text(encoding="utf-8")
    hide_block = text[text.index("def hide_loading_popup") : text.index('if __name__ == "__main__"')]
    # destroy_viewport() does not exist in DearPyGui 2.x; it must not be called.
    assert "dpg_mod.destroy_viewport()" not in hide_block
    assert "dpg_mod.destroy_context()" in hide_block