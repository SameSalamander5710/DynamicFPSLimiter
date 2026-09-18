"""Regression tests: route background-thread dpg.* calls through the GuiQueue.

DearPyGui is not thread-safe: every dpg.* call must run on the thread that owns
the render context. The pre-release audit found that the monitoring/plotting/
autopilot threads (and the LibreHardwareMonitor poll thread) still called
DearPyGui directly. These tests pin the routing fix:

- ``autopilot_on_check`` accepts a ``gui_submit`` callable and defers its
  dpg.* / profile-load / start-stop work through it (direct calls kept only when
  ``gui_submit`` is None, for tests and legacy callers).
- ``LHMSensor`` defers its ``ReadingsText`` update via an attached GuiQueue.
- ``app.py`` submits all loop dpg work through a single ``_gui_submit`` helper.
"""
from pathlib import Path

from conftest import StubLogger
from core.autopilot import autopilot_on_check

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
APP = SRC_DIR / "core" / "app.py"


class _FakeProfilesConfig:
    def __init__(self, sections):
        self._sections = list(sections)

    def sections(self):
        return list(self._sections)

    def __contains__(self, name):
        return name in self._sections


class _FakeCM:
    def __init__(self, profiles=("GameA", "GameB")):
        self.profiles_config = _FakeProfilesConfig(profiles)
        self.autopilot_only_profiles = False
        self.current_profile = "Global"
        self.loaded = []

    def load_profile_callback(self, sender, profile, user_data):
        self.loaded.append(profile)
        self.current_profile = profile

    def apply_current_input_values(self):
        pass


class _RecordingSubmit:
    """Records (fn, args, kwargs) instead of executing the callables."""

    def __init__(self):
        self.calls = []

    def __call__(self, fn, *args, **kwargs):
        self.calls.append((fn, args, kwargs))


class _FakeRTSS:
    def __init__(self, result=(60.0, "GameA"), rtss_up=True):
        self._result = result
        self._up = rtss_up

    def is_rtss_running(self):
        return self._up

    def get_fps_for_active_window(self):
        return self._result


def _run_autopilot(fake_dpg, submit=None, *, process="GameA", running=False,
                   rtss_up=True, autopilot_only=False):
    cm = _FakeCM()
    cm.autopilot_only_profiles = autopilot_only
    rtss = _FakeRTSS(result=(60.0, process), rtss_up=rtss_up)
    logger = StubLogger()
    starts = []

    def start_stop_callback(sender, app_data, user_data):
        starts.append(user_data)

    autopilot_on_check(cm, rtss, fake_dpg, logger, running, start_stop_callback,
                       gui_submit=submit)
    return cm, logger, starts, start_stop_callback


def test_autopilot_specific_profile_submits_gui_calls_to_queue(fake_dpg, stub_logger):
    submit = _RecordingSubmit()
    cm, logger, starts, start_cb = _run_autopilot(
        fake_dpg, submit=submit, process="GameA", running=False)

    # Dropdown update, profile load and start/stop are queued, in order.
    assert len(submit.calls) == 3
    fn, args, _ = submit.calls[0]
    assert fn == fake_dpg.set_value and args == ("profile_dropdown", "GameA")
    fn, args, _ = submit.calls[1]
    assert fn == cm.load_profile_callback and args == (None, "GameA", None)
    fn, args, _ = submit.calls[2]
    assert fn == start_cb and args == (None, None, cm)

    # Nothing ran directly on the calling (autopilot) thread.
    assert fake_dpg.calls == []
    assert cm.loaded == []
    assert starts == []


def test_autopilot_global_profile_submits_to_queue(fake_dpg, stub_logger):
    submit = _RecordingSubmit()
    cm, logger, starts, start_cb = _run_autopilot(
        fake_dpg, submit=submit, process="Other.exe", running=False)

    assert len(submit.calls) == 3
    fn, args, _ = submit.calls[0]
    assert fn == fake_dpg.set_value and args == ("profile_dropdown", "Global")
    fn, args, _ = submit.calls[1]
    assert fn == cm.load_profile_callback and args == (None, "Global", None)
    assert submit.calls[2][0] == start_cb


def test_autopilot_legacy_only_profiles_submits_to_queue(fake_dpg, stub_logger):
    submit = _RecordingSubmit()
    _run_autopilot(fake_dpg, submit=submit, process="GameA", running=False,
                   autopilot_only=True)
    assert len(submit.calls) == 3


