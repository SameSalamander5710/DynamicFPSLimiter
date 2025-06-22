import threading
import time
import os
import sys
import ctypes
from PIL import Image
import dearpygui.dearpygui as dpg
from pystray import Icon, MenuItem, Menu

def get_hwnd():
    # Get DearPyGui main window handle (HWND)
    # This works for DPG >= 1.8 on Windows
    try:
        return dpg.get_viewport_platform_handle()
    except Exception:
        return None

def hide_from_taskbar():
    hwnd = get_hwnd()
    if hwnd:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x08 | 0x80  # Remove APPWINDOW, add TOOLWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE

def show_to_taskbar():
    hwnd = get_hwnd()
    if hwnd:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x80 | 0x08  # Remove TOOLWINDOW, add APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW

def is_window_minimized():
    """Returns True if the DearPyGui window is minimized (iconic), else False."""
    hwnd = get_hwnd()
    if hwnd:
        return ctypes.windll.user32.IsIconic(hwnd)
    return False

def minimize_watcher(tray_manager):
    """
    Watches for window minimize events and calls tray_manager.minimize_to_tray()
    when the window is minimized by the user.
    Intended to be run in a background thread.
    """
    was_minimized = False
    while dpg.is_dearpygui_running():
        if is_window_minimized():
            if not was_minimized:
                tray_manager.minimize_to_tray()
                was_minimized = True
        else:
            was_minimized = False
        time.sleep(0.2)  # Check 5 times per second

class TrayManager:
    def __init__(self, app_name, icon_path, on_restore, on_exit, hover_text=None):
        self.app_name = app_name
        self.icon_path = icon_path
        self.on_restore = on_restore
        self.on_exit = on_exit
        self.hover_text = hover_text or app_name
        self.icon = None
        self.tray_thread = None
        self.is_tray_active = False

    def _create_icon(self):
        image = Image.open(self.icon_path)
        menu = Menu(
            MenuItem("Restore", self._restore_window),
            MenuItem("Exit", self._exit_app)
        )
        self.icon = Icon(self.app_name, image, self.hover_text, menu)

    def _restore_window(self, icon, item):
        # Called from tray thread, so use dpg callback
        dpg.run_async_callback(self.on_restore)
        self.is_tray_active = False
        if self.icon:
            self.icon.stop()

    def _exit_app(self, icon, item):
        dpg.run_async_callback(self.on_exit)
        self.is_tray_active = False
        if self.icon:
            self.icon.stop()

    def show_tray(self):
        if self.is_tray_active:
            return
        self.is_tray_active = True
        self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        self.tray_thread.start()

    def _run_tray(self):
        self._create_icon()
        self.icon.run()

    def minimize_to_tray(self):
        # Hide the main window and show tray icon
        dpg.configure_viewport(0, show=False)
        hide_from_taskbar()
        self.show_tray()

    def restore_from_tray(self):
        # Show the main window and stop tray icon
        dpg.show_viewport()
        show_to_taskbar()
        self.is_tray_active = False
        if self.icon:
            self.icon.stop()

# Example usage in your main file:
# import threading
# from core.tray_functions import TrayManager, minimize_watcher
# tray = TrayManager(...)
# threading.Thread(target=minimize_watcher, args=(tray,), daemon=True).start()