import subprocess
import psutil
from ctypes import wintypes, WinDLL, byref
import mmap
import struct
import time
from collections import defaultdict
import dearpygui.dearpygui as dpg
import threading
import os # Added for os.path.dirname

# Assuming logger is imported correctly from the main script or passed in
# from . import logger # Example if logger is in the same directory

user32 = WinDLL('user32', use_last_error=True)

class RTSSInterface:
    def __init__(self, rtss_cli_path, logger_instance, dpg_instance):
        """
        Initializes the RTSS Interface.

        Args:
            rtss_cli_path (str): The absolute path to rtss-cli.exe.
            logger_instance: An instance of the logger module/class.
            dpg_instance: The dearpygui instance (dpg).
        """
        self.rtss_cli_path = rtss_cli_path
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.last_dwTime0s = defaultdict(int)
        self.rtss_monitor_running = True
        self.rtss_status = False
        self._monitor_thread = None

    def run_rtss_cli(self, command_args):
        """Executes the rtss-cli.exe with given arguments."""
        # Prepend the executable path to the command arguments
        full_command = [self.rtss_cli_path] + command_args

        # Suppress console window on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            result = subprocess.run(
                full_command, # Use the full command list
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip()
        except FileNotFoundError:
            self.logger.add_log(f"> Error: rtss-cli.exe not found at\n{self.rtss_cli_path}")
            return None
        except Exception as e:
            self.logger.add_log(f"> Subprocess failed for rtss-cli.exe:\n{e}")
            return None

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
                            return fps, process_name
            return None, None
        except FileNotFoundError:
            # Shared memory doesn't exist (RTSS likely not running or OSD not enabled)
            self.rtss_status = False # Update status
            return None, None
        except Exception as e:
            self.logger.add_log(f"> Error reading RTSS Shared Memory: {e}")
            return None, None

        return None, None # Process not found in shared memory

    def _rtss_monitor_thread_func(self):
        """Internal thread function to monitor RTSS status."""
        while self.rtss_monitor_running:
            try:
                current_status = self.is_rtss_running()
                if current_status != self.rtss_status:
                    self.rtss_status = current_status
                    # Use logger instance
                    self.logger.add_log("> RTSS detected" if self.rtss_status else "> RTSS not running!")
                    # Use dpg instance and check if running/item exists
                    if self.dpg.is_dearpygui_running():
                        if self.dpg.does_item_exist("start_stop_button"):
                             theme_tag = "rtss_running_theme" if self.rtss_status else "rtss_not_running_theme"
                             # Check if themes exist before binding
                             if self.dpg.does_item_exist(theme_tag):
                                 self.dpg.bind_item_theme("start_stop_button", theme_tag)
                        if self.dpg.does_item_exist("dynamic_RTSS_running:"):
                            self.dpg.set_value("dynamic_RTSS_running:", "Yes" if self.rtss_status else "No")

            except Exception as e:
                self.logger.add_log(f"> Error in RTSS monitor thread: {e}")
                # Avoid spamming logs in case of rapid errors
                time.sleep(5)
            time.sleep(1) # Check less frequently

    def start_monitor_thread(self):
        """Starts the RTSS status monitoring thread."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self.rtss_monitor_running = True
            self._monitor_thread = threading.Thread(target=self._rtss_monitor_thread_func, daemon=True)
            self._monitor_thread.start()
            self.logger.add_log("> RTSS monitor thread started.")

    def stop_monitor_thread(self):
        """Stops the RTSS status monitoring thread."""
        self.rtss_monitor_running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1) # Wait briefly for thread to exit
        self._monitor_thread = None
        self.logger.add_log("> RTSS monitor thread stopped.")

