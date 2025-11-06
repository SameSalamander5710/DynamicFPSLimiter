import ctypes
import time

def get_idle_duration():
    """Return seconds since last user input (mouse/keyboard) on Windows."""

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        raise ctypes.WinError()

    # Use 32-bit tick count and unsigned arithmetic to handle wrap-around.
    ticks = ctypes.windll.kernel32.GetTickCount()
    delta_ms = (ticks - lii.dwTime) & 0xFFFFFFFF
    return delta_ms / 1000.0

def monitor_idle(threshold=5, interval=1):
    """Monitor idle time."""
    while True:
        try:
            idle = get_idle_duration()
        except Exception as exc:
            print(f"[error] get_idle_duration() raised: {exc!r}", flush=True)
            time.sleep(max(1.0, interval))
            continue

        # always-print for debugging; keep verbose behavior for less output later
        print(f"[debug] idle={idle:.1f}s (threshold={threshold}s)", flush=True)

        if idle >= threshold:
            print(f"User idle for {int(idle)} seconds — triggering idle event.", flush=True)

        time.sleep(interval)

if __name__ == "__main__":

    monitor_idle()