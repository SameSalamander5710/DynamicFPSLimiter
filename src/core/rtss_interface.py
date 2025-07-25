import subprocess
import psutil
from ctypes import wintypes, WinDLL, byref
import mmap
import struct
import time
from collections import defaultdict
import dearpygui.dearpygui as dpg
import threading
import os
from decimal import Decimal, InvalidOperation

user32 = WinDLL('user32', use_last_error=True)

class RTSSInterface:
    def __init__(self, logger_instance, dpg_instance):
        """
        Initializes the RTSS Interface.

        Args:
            logger_instance: An instance of the logger module/class.
            dpg_instance: The dearpygui instance (dpg).
        """
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.last_dwTime0s = defaultdict(int)

    def is_rtss_running(self):
        """Checks if RTSS.exe process is running."""
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] == 'RTSS.exe':
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass # Ignore processes that can't be accessed
        return False

    def _get_foreground_window_process_id(self):
        """Gets the process ID of the foreground window."""
        hwnd = user32.GetForegroundWindow()
        if hwnd == 0:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        return pid.value

    def get_fps_for_active_window(self):
        """Gets the FPS and process name for the active foreground window via RTSS shared memory."""
        if not self.is_rtss_running():
            return None, None

        process_id = self._get_foreground_window_process_id()
        if not process_id:
            return None, None

        try:
            # Initial size guess, might need resizing
            mmap_size = 4485160
            mm = mmap.mmap(0, mmap_size, 'RTSSSharedMemoryV2')
            dwSignature, dwVersion, dwAppEntrySize, dwAppArrOffset, dwAppArrSize, dwOSDEntrySize, dwOSDArrOffset, dwOSDArrSize, dwOSDFrame = struct.unpack('4sLLLLLLLL', mm[0:36])
            calc_mmap_size = dwAppArrOffset + dwAppArrSize * dwAppEntrySize
            if mmap_size < calc_mmap_size:
                mm = mmap.mmap(0, calc_mmap_size, 'RTSSSharedMemoryV2')
            if dwSignature[::-1] not in [b'RTSS', b'SSTR'] or dwVersion < 0x00020000:
                return None, None # Invalid signature or version

            for dwEntry in range(0, dwAppArrSize):
                entry = dwAppArrOffset + dwEntry * dwAppEntrySize
                stump = mm[entry:entry + 6 * 4 + 260]
                if len(stump) == 0:
                    continue
                dwProcessID, szName, dwFlags, dwTime0, dwTime1, dwFrames, dwFrameTime = struct.unpack('L260sLLLLL', stump)
                if dwProcessID == process_id:
                    if dwTime0 > 0 and dwTime1 > 0 and dwFrames > 0:
                        if dwTime0 != self.last_dwTime0s.get(dwProcessID):
                            fps = 1000 * dwFrames / (dwTime1 - dwTime0)
                            self.last_dwTime0s[dwProcessID] = dwTime0
                            process_name = szName.decode(errors='ignore').rstrip('\x00')
                            process_name = process_name.split('\\')[-1]
                            return Decimal(fps), process_name
            return None, None
        except FileNotFoundError:
            # Shared memory doesn't exist (RTSS likely not running or OSD not enabled)
            self.rtss_status = False # Update status
            return None, None
        except Exception as e:
            self.logger.add_log(f"Error reading RTSS Shared Memory: {e}")
            return None, None

        return None, None # Process not found in shared memory
