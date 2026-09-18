import ctypes

def get_idle_duration():
    """Return seconds since last user input (mouse/keyboard) on Windows."""

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        raise ctypes.WinError()

    # Prefer GetTickCount64 if available
    try:
        ticks = ctypes.windll.kernel32.GetTickCount64()
        # dwTime is 32-bit, keep arithmetic safe
        delta_ms = (int(ticks) - int(lii.dwTime)) & ((1 << 64) - 1)

    except AttributeError:
        # fallback to 32-bit GetTickCount
        ticks = ctypes.windll.kernel32.GetTickCount()
        delta_ms = (int(ticks) - int(lii.dwTime)) & 0xFFFFFFFF
    return delta_ms / 1000.0

def monitor_idle(threshold=5):
    """Return True if the user has been idle for at least *threshold* seconds."""
    try:
        return get_idle_duration() >= threshold
    except Exception:
        return False

if __name__ == "__main__":

    print(monitor_idle(5))