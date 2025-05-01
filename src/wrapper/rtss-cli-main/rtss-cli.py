import ctypes
from ctypes import c_char_p, c_int, c_uint
import os

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the full path to the DLL
dll_path = os.path.join(script_dir, "rtss.dll")

rtss = ctypes.CDLL(dll_path) # Load using the full path

rtss.set_property.argtypes = [c_char_p, c_char_p, c_int]
rtss.set_property.restype = c_int

rtss.get_property.argtypes = [c_char_p, c_char_p]
rtss.get_property.restype = c_int

rtss.set_flags.argtypes = [c_uint, c_uint]
rtss.set_flags.restype = None

rtss.get_flags.argtypes = []
rtss.get_flags.restype = c_uint

RTSSHOOKSFLAG_OSD_VISIBLE = 1
RTSSHOOKSFLAG_LIMITER_DISABLED = 4

# Usage example:
def set_property(profile, prop, value):
    return rtss.set_property(profile.encode(), prop.encode(), value)

def get_property(profile, prop):
    return rtss.get_property(profile.encode(), prop.encode())

def set_flags(and_mask, or_mask):
    rtss.set_flags(and_mask, or_mask)

def get_flags():
    return rtss.get_flags()

#Testing Specific Flags
def is_limiter_enabled():
    """Checks if the RTSS frame rate limiter is currently enabled."""
    flags = get_flags()
    # The limiter is enabled if the DISABLED flag is NOT set
    return (flags & RTSSHOOKSFLAG_LIMITER_DISABLED) == 0

def enable_limiter():
    """Enables the RTSS frame rate limiter."""
    # Clear the RTSSHOOKSFLAG_LIMITER_DISABLED bit
    set_flags(~RTSSHOOKSFLAG_LIMITER_DISABLED, 0)

def disable_limiter():
    """Disables the RTSS frame rate limiter."""
    # Set the RTSSHOOKSFLAG_LIMITER_DISABLED bit
    # (Using the same logic as rtss-cli.cpp limiter:set 0)
    set_flags(~RTSSHOOKSFLAG_LIMITER_DISABLED, RTSSHOOKSFLAG_LIMITER_DISABLED)


# Self-test when run as a script
if __name__ == "__main__":
    print("Testing RTSS DLL integration...\n")

    try:
        print("Setting 'FramerateLimit' to 72 in Global profile...")
        set_property("", "FramerateLimit", 72)

        print("Reading back 'FramerateLimit'...")
        fps = get_property("", "FramerateLimit")
        print(f"Current Framerate Limit: {fps}")

        print("Getting current flags...")
        flags = get_flags()
        print(f"Flags before toggle: {flags:#010x}")

        enable_limiter()
        print("\nChecking limiter status...")
        if is_limiter_enabled():
            print("Limiter is currently ENABLED.")
        else:
            print("Limiter is currently DISABLED.")

        flags = get_flags()
        print(f"Flags after toggle 1: {flags:#010x}")

        disable_limiter()

        print("\nChecking limiter status...") 
        if is_limiter_enabled():
            print("Limiter is currently ENABLED.")
        else:
            print("Limiter is currently DISABLED.")

        print("\nAll operations completed successfully.")

        flags = get_flags()
        print(f"Flags after toggle 2: {flags:#010x}")
    except Exception as e:
        print("An error occurred:", e)
