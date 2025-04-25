import dearpygui.dearpygui as dpg
import logging
import sys # Import sys module

log_messages = []

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

# Keep the add_log function as it was
def add_log(message):
    log_messages.insert(0, message)  # Add message at the top
    log_messages[:] = log_messages[:50]  # Keep only the latest 50 messages
    dpg.set_value("LogText", "\n".join(log_messages))