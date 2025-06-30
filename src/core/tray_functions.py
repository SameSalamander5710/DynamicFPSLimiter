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

def get_mouse_screen_pos():
    """Returns the mouse position as (x, y) in screen coordinates using Windows API."""
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)

def is_left_mouse_button_down():
    VK_LBUTTON = 0x01
    return (ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0

class TrayManager:
    def __init__(self, app_name, icon_path, on_restore, on_exit, viewport_width, hover_text=None, start_stop_callback=None, user_data=None):
        self.app_name = app_name
        self.icon_path = icon_path
        self.on_restore = on_restore
        self.on_exit = on_exit
        self.viewport_width = viewport_width
        self.hover_text = hover_text or app_name
        self.icon = None
        self.tray_thread = None
        self.is_tray_active = False
        self._dragging_viewport = False
        self._drag_start_mouse_pos = None
        self._drag_start_viewport_pos = None
        self.start_stop_callback = start_stop_callback
        self.user_data = user_data
        self.running = False  # Track running state for menu

    def drag_viewport(self, sender, app_data, user_data):
        if not self._dragging_viewport or not is_left_mouse_button_down():
            self._dragging_viewport = False
            self._drag_start_mouse_pos = None
            self._drag_start_viewport_pos = None
            return

        mouse_pos_global = get_mouse_screen_pos()
        if self._drag_start_mouse_pos is None or self._drag_start_viewport_pos is None:
            return

        dx = mouse_pos_global[0] - self._drag_start_mouse_pos[0]
        dy = mouse_pos_global[1] - self._drag_start_mouse_pos[1]
        new_x = self._drag_start_viewport_pos[0] + dx
        new_y = self._drag_start_viewport_pos[1] + dy
        
        print(f"Mouse position: {mouse_pos_global}, Start position: {self._drag_start_mouse_pos}")
        print(f"Dragging viewport by ({dx}, {dy}) to new position: ({new_x}, {new_y})")
        #current_viewport_pos = dpg.get_viewport_pos()
        #if (current_viewport_pos[0] != new_x) or (current_viewport_pos[1] != new_y):
        dpg.set_viewport_pos([new_x, new_y])

    def on_mouse_release(self, sender, app_data, user_data):
        if self._dragging_viewport:
            self._dragging_viewport = False
            self._drag_start_mouse_pos = None
            self._drag_start_viewport_pos = None
            print("Mouse released, stopping viewport dragging.")
        else:
            print("Mouse released normally")

    def on_mouse_click(self, sender, app_data, user_data):
        mouse_pos_global = get_mouse_screen_pos()
        mouse_pos_app = dpg.get_mouse_pos(local=False)
        mouse_y = mouse_pos_app[1]
        mouse_x = mouse_pos_app[0]
        if mouse_y < 40 and dpg.is_mouse_button_down(0) and mouse_x < (self.viewport_width - 75):
            self._dragging_viewport = True
            self._drag_start_mouse_pos = mouse_pos_global
            self._drag_start_viewport_pos = dpg.get_viewport_pos()
            print(f"Started dragging viewport at {mouse_pos_global}")
        else:
            self._dragging_viewport = False
            self._drag_start_mouse_pos = None
            self._drag_start_viewport_pos = None

    def _toggle_start_stop(self, icon, item):
        # Toggle running state and update menu label
        if self.start_stop_callback:
            self.start_stop_callback(None, None, self.user_data)
            self.running = not self.running
            # Update menu label
            self._update_menu()

    def _update_menu(self):
        # Rebuild the menu with updated Start/Stop label
        if self.icon:
            menu = Menu(
                MenuItem("Restore", self._restore_window),
                MenuItem("Start" if not self.running else "Stop", self._toggle_start_stop),
                MenuItem("Exit", self._exit_app)
            )
            self.icon.menu = menu

    def _create_icon(self):
        image = Image.open(self.icon_path)
        menu = Menu(
            MenuItem("Restore", self._restore_window),
            MenuItem("Start" if not self.running else "Stop", self._toggle_start_stop),
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