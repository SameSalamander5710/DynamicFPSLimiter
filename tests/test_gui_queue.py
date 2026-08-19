"""GuiQueue unit tests (F3 deliverable, pulled forward for F9).

- submit() buffers callables without executing them.
- drain() executes them in submission order on the calling thread and empties the queue.
- submit() is thread-safe (concurrent submissions are not lost).
- A callback that raises does not stall the queue; it is reported to on_error.
"""
import threading

from core.gui_queue import GuiQueue


def test_submit_buffers_without_executing():
    q = GuiQueue()
    order = []
    q.submit(order.append, "a")
    q.submit(order.append, "b")
    assert order == []
    assert len(q) == 2


def test_drain_executes_in_order_and_empties():
    q = GuiQueue()
    order = []
    for item in ["a", "b", "c"]:
        q.submit(order.append, item)
    executed = q.drain()
    assert executed == 3
    assert order == ["a", "b", "c"]
    assert len(q) == 0
    # draining an empty queue is a no-op
    assert q.drain() == 0


def test_drain_supports_kwargs():
    q = GuiQueue()
    seen = {}

    def record(a, b=None):
        seen["a"] = a
        seen["b"] = b

    q.submit(record, 1, b=2)
    q.drain()
    assert seen == {"a": 1, "b": 2}


def test_concurrent_submits_not_lost():
    q = GuiQueue()
    order = []
    lock = threading.Lock()

    def worker(n):
        for i in range(50):
            def append():
                with lock:
                    order.append((n, i))
            q.submit(append)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    executed = q.drain()
    assert executed == 200
    assert len(order) == 200


def test_failing_callback_does_not_stall_queue():
    errors = []
    q = GuiQueue(on_error=lambda fn, e: errors.append(e))
    order = []
    q.submit(order.append, "before")

    def boom():
        raise ZeroDivisionError("nope")

    q.submit(boom)
    q.submit(order.append, "after")

    executed = q.drain()
    assert executed == 2  # "before" and "after" succeeded; boom did not
    assert order == ["before", "after"]
    assert len(errors) == 1
    assert isinstance(errors[0], ZeroDivisionError)
    assert len(q) == 0
