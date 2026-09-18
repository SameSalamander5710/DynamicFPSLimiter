"""L14: AutoStartManager calls subprocess.run with argument lists, never shell=True.

Regression guard: every subprocess.run call must pass a list (program + args)
and never pass ``shell=True``. ``update_if_needed`` must still consume the
captured stdout and returncodes as before.
"""
import pytest

import core.autostart as autostart

FIXED_APP_PATH = "C:\\DynamicFPSLimiter\\DFL.exe"
FIXED_TASK_NAME = "DFL_TestTask"

QUERY_ARGS = ["schtasks", "/Query", "/TN", FIXED_TASK_NAME]
XML_ARGS = ["schtasks", "/Query", "/TN", FIXED_TASK_NAME, "/XML"]
DELETE_ARGS = ["schtasks", "/Delete", "/TN", FIXED_TASK_NAME, "/F"]
CREATE_ARGS = [
    "schtasks",
    "/Create",
    "/SC", "ONLOGON",
    "/TN", FIXED_TASK_NAME,
    "/TR", f'"{FIXED_APP_PATH}"',
    "/RL", "HIGHEST",
    "/F",
]


class _FakeResult:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _RunRecorder:
    """Stand-in for subprocess.run: records (args, kwargs), returns a fake
    CompletedProcess carrying the configured returncode/stdout/stderr."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return _FakeResult(self.returncode, self.stdout, self.stderr)


@pytest.fixture
def autostart_manager(fake_dpg, monkeypatch):
    mgr = autostart.AutoStartManager(
        app_path=FIXED_APP_PATH,
        task_name=FIXED_TASK_NAME,
    )
    recorder = _RunRecorder()
    monkeypatch.setattr(autostart.subprocess, "run", recorder)
    return mgr, recorder


def _assert_call_sequences(recorder, expected):
    assert [args[0] for args, _ in recorder.calls] == expected
    for args, kwargs in recorder.calls:
        assert "shell" not in kwargs, f"shell=True leaked into call: {kwargs}"
        assert isinstance(args[0], list), f"expected argument list, got: {args[0]!r}"


def test_create_passes_argument_list_no_joined_string(autostart_manager):
    mgr, recorder = autostart_manager
    mgr.create()
    _assert_call_sequences(recorder, [CREATE_ARGS])


def test_task_exists_passes_argument_list_and_uses_returncode(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    assert mgr.task_exists() is True
    recorder.returncode = 1
    assert mgr.task_exists() is False
    _assert_call_sequences(recorder, [QUERY_ARGS, QUERY_ARGS])


def test_delete_passes_argument_list(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    mgr.delete()
    _assert_call_sequences(recorder, [QUERY_ARGS, DELETE_ARGS])


def test_update_if_needed_recreates_when_xml_path_mismatches(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    recorder.stdout = "<xml><Command>C:\\Old\\Location\\DFL.exe</Command></xml>"
    mgr.update_if_needed(True)
    _assert_call_sequences(
        recorder,
        [QUERY_ARGS, XML_ARGS, QUERY_ARGS, DELETE_ARGS, CREATE_ARGS],
    )


def test_update_if_needed_keeps_task_when_xml_path_matches(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    recorder.stdout = f"<xml><Command>{FIXED_APP_PATH}</Command></xml>"
    mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS, XML_ARGS])


def test_update_if_needed_creates_when_task_missing(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 1  # task does not exist
    mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS, CREATE_ARGS])


def test_update_if_needed_removes_when_checkbox_off(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    mgr.update_if_needed(False)
    _assert_call_sequences(recorder, [QUERY_ARGS, QUERY_ARGS, DELETE_ARGS])