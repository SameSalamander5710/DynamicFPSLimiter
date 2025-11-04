import dearpygui.dearpygui as dpg
import sys
import os
import ctypes

ctypes.windll.shcore.SetProcessDpiAwareness(2)

# Add the src directory to the Python path for imports
_this_dir = os.path.abspath(os.path.dirname(__file__))
_src_dir = os.path.dirname(_this_dir)  # Gets src directory
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from core.themes import ThemesManager
from core.tray_functions import TrayManager

class PopupDragHandler:
    """Simple drag handler that uses TrayManager's drag functionality for popups."""
    def __init__(self, viewport_width=420):
        # Create a minimal TrayManager instance just for drag functionality
        self.tray_manager = TrayManager(
            app_name="DynamicFPSLimiter",
            icon_path="",  # Not needed for drag functionality
            on_restore=None,
            on_exit=None,
            viewport_width=viewport_width,
            config_manager_instance=None
        )
    
    def on_mouse_click(self, sender, app_data, user_data):
        self.tray_manager.on_mouse_click(sender, app_data, user_data)
    
    def drag_viewport(self, sender, app_data, user_data):
        self.tray_manager.drag_viewport(sender, app_data, user_data)
    
    def on_mouse_release(self, sender, app_data, user_data):
        self.tray_manager.on_mouse_release(sender, app_data, user_data)

def show_missing_rtss_popup(message="Could not find RTSSHooks64.dll. Please ensure RivaTuner Statistics Server is installed before running this app.", exit_callback=None, themes_manager=None):
    # Create drag handler for the popup
    drag_handler = PopupDragHandler(viewport_width=420)
    
    with dpg.window(label="Error", modal=True, no_close=True, tag="Primary Window"):
        # Split the message to handle "Error:" separately
        if message.startswith("Error:"):
            error_part = "Error:"
            rest_of_message = message[6:].strip()  # Remove "Error:" and any following whitespace
            
            # Add "Error:" in bold
            error_text = dpg.add_text(error_part, wrap=400)
            if themes_manager:
                themes_manager.bind_font_to_item(error_text, "bold_font")
            
            # Add the rest of the message
            dpg.add_text(rest_of_message, wrap=400)
        else:
            dpg.add_text(message, wrap=400)
        
        # Add "Notice:" in bold
        notice_text = dpg.add_text("Notice:", wrap=400)
        if themes_manager:
            themes_manager.bind_font_to_item(notice_text, "bold_font")
            
        dpg.add_text("Please also ensure that the DynamicFPSLimiter app is downloaded from:", wrap=400)
        dpg.add_spacer(height=5)
        dpg.add_input_text(tag="notice_link", multiline=False, readonly=True, width=400)
        dpg.set_value("notice_link", "https://github.com/SameSalamander5710/DynamicFPSLimiter")
        
        # Apply blue text color to the link
        if themes_manager:
            with dpg.theme() as link_theme:
                with dpg.theme_component(dpg.mvInputText):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 150, 255, 255))  # Blue color
            dpg.bind_item_theme("notice_link", link_theme)

        dpg.add_spacer(height=5)
        dpg.add_text("This is currently the only official source of the app.")
        dpg.add_spacer(height=20)
        def _exit_app():
            if exit_callback:
                exit_callback()
            else:
                dpg.destroy_context()
                sys.exit(1)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=132)
            dpg.add_button(label="Close", width=120, callback=lambda: _exit_app())
        
        # Set up drag handlers for the popup
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(callback=drag_handler.on_mouse_click)
            dpg.add_mouse_drag_handler(callback=drag_handler.drag_viewport)
            dpg.add_mouse_release_handler(callback=drag_handler.on_mouse_release)

