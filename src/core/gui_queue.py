"""Thread-safe queue for deferring DearPyGui calls to the main render thread.

DearPyGui is not thread-safe: every ``dpg.*`` call must run on the thread that owns
the render context (the main thread). Background threads (monitoring, plotting, tray,
.NET callbacks) therefore cannot call ``dpg.*`` directly. They instead submit a
callable to a :class:`GuiQueue`, which the main thread drains once per frame via a
self-rescheduling ``dpg.set_frame_callback`` hook.
"""

import threading
from collections import deque
from typing import Any, Callable, Optional


class GuiQueue:
    """Buffers GUI callables from any thread and executes them on the main thread.

    Example:
        gui_queue = GuiQueue()
        # from any thread:
        gui_queue.submit(dpg.set_value, "some_tag", "hello")
        # main thread, once per frame (see the frame hook wired in DFL_v5.py):
        gui_queue.drain()
    """

    def __init__(self, on_error: Optional[Callable] = None) -> None:
        self._queue: deque = deque()
        self._lock = threading.Lock()
        self._on_error = on_error

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        """Buffer ``fn(*args, **kwargs)`` to execute on the main thread.

        Thread-safe: may be called from any thread. The callable is NOT executed here;
        it runs later when :meth:`drain` is called on the main thread.
        """
        with self._lock:
            self._queue.append((fn, args, kwargs))

    def drain(self) -> int:
        """Execute all buffered callables, in submission order, on the calling thread.

        Must be called from the main thread (the thread that owns the DPG context).
        A callback that raises is caught so a single failure cannot stall the queue or
        the render loop; it is reported to ``on_error`` (if provided). Returns the
        number of callables executed successfully.
        """
        executed = 0
        while True:
            with self._lock:
                if not self._queue:
                    break
                fn, args, kwargs = self._queue.popleft()
            try:
                fn(*args, **kwargs)
                executed += 1
            except Exception as exc:  # noqa: BLE001 - keep the render loop alive
                if self._on_error is not None:
                    try:
                        self._on_error(fn, exc)
                    except Exception:
                        pass
        return executed

    def __len__(self) -> int:
        """Number of callables currently buffered."""
        with self._lock:
            return len(self._queue)
