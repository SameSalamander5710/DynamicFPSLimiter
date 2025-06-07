import ctypes
import os
import winreg
from decimal import Decimal, InvalidOperation

class RTSSController:
    RTSSHOOKSFLAG_LIMITER_DISABLED = 4

    def __init__(self, logger_instance):
        self.rtss_install_path = self.get_rtss_install_path()
        self.rtss_path = os.path.join(self.rtss_install_path, "RTSSHooks64.dll")
        self.dll = ctypes.WinDLL(self.rtss_path)
        self.logger = logger_instance
        self._setup_functions()

    def _setup_functions(self):
        self.LoadProfile = self.dll.LoadProfile
        self.LoadProfile.argtypes = [ctypes.c_char_p]
        self.LoadProfile.restype = None

        self.SaveProfile = self.dll.SaveProfile
        self.SaveProfile.argtypes = [ctypes.c_char_p]
        self.SaveProfile.restype = None

        self.GetProfileProperty = self.dll.GetProfileProperty
        self.GetProfileProperty.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint]
        self.GetProfileProperty.restype = ctypes.c_bool

        self.SetProfileProperty = self.dll.SetProfileProperty
        self.SetProfileProperty.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint]
        self.SetProfileProperty.restype = ctypes.c_bool

        self.DeleteProfile = self.dll.DeleteProfile
        self.DeleteProfile.argtypes = [ctypes.c_char_p]
        self.DeleteProfile.restype = None

        self.ResetProfile = self.dll.ResetProfile
        self.ResetProfile.argtypes = [ctypes.c_char_p]
        self.ResetProfile.restype = None

        self.UpdateProfiles = self.dll.UpdateProfiles
        self.UpdateProfiles.argtypes = []
        self.UpdateProfiles.restype = None

        self.SetFlags = self.dll.SetFlags
        self.SetFlags.argtypes = [ctypes.c_uint, ctypes.c_uint]
        self.SetFlags.restype = ctypes.c_uint

        self.GetFlags = self.dll.GetFlags
        self.GetFlags.argtypes = []
        self.GetFlags.restype = ctypes.c_uint

    def get_rtss_install_path(self):
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
                raise FileNotFoundError("RTSS not found in registry.") #TODO: Add to logger
            #TODO: Add example default path
        if path.lower().endswith("rtss.exe"):
            path = os.path.dirname(path)
        return path

    def delete_profile(self, profile_name):
        self.DeleteProfile(profile_name.encode('ascii'))

    def reset_profile(self, profile_name):
        self.ResetProfile(profile_name.encode('ascii'))

    def get_profile_property(self, profile_name, property_name, size=4):
        self.LoadProfile(profile_name.encode('ascii'))
        buf = (ctypes.c_byte * size)()
        success = self.GetProfileProperty(property_name.encode('ascii'), ctypes.byref(buf), size)
        if not success:
            return None
        return bytes(buf)

    def set_profile_property(self, profile_name, property_name, value, size=4, update=True):
        self.LoadProfile(profile_name.encode('ascii'))
        if isinstance(value, int):
            buf = ctypes.c_int(value)
            ptr = ctypes.byref(buf)
        elif isinstance(value, bytes):
            buf = (ctypes.c_byte * size).from_buffer_copy(value)
            ptr = ctypes.byref(buf)
        else:
            raise ValueError("Unsupported value type")
        success = self.SetProfileProperty(property_name.encode('ascii'), ptr, size)
        self.SaveProfile(profile_name.encode('ascii'))
        if update:
            self.UpdateProfiles()
        return success

    def create_profile(self, profile_name, properties):
        # Load global profile as a base
        self.LoadProfile(b"")
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
            self.SetProfileProperty(prop.encode('ascii'), ptr, size)
        # Save as new profile
        self.SaveProfile(profile_name.encode('ascii'))
        self.UpdateProfiles()

    def get_flags(self):
        return self.GetFlags()

    def set_flags(self, and_mask, xor_mask):
        return self.SetFlags(and_mask, xor_mask)

    def disable_limiter(self):
        self.SetFlags(0xFFFFFFFF, self.RTSSHOOKSFLAG_LIMITER_DISABLED)
        self.UpdateProfiles()

    def enable_limiter(self):
        self.logger.add_log(f"Enabling RTSS limiter...")
        self.SetFlags(~self.RTSSHOOKSFLAG_LIMITER_DISABLED & 0xFFFFFFFF, 0)
        self.UpdateProfiles()

    # Derived functions    
    def set_limit_denominator(self, profile_name, new_denominator, update=True):
        profiles_dir = os.path.join(self.rtss_install_path, "Profiles")
        if not profile_name or profile_name.lower() == "global":
            profile_file = os.path.join(profiles_dir, "Global")
            profile_name_for_api = ""
        else:
            profile_file = os.path.join(profiles_dir, f"{profile_name}.cfg")
            profile_name_for_api = profile_name

        if not os.path.isfile(profile_file):
            print(f"Profile file not found: {profile_file}")
            return False

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
            self.UpdateProfiles()
        return True

    def set_fractional_framerate(self, profile_name, framerate, update=False):
        profile_name_for_api = "" if not profile_name or profile_name.lower() == "global" else profile_name
        fr_str = str(framerate)
        if '.' in fr_str:
            decimals = len(fr_str.split('.')[1])
            denominator = 10 ** decimals
            limit = int(round(float(framerate) * denominator))
        else:
            denominator = 1
            limit = int(framerate)

        self.set_limit_denominator(profile_name, denominator, update=update)
        self.set_profile_property(profile_name_for_api, "FramerateLimit", limit, update=update)
        if not update:
            self.UpdateProfiles()

        print(f"Set {profile_name}: FramerateLimit={limit}, LimitDenominator={denominator} (actual limit: {limit/denominator})")
        return limit, denominator

    def set_fractional_fps_direct(self, profile_name, framerate, update=True):

        profiles_dir = os.path.join(self.rtss_install_path, "Profiles")
        if not profile_name or profile_name.lower() == "global":
            profile_file = os.path.join(profiles_dir, "Global")
            profile_name_for_api = ""
        else:
            profile_file = os.path.join(profiles_dir, f"{profile_name}.cfg")
            profile_name_for_api = profile_name

        if not os.path.isfile(profile_file):
            print(f"Profile file not found: {profile_file}")
            return False

        fr_str = str(framerate)

        if '.' in fr_str:
            decimals = len(fr_str.split('.')[1])
            denominator = 10 ** decimals
            limit = int(round(float(framerate) * denominator))
        else:
            denominator = 1
            limit = int(framerate)

        with open(profile_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith("LimitDenominator="):
                lines[i] = f"LimitDenominator={denominator}\n"
                found = True
                break

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("Limit="):
                lines[i] = f"Limit={limit}\n"
                found_limit = True
            elif stripped.startswith("LimitDenominator="):
                lines[i] = f"LimitDenominator={denominator}\n"
                found_denominator = True

        # Append if not found
        if not found_limit:
            lines.append(f"Limit={limit}\n")
        if not found_denominator:
            lines.append(f"LimitDenominator={denominator}\n")

        with open(profile_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"Updated Limit={limit}, LimitDenominator={denominator} in {profile_file}")
        if update:
            self.UpdateProfiles()
        return True
    
    def get_framerate_limit(self, profile_name, get_denominator=False):
        profile_name_for_api = "" if not profile_name or profile_name.lower() == "global" else profile_name
        limit = self.get_profile_property(profile_name_for_api, "FramerateLimit", 4)
        if limit is None:
            return None

        limit_int = int.from_bytes(limit, byteorder='little', signed=True)

        if not get_denominator:
            return limit_int

        profiles_dir = os.path.join(self.rtss_install_path, "Profiles")
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

if __name__ == "__main__":
    rtss = RTSSController()
    test_profile = "test_profile 5.exe"

    #rtss.create_profile("test245345.exe") # this doesn not work without an additional parameter.

    # Set a framerate limit
    #print("Setting framerate limit to 60...")
    #rtss.set_profile_property(test_profile, "FramerateLimit", 65)

    # Get the framerate limit
    #limit = rtss.get_framerate_limit(test_profile)
    #print(f"Framerate limit for {test_profile}: {limit}")

    # Set a fractional framerate (e.g., 59.94)
    #print("Setting fractional framerate to 59.94...")
    #rtss.set_fractional_framerate(test_profile, 59.94)
    #limit_fractional = rtss.get_framerate_limit(test_profile, get_denominator=True)
    #print(f"Fractional framerate limit for {test_profile}: {limit_fractional}")

    # Clean up (optional)
    # rtss.delete_profile(test_profile)