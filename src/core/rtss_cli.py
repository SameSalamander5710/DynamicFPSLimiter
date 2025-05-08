import ctypes
from ctypes import c_char_p, c_int, c_uint
import os

class RTSSCLI:
    def __init__(self, logger_instance, dll_path=None, ):
        """
        Initializes the RTSS interface by loading the DLL.

        Args:
            dll_path (str): Path to the RTSS DLL. If None, defaults to 'assets/rtss.dll' in the script directory.
        """
        self.logger = logger_instance
        if dll_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            dll_path = os.path.join(script_dir, "assets/rtss.dll")

        self.rtss = ctypes.CDLL(dll_path)  # Load the DLL
        self._configure_functions()

    def _configure_functions(self):
        """Configures the argument and return types for the DLL functions."""
        self.rtss.set_property.argtypes = [c_char_p, c_char_p, c_int]
        self.rtss.set_property.restype = None

        self.rtss.get_property.argtypes = [c_char_p, c_char_p]
        self.rtss.get_property.restype = c_int

        self.rtss.set_flags.argtypes = [c_uint, c_uint]
        self.rtss.set_flags.restype = None

        self.rtss.get_flags.argtypes = []
        self.rtss.get_flags.restype = c_uint

    def set_property(self, profile, prop, value):
        """Sets a property for a given profile."""
        # Replace "Global" with an empty string
        if profile == "Global":
            profile = ""
        #self.logger.add_log(f"{profile.encode()}, {prop.encode()}, {value}")
        self.rtss.set_property(profile.encode(), prop.encode(), value)
        self.logger.add_log(f"Last RTSS error, if present: {ctypes.get_last_error()}")
        self.logger.add_log(f"FPS Limiter set to {value} for profile '{profile}' with property '{prop}'.")

    def get_property(self, profile, prop):
        """Gets a property value for a given profile."""
        # Replace "Global" with an empty string
        if profile == "Global":
            profile = ""
        return self.rtss.get_property(profile.encode(), prop.encode())

    def set_flags(self, and_mask, or_mask):
        """Sets flags using AND and OR masks."""
        self.rtss.set_flags(and_mask, or_mask)

    def get_flags(self):
        """Gets the current flags."""
        return self.rtss.get_flags()

    def is_limiter_enabled(self):
        """Checks if the RTSS frame rate limiter is currently enabled."""
        flags = self.get_flags()
        return (flags & RTSSHOOKSFLAG_LIMITER_DISABLED) == 0

    def enable_limiter(self):
        """Enables the RTSS frame rate limiter."""
        self.logger.add_log(f"Enabling RTSS limiter...")
        self.set_flags(~RTSSHOOKSFLAG_LIMITER_DISABLED, 0)
        #self.logger.add_log(f"RTSS limiter enabled.")

    def disable_limiter(self):
        """Disables the RTSS frame rate limiter."""
        self.set_flags(~RTSSHOOKSFLAG_LIMITER_DISABLED, RTSSHOOKSFLAG_LIMITER_DISABLED)

# Constants
RTSSHOOKSFLAG_OSD_VISIBLE = 1
RTSSHOOKSFLAG_LIMITER_DISABLED = 4
