"""L16: drag helper extraction – verify no full TrayManager is constructed for popup drag.

Two complementary checks:
1. Source-level: ``launch_popup.py`` no longer contains a ``TrayManager(``
   call inside the drag-handler class path.
2. Runtime monkeypatch: ``TrayManager.__init__`` is replaced with a
   sentinel that raises, and the new ``ViewportDragHandler`` (along with
   the ``PopupDragHandler`` name which is now gone) must work without
   triggering it.
"""
import ast
import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCH_POPUP_SRC = REPO_ROOT / "src" / "core" / "launch_popup.py"


# ---------------------------------------------------------------------------
# 1. Source-level check: no TrayManager( inside a drag-handler class
# ---------------------------------------------------------------------------

def test_launch_popup_source_no_tray_manager_in_drag_handler():
    """``launch_popup.py`` must not construct a ``TrayManager`` inside
    the popup-drag-handler class (class body or ``__init__``)."""
    tree = ast.parse(LAUNCH_POPUP_SRC.read_text(encoding="utf-8"))

    class_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    for cls in class_nodes:
        if not cls.name.endswith("DragHandler"):
            continue
        for node in ast.walk(cls):
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                assert name != "TrayManager", (
                    f"Class {cls.name} still constructs TrayManager (line {node.lineno})"
                )


def test_launch_popup_source_imports_drag_helper():
    """``launch_popup.py`` must import from the new drag_helper module."""
    src = LAUNCH_POPUP_SRC.read_text(encoding="utf-8")
    assert "from core.drag_helper import ViewportDragHandler" in src


# ---------------------------------------------------------------------------
# 2. Runtime check: TrayManager constructor raises if accidentally called
# ---------------------------------------------------------------------------

class _TrayManagerPoison:
    """Replacement for TrayManager that raises on instantiation."""
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "TrayManager was instantiated – drag helper must not need it"
        )


def test_viewport_drag_handler_works_without_tray_manager(
    fake_dpg, monkeypatch
):
    """Instantiating ``ViewportDragHandler`` must NOT instantiate a
    ``TrayManager`` (verified by monkeypatching the constructor to raise)."""
    import core.tray_functions as tray_mod
    import core.drag_helper as drag_mod
    monkeypatch.setattr(
        tray_mod.TrayManager, "__init__", _TrayManagerPoison.__init__
    )
    # Stub Win32 helpers so callbacks run under fake_dpg.
    monkeypatch.setattr(drag_mod, "get_mouse_screen_pos", lambda: (100, 50))
    monkeypatch.setattr(drag_mod, "is_left_mouse_button_down", lambda: False)
    fake_dpg.get_mouse_pos = lambda local=True: (100, 30)
    fake_dpg.get_viewport_pos = lambda: (0, 0)
    fake_dpg.set_viewport_pos = lambda pos: None
    fake_dpg.is_mouse_button_down = lambda button=0: False

    from core.drag_helper import ViewportDragHandler

    handler = ViewportDragHandler(viewport_width=420)
    assert hasattr(handler, "on_mouse_click")
    assert hasattr(handler, "drag_viewport")
    assert hasattr(handler, "on_mouse_release")

    # Exercise the callbacks with fake_dpg – they must not raise.
    handler.on_mouse_click(None, None, None)
    handler.drag_viewport(None, None, None)
    handler.on_mouse_release(None, None, None)


def test_launch_popup_importable_without_tray_manager_drag(
    fake_dpg, monkeypatch
):
    """Importing ``launch_popup`` and exercising the drag-handler path must
    not require a real ``TrayManager`` instance."""
    import core.tray_functions as tray_mod
    import importlib
    import sys

    monkeypatch.setattr(
        tray_mod.TrayManager, "__init__", _TrayManagerPoison.__init__
    )

    # Force a fresh import so the monkeypatch is visible at import time.
    if "core.launch_popup" in sys.modules:
        mod = importlib.reload(sys.modules["core.launch_popup"])
    else:
        mod = importlib.import_module("core.launch_popup")

    # PopupDragHandler should no longer exist (replaced by ViewportDragHandler).
    assert not hasattr(mod, "PopupDragHandler"), (
        "PopupDragHandler should have been removed"
    )
    assert hasattr(mod, "ViewportDragHandler")
