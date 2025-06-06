import ctypes
import os
import winreg

def get_rtss_install_path():
    # Try 64-bit registry first, then fallback to 32-bit
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Unwinder\RTSS")
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
    except FileNotFoundError:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Unwinder\RTSS")
            path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
        except FileNotFoundError:
            raise FileNotFoundError("RTSS not found in registry.")
    # Remove trailing RTSS.exe if present
    if path.lower().endswith("rtss.exe"):
        path = os.path.dirname(path)
    return path

rtss_install_path = get_rtss_install_path()
rtss_path = os.path.join(rtss_install_path, "RTSSHooks64.dll")
dll = ctypes.WinDLL(rtss_path)

# Function prototypes
LoadProfile = dll.LoadProfile
LoadProfile.argtypes = [ctypes.c_char_p]
LoadProfile.restype = None

SaveProfile = dll.SaveProfile
SaveProfile.argtypes = [ctypes.c_char_p]
SaveProfile.restype = None

GetProfileProperty = dll.GetProfileProperty
GetProfileProperty.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint]
GetProfileProperty.restype = ctypes.c_bool

SetProfileProperty = dll.SetProfileProperty
SetProfileProperty.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint]
SetProfileProperty.restype = ctypes.c_bool

DeleteProfile = dll.DeleteProfile
DeleteProfile.argtypes = [ctypes.c_char_p]
DeleteProfile.restype = None

ResetProfile = dll.ResetProfile
ResetProfile.argtypes = [ctypes.c_char_p]
ResetProfile.restype = None

UpdateProfiles = dll.UpdateProfiles
UpdateProfiles.argtypes = []
UpdateProfiles.restype = None

SetFlags = dll.SetFlags
SetFlags.argtypes = [ctypes.c_uint, ctypes.c_uint]
SetFlags.restype = ctypes.c_uint

GetFlags = dll.GetFlags
GetFlags.argtypes = []
GetFlags.restype = ctypes.c_uint

# Example wrappers
# Base functions

def delete_profile(profile_name):
    DeleteProfile(profile_name.encode('ascii'))

def reset_profile(profile_name):
    ResetProfile(profile_name.encode('ascii'))

def get_profile_property(profile_name, property_name, size=4):
    LoadProfile(profile_name.encode('ascii'))
    buf = (ctypes.c_byte * size)()
    success = GetProfileProperty(property_name.encode('ascii'), ctypes.byref(buf), size)
    if not success:
        return None
    return bytes(buf)

def set_profile_property(profile_name, property_name, value, size=4, update=True):
    LoadProfile(profile_name.encode('ascii'))
    if isinstance(value, int):
        buf = ctypes.c_int(value)
        ptr = ctypes.byref(buf)
    elif isinstance(value, bytes):
        buf = (ctypes.c_byte * size).from_buffer_copy(value)
        ptr = ctypes.byref(buf)
    else:
        raise ValueError("Unsupported value type")
    success = SetProfileProperty(property_name.encode('ascii'), ptr, size)
    SaveProfile(profile_name.encode('ascii'))
    if update:
        UpdateProfiles()
    return success

def create_profile(profile_name, properties):
    # Load global profile as a base
    LoadProfile(b"")
    # Set each property
    for prop, value in properties.items():
        if isinstance(value, int):
            buf = ctypes.c_int(value)
            ptr = ctypes.byref(buf)
            size = ctypes.sizeof(buf)
        elif isinstance(value, bytes):
            size = len(value)
            buf = (ctypes.c_byte * size).from_buffer_copy(value)
            ptr = ctypes.byref(buf)
        else:
            raise ValueError("Unsupported value type")
        SetProfileProperty(prop.encode('ascii'), ptr, size)
    # Save as new profile
    SaveProfile(profile_name.encode('ascii'))
    UpdateProfiles()

def get_flags():
    return GetFlags()

def set_flags(and_mask, xor_mask):
    return SetFlags(and_mask, xor_mask)

RTSSHOOKSFLAG_LIMITER_DISABLED = 4

def disable_limiter():
    """Disable the RTSS framerate limiter (set the flag)."""
    # Set bit 2 to 1 (disable limiter)
    current = GetFlags()
    SetFlags(0xFFFFFFFF, RTSSHOOKSFLAG_LIMITER_DISABLED)
    UpdateProfiles()

def enable_limiter():
    """Enable the RTSS framerate limiter (clear the flag)."""
    # Set bit 2 to 0 (enable limiter)
    current = GetFlags()
    SetFlags(~RTSSHOOKSFLAG_LIMITER_DISABLED & 0xFFFFFFFF, 0)
    UpdateProfiles()

