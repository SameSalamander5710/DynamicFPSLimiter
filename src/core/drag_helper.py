"""Lightweight viewport-drag handler for popups.

Replicates the minimal drag/window-moving logic that was previously
delegated to a full ``TrayManager`` instance in ``launch_popup.py``.
The helper keeps only the three pieces of mutable state the drag needs
(_dragging_viewport, _drag_start_mouse_pos, _drag_start_viewport_pos)
and the corresponding dpg callback signatures.
"""
import dearpygui.dearpygui as dpg

from core.tray_functions import (
    get_mouse_screen_pos,
    is_left_mouse_button_down,
)


class ViewportDragHandler:
    """Stateful mouse-drag handler that moves a DearPyGui viewport."""

    def __init__(self, viewport_width=420):
        self.viewport_width = viewport_width
        self._dragging_viewport = False
        self._drag_start_mouse_pos = None
        self._drag_start_viewport_pos = None

    def on_mouse_click(self, sender, app_data, user_data):
        mouse_pos_global = get_mouse_screen_pos()
        mouse_pos_app = dpg.get_mouse_pos(local=False)
        mouse_y = mouse_pos_app[1]
        mouse_x = mouse_pos_app[0]
        if mouse_y < 40 and dpg.is_mouse_button_down(0) and mouse_x < (self.viewport_width - 75):
            self._dragging_viewport = True
            self._drag_start_mouse_pos = mouse_pos_global
            self._drag_start_viewport_pos = dpg.get_viewport_pos()
        else:
            self._dragging_viewport = False
            self._drag_start_mouse_pos = None
            self._drag_start_viewport_pos = None

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
        dpg.set_viewport_pos([new_x, new_y])

    def on_mouse_release(self, sender, app_data, user_data):
        if self._dragging_viewport:
            self._dragging_viewport = False
            self._drag_start_mouse_pos = None
            self._drag_start_viewport_pos = None
