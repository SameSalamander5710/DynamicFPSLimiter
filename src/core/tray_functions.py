import threading
import time
import os
import sys
import ctypes
from PIL import Image
import dearpygui.dearpygui as dpg
from pystray import Icon, MenuItem, Menu

app_title = "Dynamic FPS Limiter"

def get_hwnd_by_title(window_title):
    """
    Returns the HWND (window handle) for a window with the given title.
    Returns None if not found.
    """
    FindWindowW = ctypes.windll.user32.FindWindowW
    FindWindowW.restype = ctypes.c_void_p
    hwnd = FindWindowW(None, window_title)
    if hwnd == 0:
        return None
    return hwnd

def hide_from_taskbar():
    hwnd = get_hwnd_by_title(app_title)
    if hwnd:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x08 | 0x80  # Remove APPWINDOW, add TOOLWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE

def show_to_taskbar():
    hwnd = get_hwnd_by_title(app_title)
    if hwnd:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x80 | 0x08  # Remove TOOLWINDOW, add APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW

def is_window_minimized():
    """Returns True if the DearPyGui window is minimized (iconic), else False."""
    hwnd = get_hwnd_by_title(app_title)
    if hwnd:
        return ctypes.windll.user32.IsIconic(hwnd)
    return False

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
        self._dragging_viewport = False
        self._drag_start_mouse_y = None

    def drag_viewport(self, sender, app_data, user_data):
        mouse_pos = dpg.get_mouse_pos(local=False)
        mouse_y = mouse_pos[1]
        print(f"Mouse position: {mouse_pos}, dragging: {self._dragging_viewport}")

        if not self._dragging_viewport:
            # Only start dragging if mouse is in the top 40px when button is pressed
            if dpg.is_mouse_button_down(0):
                # Now handled in on_mouse_click
                return
            else:
                return

        # If dragging, update viewport position
        drag_deltas = app_data
        print(f"Drag deltas: {drag_deltas}, start mouse Y: {self._drag_start_mouse_y}")
        viewport_current_pos = dpg.get_viewport_pos()
        new_x_position = max(viewport_current_pos[0] + drag_deltas[1], 0)
        new_y_position = max(viewport_current_pos[1] + drag_deltas[2], 0)
        dpg.set_viewport_pos([new_x_position, new_y_position])

    def on_mouse_release(self, sender, app_data, user_data):
        if self._dragging_viewport:
            self._dragging_viewport = False
            self._drag_start_mouse_y = None
            print("Mouse released, stopping viewport dragging.")
            print(f"_dragging_viewport {self._dragging_viewport}")
        else:
            print("Mouse released normally")

    def on_mouse_click(self, sender, app_data, user_data):
        mouse_pos = dpg.get_mouse_pos(local=False)
        mouse_y = mouse_pos[1]
        if mouse_y < 40 and dpg.is_mouse_button_down(0):
            self._dragging_viewport = True
            self._drag_start_mouse_y = mouse_y
            print(f"Started dragging viewport at y={mouse_y}")
        else:
            self._dragging_viewport = False
            self._drag_start_mouse_y = None

    def _create_icon(self):
        image = Image.open(self.icon_path)
        menu = Menu(
            MenuItem("Restore", self._restore_window),
            MenuItem("Exit", self._exit_app)
        )
        self.icon = Icon(self.app_name, image, self.hover_text, menu)

    def _restore_window(self, icon, item):
        # Called from tray thread, so use a thread to call the GUI callback
        threading.Thread(target=self.on_restore, daemon=True).start()
        self.is_tray_active = False
        show_to_taskbar()
        if self.icon:
            self.icon.stop()

    def _exit_app(self, icon, item):
        threading.Thread(target=self.on_exit, daemon=True).start()
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
        hide_from_taskbar()
        self.show_tray()

    def restore_from_tray(self):
        # Show the main window and stop tray icon
        show_to_taskbar()
        self.is_tray_active = False
        if self.icon:
            self.icon.stop()

# Example usage in your main file:
# import threading
# from core.tray_functions import TrayManager, minimize_watcher
# tray = TrayManager(...)
# threading.Thread(target=minimize_watcher, args=(tray,), daemon=True).start()