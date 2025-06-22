import threading
import time
import os
import sys
import ctypes
from PIL import Image
import dearpygui.dearpygui as dpg
from pystray import Icon, MenuItem, Menu

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
        dpg.hide_viewport()
        self.show_tray()

    def restore_from_tray(self):
        # Show the main window and stop tray icon
        dpg.show_viewport()
        self.is_tray_active = False
        if self.icon:
            self.icon.stop()

# Example usage in DFL_v4.py:
# from core.tray_functions import TrayManager
# tray = TrayManager("DynamicFPSLimiter", icon_path, on_restore=restore_func, on_exit=exit_func, hover_text="Dynamic FPS Limiter")
# tray.minimize_to_tray()