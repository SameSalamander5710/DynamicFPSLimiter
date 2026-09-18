import logging
import sys # Import sys module
import threading

log_messages = []

# GuiQueue (injected at startup via set_gui_queue) so DPG log-widget updates are
# deferred to the main DPG thread. add_log may be called from any background thread,
# and DearPyGui is only safe on the thread that owns the render context.
_gui_queue = None
_log_lock = threading.Lock()
_dpg = None


def set_gui_queue(queue):
    """Inject the GuiQueue so DPG log-widget updates run on the main thread."""
    global _gui_queue
    _gui_queue = queue


def set_dpg(dpg_instance):
    """Inject the dearpygui module instance used for log-widget updates."""
    global _dpg
    _dpg = dpg_instance

# Function to initialize logging configuration and set the exception hook
def init_logging(log_file_path):
    """Sets up basic logging configuration and assigns the system exception hook."""
    logging.basicConfig(
        filename=log_file_path,  # Use the provided path
        level=logging.ERROR,       # Only log errors or more severe messages
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # Redirect uncaught exceptions to the error_log_exception function
    sys.excepthook = error_log_exception

# Error logging function - now just logs the error
def error_log_exception(exc_type, exc_value, exc_traceback):
    """Logs uncaught exceptions using the configured logger."""
    # BasicConfig is now called in init_logging, so we just log here
    logging.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

def _apply_log_text_to_widget():
    """Read the current log snapshot and update the LogText widget.

    Runs on the main DPG thread (via the GuiQueue) when a queue is configured, so
    ``dpg.*`` is only ever touched where it is safe.
    """
    with _log_lock:
        text = "\n".join(log_messages)
    global _dpg
    if _dpg is None:
        return
    try:
        if _dpg.does_item_exist("LogText"):
            _dpg.set_value("LogText", text)
    except Exception:
        # If there's any issue with the GUI update, just continue silently.
        # The log messages are still stored in the log_messages list.
        pass


def add_log(message):
    with _log_lock:
        log_messages.insert(0, message)  # Add message at the top
        log_messages[:] = log_messages[:50]  # Keep only the latest 50 messages
    if _gui_queue is not None:
        _gui_queue.submit(_apply_log_text_to_widget)
    else:
        _apply_log_text_to_widget()


def refresh_log_display():
    """Refresh the log display widget with current messages."""
    if _gui_queue is not None:
        _gui_queue.submit(_apply_log_text_to_widget)
    else:
        _apply_log_text_to_widget()