# Derived functions

def set_limit_denominator(profile_name, new_denominator, update=True):
    """
    Update the LimitDenominator value in the RTSS profile .cfg file.
    profile_name: e.g. "Global", "CustomProfile", etc.
    new_denominator: integer value to set
    """
    rtss_install_path = get_rtss_install_path()
    profiles_dir = os.path.join(rtss_install_path, "Profiles")
    if not profile_name or profile_name.lower() == "global":
        profile_file = os.path.join(profiles_dir, "Global")
    else:
        profile_file = os.path.join(profiles_dir, f"{profile_name}.cfg")

    if not os.path.isfile(profile_file):
        print(f"Profile file not found: {profile_file}")
        return False

    # Read and update the file
    with open(profile_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("LimitDenominator="):
            lines[i] = f"LimitDenominator={new_denominator}\n"
            found = True
            break

    if not found:
        lines.append(f"LimitDenominator={new_denominator}\n")

    with open(profile_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Updated LimitDenominator to {new_denominator} in {profile_file}")
    if update:
        UpdateProfiles()  # Reload profiles in RTSS, if available
    return True

def set_fractional_framerate(profile_name, framerate):
    """
    Sets a fractional framerate limit for the given profile.
    If framerate is an integer, denominator is 1.
    If framerate is a decimal, denominator is a power of ten so that (framerate * denominator) is an integer.
    Example: 62.33 -> denominator=100, limit=6233
    """
    # Convert to string to check for decimal
    fr_str = str(framerate)
    if '.' in fr_str:
        decimals = len(fr_str.split('.')[1])
        denominator = 10 ** decimals
        limit = int(round(float(framerate) * denominator))
    else:
        denominator = 1
        limit = int(framerate)

    set_limit_denominator(profile_name, denominator, update=False)
    set_profile_property(profile_name, "FramerateLimit", limit, update=False)
    UpdateProfiles()
    print(f"Set {profile_name}: FramerateLimit={limit}, LimitDenominator={denominator} (actual limit: {limit/denominator})")
    return limit, denominator

def get_framerate_limit(profile_name, get_denominator=False):
    """
    Get the FramerateLimit property as a float for the given profile.
    If get_denominator is True, also reads LimitDenominator from the profile file and divides.
    If False, assumes denominator is 1 and returns the integer value.
    """
    limit = get_profile_property(profile_name, "FramerateLimit", 4)
    if limit is None:
        return None

    limit_int = int.from_bytes(limit, byteorder='little', signed=True)

    if not get_denominator:
        return limit_int

    # Read denominator from the profile file
    rtss_install_path = get_rtss_install_path()
    profiles_dir = os.path.join(rtss_install_path, "Profiles")
    if not profile_name or profile_name.lower() == "global":
        profile_file = os.path.join(profiles_dir, "Global")
    else:
        profile_file = os.path.join(profiles_dir, f"{profile_name}.cfg")

    denominator = 1
    if os.path.isfile(profile_file):
        with open(profile_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("LimitDenominator="):
                    try:
                        denominator = int(line.strip().split("=")[1])
                    except Exception:
                        denominator = 1
                    break

    if denominator < 1:
        denominator = 1

    return limit_int / denominator

# Helper functions

# Example usage
if __name__ == "__main__":

    #create_profile("test2.exe", {"FramerateLimit": 60})
    print("Created new profile with FramerateLimit 60")

    #set_profile_property("test2.exe", "FramerateLimit", 45)
    print("FramerateLimit bytes:", get_profile_property("Warframe.x64.exe", "FramerateLimit"))

    limit = get_framerate_limit("Warframe.x64.exe")
    print("FramerateLimit:", limit)

    print("Current flags:", get_flags())
    disable_limiter()
    print("Current flags:", get_flags())
    enable_limiter()  
    print("Current flags:", get_flags())
    enable_limiter()  
    print("Current flags:", get_flags())
    disable_limiter()
    print("Current flags:", get_flags())
    enable_limiter()  
    print("Current flags:", get_flags())
    # delete_profile("asd")
    # reset_profile("SomeProfile.exe")

    #set_limit_denominator("test2.exe", 10)
    #set_profile_property("test2.exe", "FramerateLimit", 459)

    set_fractional_framerate("test2.exe", 31.89099)
    # set_fractional_framerate("test2.exe", 60)
    print(get_framerate_limit("test2.exe", get_denominator=True))
