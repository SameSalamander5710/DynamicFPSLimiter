"""DPI awareness regression guards (L15).

DPI must be set exactly once, in ``src/__main__.py`` ``run_app()``, before the
app module is imported. It must NOT be a module-level side effect of importing
core modules (``core.app`` imports run the application, so it cannot be
imported in-process here — the same reason ``test_dfl_main_loop.py`` guards its
wiring at the source level).

``core.launch_popup`` IS importable, so we additionally verify at runtime (with
a ``windll`` spy) that importing it never loads ``shcore``.
"""
import importlib
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"

DPI_CALL = "windll.shcore.SetProcessDpiAwareness(2)"


def _source(rel_path: str) -> str:
    return (SRC_DIR / rel_path).read_text(encoding="utf-8")


def test_app_has_no_dpi_call_at_import():
    src = _source("core/app.py")
    assert "SetProcessDpiAwareness" not in src
    assert "shcore" not in src


def test_launch_popup_has_no_dpi_call_at_import():
    src = _source("core/launch_popup.py")
    assert "SetProcessDpiAwareness" not in src
    assert "shcore" not in src
    assert "import ctypes" not in src


def test_main_sets_dpi_once_in_run_app():
    """The only DPI call must live inside run_app(), guarded by try/except."""
    src = _source("__main__.py")
    lines = src.splitlines()

    run_app_idx = next(
        i for i, line in enumerate(lines) if line.startswith("def run_app(")
    )
    app_block = "\n".join(lines[run_app_idx:])

    assert app_block.count(DPI_CALL) == 1
    assert "SetProcessDpiAwareness" in app_block
    assert "try:" in app_block
    assert "except" in app_block


@pytest.mark.win32
def test_launch_popup_import_touches_no_shcore(monkeypatch):
    import ctypes

    loaded = []

    class _SpyLoader:
        _dlltype = ctypes.WinDLL

        def __getattr__(self, name):
            loaded.append(name)
            return self._dlltype(name)

    monkeypatch.setattr(ctypes, "windll", _SpyLoader())

    if "core.launch_popup" in sys.modules:
        del sys.modules["core.launch_popup"]

    importlib.import_module("core.launch_popup")
    assert "shcore" not in loaded