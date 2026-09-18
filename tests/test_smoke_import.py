"""Import-time smoke tests.

Every importable core module must import cleanly without:
- creating a DearPyGui context,
- loading the LHM .NET assembly,
- loading the RTSS DLL,
- starting background threads.

Excluded on purpose:
- ``core.DFL_v5``: importing it *runs* the application (module-level GUI
  setup, threads, RTSS enable). See docs/status.md §2.1 (A1) for the split that
  makes the app importable.
- ``core.video2gif`` / ``core.backup_snippets``: gitignored local utilities.
"""
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

CORE_MODULES = [
    "core.autopilot",
    "core.autostart",
    "core.cap_policy",
    "core.config_manager",
    "core.cpu_monitor",
    "core.fps_utils",
    "core.gpu_monitor",
    "core.idle_timer",
    "core.launch_popup",
    "core.lhm_loader",
    "core.librehardwaremonitor",
    "core.logger",
    "core.pre_launch",
    "core.rtss_functions",
    "core.rtss_interface",
    "core.themes",
    "core.tooltips",
    "core.tray_functions",
    "core.warning",
]

# Modules using Windows-only APIs (ctypes.windll / winreg / wintypes) at
# import time; they can only be imported on Windows.
WIN32_ONLY_MODULES = {
    "core.gpu_monitor",
    "core.launch_popup",
    "core.rtss_functions",
    "core.rtss_interface",
}


def _platform_modules():
    if sys.platform == "win32":
        return CORE_MODULES
    return [m for m in CORE_MODULES if m not in WIN32_ONLY_MODULES]


@pytest.mark.parametrize("module_name", _platform_modules())
def test_core_module_imports(module_name):
    mod = importlib.import_module(module_name)
    assert mod is not None


@pytest.mark.win32
def test_expected_public_names():
    from core.config_manager import ConfigManager
    from core.cpu_monitor import CPUUsageMonitor
    from core.fps_utils import FPSUtils
    from core.gpu_monitor import GPUUsageMonitor
    from core.librehardwaremonitor import LHMSensor
    from core.rtss_functions import RTSSController
    from core.tray_functions import TrayManager

    for cls in (
        ConfigManager,
        CPUUsageMonitor,
        FPSUtils,
        GPUUsageMonitor,
        LHMSensor,
        RTSSController,
        TrayManager,
    ):
        assert isinstance(cls, type)


# Runs the imports in a fresh interpreter so no test-runner state (threads,
# partially imported modules) can mask import-time side effects.
SMOKE_SCRIPT = """
import ctypes
import json
import sys
import threading

sys.path.insert(0, sys.argv[1])
modules = json.loads(sys.argv[2])

import dearpygui.dearpygui as dpg

dpg_context_calls = []
_orig_create_context = dpg.create_context

def _spy_create_context(*args, **kwargs):
    dpg_context_calls.append(1)
    return _orig_create_context(*args, **kwargs)

dpg.create_context = _spy_create_context

windll_paths = []
_orig_windll = ctypes.WinDLL

def _spy_windll(name, *args, **kwargs):
    windll_paths.append(str(name))
    return _orig_windll(name, *args, **kwargs)

ctypes.WinDLL = _spy_windll

threads_before = threading.active_count()

results = {}
for name in modules:
    try:
        __import__(name)
        results[name] = "ok"
    except Exception as exc:
        results[name] = f"{type(exc).__name__}: {exc}"

threads_after = threading.active_count()

import core.lhm_loader as lhm_loader

print(json.dumps({
    "imports": results,
    "dpg_context_calls": len(dpg_context_calls),
    "windll_paths": windll_paths,
    "threads_before": threads_before,
    "threads_after": threads_after,
    "lhm_loaded": lhm_loader._LOADED,
}))
"""


@pytest.mark.win32
def test_no_import_time_side_effects():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            SMOKE_SCRIPT,
            str(SRC_DIR),
            json.dumps(CORE_MODULES),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout.strip().splitlines()[-1])

    failures = {m: err for m, err in report["imports"].items() if err != "ok"}
    assert not failures, f"modules failed to import: {failures}"
    assert report["dpg_context_calls"] == 0, (
        "a DearPyGui context was created at import time"
    )
    assert not any("RTSS" in p for p in report["windll_paths"]), (
        f"RTSS DLL loaded at import time: {report['windll_paths']}"
    )
    assert report["threads_after"] <= report["threads_before"], (
        "importing core modules started background threads"
    )
    assert report["lhm_loaded"] is False, (
        "LHM .NET assembly was loaded at import time"
    )