def show_rtss_error_and_exit(rtss_path):
    """
    Shows an RTSS error popup with full DearPyGui context creation and execution.
    This function handles the complete workflow and exits the application.
    """
    # Get the base directory for themes manager (same as in DFL_v4.py)
    Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    dpg.create_context()
    
    # Create themes and fonts for the popup
    themes_manager = ThemesManager(Base_dir)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()
    
    show_missing_rtss_popup(
        f"Error: Could not find 'RTSSHooks64.dll' (or one of its dependencies). "
        "Please ensure RivaTuner Statistics Server is installed before running this app.\n\n",
        themes_manager=themes_manager
    )
    
    # Apply the main theme to the popup
    dpg.bind_theme(themes_manager.themes["main_theme"])
    
    # Calculate center position for the viewport
    viewport_width = 420
    viewport_height = 320
    x_pos, y_pos = TrayManager.get_centered_viewport_position(viewport_width, viewport_height)
    
    dpg.create_viewport(title="Dynamic FPS Limiter - Error", width=viewport_width, height=viewport_height, 
                       resizable=False, decorated=False, x_pos=x_pos, y_pos=y_pos)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    dpg.start_dearpygui()
    sys.exit(1)

def show_loading_popup(message="Loading...", width=300, height=50, title="Dynamic FPS Limiter - Loading", themes_manager=None):
    """
    Creates a minimal DearPyGui context + viewport and shows a simple loading window.
    This is self-contained so it can be shown early and later completely destroyed
    with hide_loading_popup() before the main GUI context is created.
    """ 
    # If a context already exists, don't try to recreate it here.
    try:
        dpg.create_context()
    except Exception:
        # context may already exist; ignore
        pass

    Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

    # Create themes and fonts for the popup
    themes_manager = ThemesManager(Base_dir)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()

    # Basic window content
    with dpg.window(label="", tag="LoadingWindow", no_title_bar=True, no_resize=True,
                    no_move=False, no_collapse=True, width=width, height=height):
        dpg.add_spacer(height=1)
        dpg.add_text(message, tag="loading_text", wrap=width - 20)
        dpg.add_spacer(height=1)


    # If a themes manager is provided, bind the app font/theme to the loading text
    if themes_manager:
        try:
            # If themes/fonts were already created, bind the regular font (fallback if missing)
            themes_manager.bind_font_to_item("loading_text", "regular_font")
            # Bind the main theme so styles match other popups
            dpg.bind_theme(themes_manager.themes["main_theme"])
        except Exception:
            # Don't fail popup creation just because theming couldn't be applied
            pass

    # Center viewport on screen
    x_pos, y_pos = TrayManager.get_centered_viewport_position(width, height)
    try:
        dpg.create_viewport(title=title, width=width, height=height,
                            resizable=False, decorated=False, x_pos=x_pos, y_pos=y_pos)
    except Exception:
        # viewport may already exist
        pass

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("LoadingWindow", True)

    # Render a single frame so the window appears immediately
    try:
        dpg.render_dearpygui_frame()
    except Exception:
        pass

def hide_loading_popup():
    """
    Destroys the temporary loading viewport/context created by show_loading_popup.
    Call this before creating the main application context/viewport.
    """
    try:
        # destroy viewport if present
        try:
            dpg.destroy_viewport()
        except Exception:
            pass
        # destroy context
        try:
            dpg.destroy_context()
        except Exception:
            pass
    except Exception:
        pass

if __name__ == "__main__":
    # Test the popup by running this file directly using: python src\core\launch_popup.py
    print("Testing RTSS error popup...")
    
    # Get the base directory (same as in DFL_v4.py)
    Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    # Create context and apply fonts/themes
    dpg.create_context()
    themes_manager = ThemesManager(Base_dir)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()
    
    # Test with a sample RTSS path
    show_missing_rtss_popup(
        "Error: Could not find 'RTSSHooks64.dll' (or one of its dependencies). "
        "Please ensure RivaTuner Statistics Server is installed before running this app.\n\n",
        themes_manager=themes_manager
    )
    
    # Apply theme
    dpg.bind_theme(themes_manager.themes["main_theme"])
    
    # Calculate center position for the viewport
    viewport_width = 420
    viewport_height = 320
    x_pos, y_pos = TrayManager.get_centered_viewport_position(viewport_width, viewport_height)
    
    dpg.create_viewport(title="Dynamic FPS Limiter - Error", width=viewport_width, height=viewport_height, 
                       resizable=False, decorated=False, x_pos=x_pos, y_pos=y_pos)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    dpg.start_dearpygui()

