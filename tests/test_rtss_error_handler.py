"""A3: RTSSController takes an injected error handler instead of importing
show_rtss_error_and_exit from core.launch_popup at module import time.

The real handler (show_rtss_error_and_exit) shows a popup and exits the
process, so when the DLL load fails it never returns. These tests wire a
harmless sentinel handler (which does return) and stub out the DLL-API
setup step so __init__ completes; the no-handler path must re-raise the
original OSError instead of silently continuing.
"""
from pathlib import Path

import pytest

from conftest import requires_win32
from core import rtss_functions
from core.rtss_functions import RTSSController

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


def _raise_oserror(*args, **kwargs):
    raise OSError("fake missing RTSSHooks64.dll")


@requires_win32
def test_error_handler_called_when_rtss_dll_missing(monkeypatch, stub_logger):
    calls = []

    def sentinel_handler(path):
        calls.append(path)

    monkeypatch.setattr(rtss_functions.ctypes, "WinDLL", _raise_oserror)
    monkeypatch.setattr(RTSSController, "_setup_functions", lambda self: None)

    controller = RTSSController(stub_logger, error_handler=sentinel_handler)

    assert calls == [controller.rtss_path]
    assert controller.rtss_path.endswith("RTSSHooks64.dll")


@requires_win32
def test_missing_rtss_dll_raises_without_error_handler(monkeypatch, stub_logger):
    monkeypatch.setattr(rtss_functions.ctypes, "WinDLL", _raise_oserror)

    with pytest.raises(OSError):
        RTSSController(stub_logger)


def test_rtss_functions_has_no_launch_popup_reference():
    src = (SRC_DIR / "core" / "rtss_functions.py").read_text(encoding="utf-8")
    assert "launch_popup" not in src
    assert "show_rtss_error_and_exit" not in src


def test_dfl_v5_injects_rtss_error_handler():
    src = (SRC_DIR / "core" / "DFL_v5.py").read_text(encoding="utf-8")
    assert "error_handler=show_rtss_error_and_exit" in src