def test_autopilot_legacy_ignores_non_profile_process(fake_dpg, stub_logger):
    submit = _RecordingSubmit()
    _run_autopilot(fake_dpg, submit=submit, process="Other.exe", running=False,
                   autopilot_only=True)
    assert submit.calls == []
    assert fake_dpg.calls == []


def test_autopilot_skips_start_when_already_running(fake_dpg, stub_logger):
    submit = _RecordingSubmit()
    starts = []
    cm = _FakeCM()
    rtss = _FakeRTSS(result=(60.0, "GameA"), rtss_up=True)

    def start_stop_callback(sender, app_data, user_data):
        starts.append(user_data)

    autopilot_on_check(cm, rtss, fake_dpg, stub_logger, True, start_stop_callback,
                       gui_submit=submit)
    # Profile switch is queued, but start/stop is NOT (already running).
    assert [s[0] for s in submit.calls] == [fake_dpg.set_value, cm.load_profile_callback]
    assert starts == []


def test_autopilot_runs_directly_without_gui_submit(fake_dpg, stub_logger):
    cm, logger, starts, start_cb = _run_autopilot(fake_dpg, submit=None,
                                                  process="GameA", running=False)
    assert cm.loaded == ["GameA"]
    assert starts == [cm]
    set_values = [c[1] for c in fake_dpg.calls if c[0] == "set_value"]
    assert ("profile_dropdown", "GameA") in set_values


def test_autopilot_returns_silently_when_rtss_down(fake_dpg, stub_logger):
    submit = _RecordingSubmit()
    _run_autopilot(fake_dpg, submit=submit, rtss_up=False)
    assert submit.calls == []
    assert fake_dpg.calls == []


def _make_lhm_sensor(stub_logger, fake_dpg):
    from core import librehardwaremonitor as lhm_mod
    return lhm_mod.LHMSensor(lambda: True, stub_logger, fake_dpg, {},
                             interval=0.01, base_dir=None)


def test_lhm_submit_dpg_deferred_via_gui_queue(fake_lhm, stub_logger, fake_dpg):
    from core.gui_queue import GuiQueue
    sensor = _make_lhm_sensor(stub_logger, fake_dpg)
    queue = GuiQueue()
    sensor.set_gui_queue(queue)

    sensor._submit_dpg(fake_dpg.set_value, "ReadingsText", "hello")
    assert fake_dpg.calls == []  # not executed on the poll thread
    assert "ReadingsText" not in fake_dpg.values

    queue.drain()  # the main render thread runs it
    assert fake_dpg.values.get("ReadingsText") == "hello"


def test_lhm_submit_dpg_runs_directly_without_queue(fake_lhm, stub_logger, fake_dpg):
    sensor = _make_lhm_sensor(stub_logger, fake_dpg)
    sensor._submit_dpg(fake_dpg.set_value, "ReadingsText", "hi")
    assert fake_dpg.values.get("ReadingsText") == "hi"


def test_lhm_poll_loop_uses_gui_queue_submit():
    src = (SRC_DIR / "core" / "librehardwaremonitor.py").read_text(encoding="utf-8")
    assert 'self._submit_dpg(self.dpg.set_value, "ReadingsText", readings)' in src
    assert 'self.dpg.set_value("ReadingsText"' not in src


def test_app_wires_gui_submit_through_loops():
    src = APP.read_text(encoding="utf-8")
    assert "def _gui_submit(fn, *args, **kwargs):" in src
    assert "gui_queue.submit(fn, *args, **kwargs)" in src
    for needle in (
        "_gui_submit(_load_profile_on_gui",
        "_gui_submit(_update_legend_labels",
        "_gui_submit(update_plot_FPS",
        "_gui_submit(update_plot_usage",
        "_gui_submit(fps_utils.update_summary_statistics)",
        "_gui_submit(_update_idle_ui)",
        "_gui_submit(_force_open_headers)",
        "gui_submit=_gui_submit",
        "lhm_sensor.set_gui_queue(gui_queue)",
    ):
        assert needle in src, needle


def test_autopilot_on_check_accepts_gui_submit_parameter():
    import inspect
    assert "gui_submit" in inspect.signature(autopilot_on_check).parameters