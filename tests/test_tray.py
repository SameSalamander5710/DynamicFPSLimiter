"""F3: tray callbacks are deferred to the main DPG thread via the GuiQueue.

pystray menu actions fire on a background thread where DearPyGui is not safe, so
every action that touches DPG (directly or via the ConfigManager callbacks it
triggers) must be routed through the queue and run on the main thread.
"""
import configparser
import threading

import core.tray_functions as tray_functions
from core.gui_queue import GuiQueue


class _CmStub:
    def __init__(self, profile="Global", method="ratio"):
        self.current_profile = profile
        self.current_method = method
        self.autopilot = False
        self.profiles_config = None


class _FpsUtilsStub:
    """Mimics fps_utils.current_stepped_limits performing a DPG read."""

    def __init__(self, dpg):
        self.dpg = dpg

    def current_stepped_limits(self):
        self.dpg.get_value("input_capmethod")  # simulate the real DPG read
        return [60, 120]


def _make_tray(cm=None, fps_utils=None, queue=None, dpg=None):
    return tray_functions.TrayManager(
        app_name="TestApp",
        icon_path="",
        on_restore=None,
        on_exit=None,
        viewport_width=100,
        config_manager_instance=cm,
        hover_text="TestApp",
        start_stop_callback=None,
        fps_utils=fps_utils,
        gui_queue=queue,
        dpg=dpg,
    )


def test_run_on_main_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    tray = _make_tray(queue=queue, dpg=fake_dpg)
    called = []
    tray._run_on_main(lambda: called.append(1))
    assert called == []
    assert len(queue) == 1
    queue.drain()
    assert called == [1]


def test_run_on_main_inline_without_queue(fake_dpg):
    tray = _make_tray(dpg=fake_dpg)
    assert tray.gui_queue is None
    called = []
    tray._run_on_main(lambda: called.append(1))
    assert called == [1]


def test_update_hover_text_defers_off_main_thread(fake_dpg):
    queue = GuiQueue()
    cm = _CmStub(profile="MyProfile", method="step")
    fps = _FpsUtilsStub(fake_dpg)
    tray = _make_tray(cm=cm, fps_utils=fps, queue=queue, dpg=fake_dpg)
    fake_dpg.calls.clear()

    def _bg():
        tray.update_hover_text()

    t = threading.Thread(target=_bg)
    t.start()
    t.join()

    # No DPG reads on the background thread (deferred to the queue).
    get_value_calls = [c for c in fake_dpg.calls if c[0] == "get_value"]
    assert get_value_calls == []
    assert len(queue) == 1

    queue.drain()

    get_value_calls = [c for c in fake_dpg.calls if c[0] == "get_value"]
    assert len(get_value_calls) >= 1
    assert all(c[3] == threading.main_thread().name for c in get_value_calls)
    # Hover text built from the ConfigManager snapshot.
    assert "Profile: MyProfile" in tray.hover_text
    assert "Method: Step" in tray.hover_text
    assert "Max FPS: 120" in tray.hover_text


def test_update_hover_text_inline_on_main_thread(fake_dpg):
    cm = _CmStub(profile="Global", method="ratio")
    fps = _FpsUtilsStub(fake_dpg)
    tray = _make_tray(cm=cm, fps_utils=fps, queue=GuiQueue(), dpg=fake_dpg)
    fake_dpg.calls.clear()

    tray.update_hover_text()  # called from the main thread

    get_value_calls = [c for c in fake_dpg.calls if c[0] == "get_value"]
    assert len(get_value_calls) >= 1
    assert "Profile: Global" in tray.hover_text
    assert "Method: Ratio" in tray.hover_text


def test_profile_menu_lambda_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    cm = _CmStub()
    cfg = configparser.ConfigParser()
    cfg["Global"] = {}
    cfg["GameA"] = {}
    cm.profiles_config = cfg
    tray = _make_tray(cm=cm, queue=queue, dpg=fake_dpg)
    fake_dpg.calls.clear()

    items = tray._profile_menu_items()
    assert [item.text for item in items] == ["Global", "GameA"]

    # Invoke the first item's action as pystray would (from the tray thread).
    def _bg():
        items[0]._action(None, None)

    t = threading.Thread(target=_bg)
    t.start()
    t.join()

    # Deferred: no DPG set_value on the background thread.
    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert set_value_calls == []
    assert len(queue) == 1

    queue.drain()

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert len(set_value_calls) == 1
    assert set_value_calls[0][1][0] == "profile_dropdown"
    assert set_value_calls[0][1][1] == "Global"


def test_method_menu_lambda_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    cm = _CmStub()
    tray = _make_tray(cm=cm, queue=queue, dpg=fake_dpg)
    fake_dpg.calls.clear()

    items = list(tray._method_menu_items())
    assert [item.text for item in items] == ["Ratio", "Step", "Custom"]
    step_item = items[1]

    def _bg():
        step_item._action(None, None)

    t = threading.Thread(target=_bg)
    t.start()
    t.join()

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert set_value_calls == []
    assert len(queue) == 1

    queue.drain()

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert len(set_value_calls) == 1
    assert set_value_calls[0][1][0] == "input_capmethod"
    assert set_value_calls[0][1][1] == "step"


def test_exit_app_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    ran = []
    tray = _make_tray(queue=queue, dpg=fake_dpg)
    tray.on_exit = lambda: ran.append("exit")

    tray._exit_app(None, None)

    # Deferred: on_exit not called on the tray thread.
    assert ran == []
    assert len(queue) == 1

    queue.drain()
    assert ran == ["exit"]


def test_restore_window_defers_to_queue(monkeypatch, fake_dpg):
    queue = GuiQueue()
    ran = []
    tray = _make_tray(queue=queue, dpg=fake_dpg)
    tray.on_restore = lambda: ran.append("restore")
    # Avoid a real Win32 ShowWindow call during the test.
    monkeypatch.setattr(tray_functions, "show_to_taskbar", lambda: None)

    tray._restore_window(None, None)

    assert ran == []
    assert len(queue) == 1
    assert tray.is_tray_active is False

    queue.drain()
    assert ran == ["restore"]
