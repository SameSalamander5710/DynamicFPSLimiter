"""F3: logger DPG updates are deferred to the main thread via the GuiQueue.

The log buffer must stay thread-safe (it is appended from background threads)
and the DearPyGui widget refresh must run on the main render thread.
"""
import threading

import core.logger as logger
from core.gui_queue import GuiQueue


def test_set_gui_queue_injects_queue(monkeypatch):
    monkeypatch.setattr(logger, "_gui_queue", None)
    queue = GuiQueue()
    logger.set_gui_queue(queue)
    assert logger._gui_queue is queue


def test_add_log_defers_dpg_to_queue(fake_dpg, monkeypatch):
    monkeypatch.setattr(logger, "log_messages", [])
    monkeypatch.setattr(logger, "_dpg", fake_dpg)
    queue = GuiQueue()
    monkeypatch.setattr(logger, "_gui_queue", queue)
    fake_dpg.calls.clear()
    fake_dpg.items.add("LogText")  # pretend the log widget exists

    def _bg():
        logger.add_log("hello from bg")

    t = threading.Thread(target=_bg)
    t.start()
    t.join()

    # Deferred: no DPG set_value happened on the background thread.
    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert set_value_calls == []
    assert len(queue) == 1

    queue.drain()

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert len(set_value_calls) == 1
    assert set_value_calls[0][1][0] == "LogText"
    assert "hello from bg" in set_value_calls[0][1][1]
    # Ran on the draining (main) thread, not the background thread.
    assert set_value_calls[0][3] == threading.main_thread().name


def test_add_log_inline_without_queue(fake_dpg, monkeypatch):
    monkeypatch.setattr(logger, "log_messages", [])
    monkeypatch.setattr(logger, "_dpg", fake_dpg)
    monkeypatch.setattr(logger, "_gui_queue", None)
    fake_dpg.calls.clear()
    fake_dpg.items.add("LogText")  # pretend the log widget exists

    logger.add_log("direct")

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert len(set_value_calls) == 1
    assert set_value_calls[0][1][0] == "LogText"
    assert "direct" in set_value_calls[0][1][1]


def test_add_log_trims_to_50(fake_dpg, monkeypatch):
    monkeypatch.setattr(logger, "log_messages", [])
    monkeypatch.setattr(logger, "_gui_queue", None)

    for i in range(60):
        logger.add_log(f"msg {i}")

    # Only the latest 50 are kept; newest first.
    assert len(logger.log_messages) == 50
    assert logger.log_messages[0] == "msg 59"
    assert logger.log_messages[-1] == "msg 10"


def test_add_log_is_thread_safe(fake_dpg, monkeypatch):
    monkeypatch.setattr(logger, "log_messages", [])
    monkeypatch.setattr(logger, "_gui_queue", None)

    def _worker(n):
        for i in range(50):
            logger.add_log(f"t{n}-{i}")

    threads = [threading.Thread(target=_worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The lock keeps the buffer consistent: exactly the latest 50 survive.
    assert len(logger.log_messages) == 50
