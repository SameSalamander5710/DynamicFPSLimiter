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

# Usage example:
def set_property(profile, prop, value):
    return rtss.set_property(profile.encode(), prop.encode(), value)

def get_property(profile, prop):
    return rtss.get_property(profile.encode(), prop.encode())

def set_flags(and_mask, or_mask):
    rtss.set_flags(and_mask, or_mask)

def get_flags():
    return rtss.get_flags()

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

        print("Toggling overlay bit (bit 0)...")
        set_flags(0xFFFFFFFF, flags ^ 0x1)

        print("Flags after toggle:")
        print(f"{get_flags():#010x}")

        print("\nAll operations completed successfully.")
    except Exception as e:
        print("An error occurred:", e)